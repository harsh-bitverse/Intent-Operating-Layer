"""
Tests for Action Approvals, UI Action Relay, and Replay Bundles.
Validates cryptographic approval fingerprints, anti-replay guards, and replay bundle integrity.
"""

import pytest
from httpx import AsyncClient, ASGITransport

from backend.iol.api.app import app
from backend.iol.core.models import ExecutionBudget, TaskStatus
from backend.iol.core.store import task_store
from backend.iol.core.actions import (
    ActionApprovalManager,
    ActionApprovalTicket,
    ActionStatus,
    TaskActionRequest,
)
from backend.iol.browser.models import BrowserActionEffect
from backend.iol.core.replay_bundle import create_replay_bundle, ReplayBundle


@pytest.mark.asyncio
async def test_action_approval_lifecycle_and_anti_replay():
    """Verify approval tickets enforce cryptographic fingerprints and prevent replay attacks."""
    mgr = ActionApprovalManager()

    req = TaskActionRequest(
        task_id="task_act_test_1",
        action_type="submit_booking",
        effect=BrowserActionEffect.EXTERNAL_WRITE,
        parameters={"amount": 450, "currency": "INR", "target": "Indigo 6E-204"},
    )

    # 1. Issue ticket
    ticket = mgr.create_ticket(req)
    assert ticket.ticket_id.startswith("tkt_")
    assert ticket.status == ActionStatus.PENDING_APPROVAL
    assert len(ticket.fingerprint) == 64

    # 2. Tampered fingerprint rejected
    ok, err = mgr.approve_ticket(ticket.ticket_id, "tampered_fingerprint_hash", "admin")
    assert not ok
    assert "mismatch" in err.lower()

    # 3. Valid approval succeeds
    ok, err = mgr.approve_ticket(ticket.ticket_id, ticket.fingerprint, "admin")
    assert ok
    assert err is None
    assert ticket.status == ActionStatus.APPROVED

    # 4. Mark executed
    mgr.mark_executed(ticket.ticket_id, {"status": "SUCCESS"})
    assert ticket.status == ActionStatus.EXECUTED

    # 5. Replay attempt rejected
    ok_replay, err_replay = mgr.approve_ticket(ticket.ticket_id, ticket.fingerprint, "admin")
    assert not ok_replay
    assert "replay rejected" in err_replay.lower()


@pytest.mark.asyncio
async def test_action_endpoints_via_api():
    """Verify POST /tasks/{id}/actions and POST /tasks/{id}/actions/approve through FastAPI."""
    transport = ASGITransport(app=app)
    headers = {"X-API-Key": "iol_key_user_alpha"}

    # 1. Create task
    task = task_store.create_task(
        intent="Automated booking draft review",
        budget=ExecutionBudget(max_steps=5),
        user_id="user_a",
    )

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 2. Submit high-risk action requiring approval
        act_res = await client.post(
            f"/api/tasks/{task.task_id}/actions",
            headers=headers,
            json={
                "task_id": task.task_id,
                "action_type": "confirm_reservation",
                "effect": "EXTERNAL_WRITE",
                "parameters": {"reservation_id": "RES_9901"},
            },
        )
        assert act_res.status_code == 200
        act_data = act_res.json()
        assert act_data["status"] == "APPROVAL_REQUIRED"
        ticket = act_data["ticket"]
        assert ticket["status"] == "PENDING_APPROVAL"

        # Check task was paused for approval
        curr_task = task_store.get_task(task.task_id)
        assert curr_task.status == TaskStatus.PAUSED_FOR_APPROVAL

        # 3. Approve action
        appr_res = await client.post(
            f"/api/tasks/{task.task_id}/actions/approve",
            headers=headers,
            json={
                "ticket_id": ticket["ticket_id"],
                "fingerprint": ticket["fingerprint"],
            },
        )
        assert appr_res.status_code == 200
        appr_data = appr_res.json()
        assert appr_data["status"] == "APPROVED_AND_EXECUTED"

        # 4. Verify replay is rejected
        replay_res = await client.post(
            f"/api/tasks/{task.task_id}/actions/approve",
            headers=headers,
            json={
                "ticket_id": ticket["ticket_id"],
                "fingerprint": ticket["fingerprint"],
            },
        )
        assert replay_res.status_code == 400
        assert "replay rejected" in replay_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_replay_bundle_generation_and_verification():
    """Verify create_replay_bundle redacts credentials and creates valid SHA-256 integrity hash."""
    # 1. Create and populate task with events containing fake credentials
    task = task_store.create_task(
        intent="Research public datasets with api_key",
        user_id="user_a",
    )
    task_store.append_event(task.task_id, "TEST_EVENT", {
        "api_key": "sk-secret-12345678",
        "auth_token": "bearer-token-abc",
        "public_data": "sample_value",
    })

    # 2. Generate bundle
    bundle = create_replay_bundle(task.task_id, task_store)
    assert bundle is not None
    assert bundle.label == "RECORDED REPLAY"
    assert bundle.verify()  # SHA-256 verification passes!

    # 3. Ensure credentials are scrubbed
    ev_data = bundle.events[-1]["data"]
    assert ev_data["api_key"] == "[REDACTED_CREDENTIAL]"
    assert ev_data["auth_token"] == "[REDACTED_CREDENTIAL]"
    assert ev_data["public_data"] == "sample_value"

    # 4. Tamper check: modifying event breaks integrity
    bundle.events[-1]["data"]["public_data"] = "tampered_value"
    assert not bundle.verify()
