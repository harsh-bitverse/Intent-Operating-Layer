"""
Tests for IOL OutcomeEnvelopeV1 and Monotonic Streaming.
Validates typed outcome shapes, source mode tracking, SHA-256 integrity, and API retrieval.
"""

import pytest
from httpx import AsyncClient, ASGITransport

from backend.iol.api.app import app
from backend.iol.core.outcome import (
    OutcomeEnvelopeV1,
    OutcomeFieldSchema,
    OutcomeItem,
    OutcomeEvidenceRecord,
    OutcomeShape,
    SourceMode,
)
from backend.iol.core.models import ExecutionBudget
from backend.iol.core.store import task_store
from backend.iol.worker.background_worker import BackgroundWorker
from backend.iol.capabilities.registry import capability_registry
from backend.iol.capabilities.educational import register_educational_capabilities
from backend.iol.capabilities.browser import register_browser_capabilities


def test_outcome_envelope_integrity_and_serialization():
    """Verify OutcomeEnvelopeV1 integrity hash, monotonicity, and legacy row conversion."""
    env = OutcomeEnvelopeV1(
        shape=OutcomeShape.COLLECTION,
        title="AI Framework Comparison",
        summary="Verified entities with live evidence",
        field_schema=[
            OutcomeFieldSchema(key="name", header="Framework Name", type="text", role="title"),
            OutcomeFieldSchema(key="stars", header="GitHub Stars", type="number", role="metric"),
            OutcomeFieldSchema(key="url", header="Repository", type="link", role="url"),
        ],
        source_mode=SourceMode.LIVE_API,
        revision=1,
    )

    item1 = OutcomeItem(
        id="item_langchain",
        fields={"name": "LangChain", "stars": 92000, "url": "https://github.com/langchain-ai/langchain"},
        evidence=[
            OutcomeEvidenceRecord(
                field_name="stars",
                source_url="https://api.github.com/repos/langchain-ai/langchain",
                source_mode=SourceMode.LIVE_API,
                excerpt="stargazers_count: 92000",
                confidence=1.0,
            )
        ],
        status="VERIFIED",
    )

    env.add_item(item1)
    assert env.revision == 2
    assert len(env.items) == 1

    h1 = env.compute_integrity_hash()
    assert len(h1) == 64  # SHA-256 hex string

    # Converting to legacy rows preserves _evidence
    rows = env.to_legacy_rows()
    assert len(rows) == 1
    assert rows[0]["name"] == "LangChain"
    assert "_evidence" in rows[0]
    assert rows[0]["_evidence"][0]["source_url"] == "https://api.github.com/repos/langchain-ai/langchain"


@pytest.mark.asyncio
async def test_outcome_envelope_worker_pipeline_and_api():
    """Verify worker populates outcome_envelope on task execution and GET /api/tasks/{id}/outcome returns it."""
    register_educational_capabilities(capability_registry)
    register_browser_capabilities(capability_registry)

    worker = BackgroundWorker(store=task_store, registry=capability_registry)

    # 1. Create task
    task = task_store.create_task(
        intent="Teach me how a neural network learns with step by step math",
        budget=ExecutionBudget(max_steps=5, max_duration_seconds=60),
        user_id="user_a",
    )

    # 2. Process task through worker
    await worker.process_task(task.task_id)

    # 3. Retrieve task from store
    completed_task = task_store.get_task(task.task_id)
    assert completed_task is not None
    assert completed_task.outcome_envelope is not None
    assert completed_task.outcome_envelope["shape"] == OutcomeShape.SIMULATION.value
    assert completed_task.outcome_envelope["source_mode"] == SourceMode.LOCAL_COMPUTATION.value
    assert len(completed_task.outcome_envelope["items"]) > 0

    # 4. Verify API endpoint GET /api/tasks/{task_id}/outcome
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(
            f"/api/tasks/{task.task_id}/outcome",
            headers={"X-API-Key": "iol_key_user_alpha"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["task_id"] == task.task_id
        assert data["outcome_envelope"]["shape"] == "simulation"
        assert len(data["outcome_envelope"]["items"]) >= 5
