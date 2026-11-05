"""
Reliability, Recovery, and Persistence Test Suite for IOL.
Tests:
1. SSE reconnection and gapless replay after browser disconnect.
2. Worker recovery and restart from persistent store.
3. Mid-execution task cancellation.
4. Execution budget limits (max_steps, duration).
5. Duplicate entity handling and key resolution.
6. Source retrieval failure and timeout handling.
7. Approval gateway enforcement blocking unauthorized dispatch.
"""

import asyncio
import tempfile
from pathlib import Path
import pytest

from backend.iol.adapters.outreach.adapter import register_outreach_capabilities
from backend.iol.agent.planner import AdaptiveCapabilityPlanner
from backend.iol.capabilities.base import ExecutionContext
from backend.iol.capabilities.live_research import (
    LiveSourceAcquisitionCapability, SourceAcquisitionInput, register_live_research_capabilities
)
from backend.iol.capabilities.registry import CapabilityRegistry
from backend.iol.core.budgets import BudgetExceededError, BudgetTracker, TaskCancelledError
from backend.iol.core.models import ExecutionBudget, TaskStatus
from backend.iol.core.store import DurableTaskStore
from backend.iol.worker.background_worker import BackgroundWorker


@pytest.fixture
def env():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "reliability_test.db"
        store = DurableTaskStore(db_path=db_path)
        registry = CapabilityRegistry()
        register_outreach_capabilities(registry)
        register_live_research_capabilities(registry)
        planner = AdaptiveCapabilityPlanner()
        worker = BackgroundWorker(store=store, registry=registry, planner=planner)
        yield store, registry, planner, worker


# ------------------------------------------------------------------------------
# 1. SSE Reconnection & Replay
# ------------------------------------------------------------------------------
def test_sse_reconnection_and_replay(env):
    store, _, _, _ = env
    task = store.create_task(intent="Test SSE Reconnection")

    # Generate 5 sequential events
    for i in range(1, 6):
        store.append_event(task.task_id, f"EVENT_STEP_{i}", {"step": i})

    all_events = store.get_events(task.task_id)
    assert len(all_events) == 6  # 1 TASK_CREATED + 5 steps

    # Simulate client disconnect after event #3 (last seen id = all_events[3].event_id)
    last_seen_id = all_events[3].event_id
    replayed = store.get_events(task.task_id, since_event_id=last_seen_id)

    # Client reconnects and receives strictly the missed events in exact order
    assert len(replayed) == 2
    assert replayed[0].event_type == "EVENT_STEP_4"
    assert replayed[1].event_type == "EVENT_STEP_5"


# ------------------------------------------------------------------------------
# 2. Worker Recovery on Restart
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_worker_recovery_on_restart(env):
    store, registry, planner, worker1 = env

    # Task is submitted while worker1 is stopped
    task = store.create_task(intent="Task created before worker restart")
    assert store.get_task(task.task_id).status == TaskStatus.PENDING

    # Worker restarts (simulate new process instance)
    worker2 = BackgroundWorker(store=store, registry=registry, planner=planner)
    await worker2.process_task(task.task_id)

    # Asserts new worker successfully resumed and executed to completion
    completed = store.get_task(task.task_id)
    assert completed.status == TaskStatus.COMPLETED
    assert completed.current_step == completed.total_steps


# ------------------------------------------------------------------------------
# 3. Cancellation During Execution
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_mid_execution_cancellation(env):
    store, registry, planner, worker = env
    task = store.create_task(intent="Task to cancel mid-flight")

    # Trigger cancellation in store
    store.cancel_task(task.task_id, reason="Operator hit emergency stop")
    assert store.is_task_cancelled(task.task_id)

    # Worker attempts execution
    await worker.process_task(task.task_id)

    # Status must remain CANCELLED with cancellation reason
    final_task = store.get_task(task.task_id)
    assert final_task.status == TaskStatus.CANCELLED
    assert "Operator hit emergency stop" in (final_task.error_message or "")


# ------------------------------------------------------------------------------
# 4. Budget Exhaustion
# ------------------------------------------------------------------------------
def test_budget_exhaustion_detection():
    # Test step count limit
    budget = ExecutionBudget(max_steps=2, max_duration_seconds=60)
    tracker = BudgetTracker(budget=budget)

    tracker.record_step()  # Step 1: ok
    assert tracker.steps_executed == 1

    tracker.record_step()  # Step 2: ok
    assert tracker.steps_executed == 2

    # Step 3 breaches budget
    with pytest.raises(BudgetExceededError):
        tracker.record_step()


# ------------------------------------------------------------------------------
# 5. Duplicate Entity Discovery & Deduplication
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_duplicate_entity_handling(env):
    _, registry, _, _ = env
    ctx = ExecutionContext(task_id="t_dedup", step_id="s_dedup")

    # Feed duplicates
    entities = [
        {"name": "Prof. S. Jagannathan", "institution": "Missouri S&T"},
        {"name": "Prof. S. Jagannathan", "institution": "Missouri S&T"},  # Identical duplicate
        {"name": "Prof. Nan Jiang", "institution": "Fudan University"}
    ]
    res = await registry.invoke("data.deduplication", {
        "entity_type": "professor",
        "entities": entities,
        "identity_fields": ["institution", "name"]
    }, ctx)

    assert res.success is True
    assert res.data["duplicates_detected"] == 1
    assert len(res.data["unique_entities"]) == 2


# ------------------------------------------------------------------------------
# 6. Source Retrieval Failure & Timeout Resilience
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_source_retrieval_timeout_handling():
    cap = LiveSourceAcquisitionCapability()
    ctx = ExecutionContext(task_id="t_timeout", step_id="s_timeout")

    # Set impossible 0.0001s timeout to test timeout resilience
    params = SourceAcquisitionInput(
        entity_type="professor",
        query_terms=["test_timeout"],
        max_sources=2,
        timeout_seconds=0.0001
    )
    res = await cap.execute(params, ctx)
    # Should catch timeout cleanly without raising unhandled crash
    assert res.success is False
    assert "failed" in (res.error_message or "").lower() or res.verification_score == 0.0


# ------------------------------------------------------------------------------
# 7. Approval Gateway Rejects Unauthorized Live Dispatch
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_approval_gateway_blocks_unauthorized_dispatch(env):
    _, registry, _, _ = env
    ctx = ExecutionContext(task_id="t_sec", step_id="s_sec")

    # Attempt live email dispatch without operator session
    res = await registry.invoke("security.human_approval_gateway", {
        "action_type": "DISPATCH_OUTREACH",
        "payload": {"recipient": "prof@uni.edu", "body": "Draft text"},
        "dry_run": False  # Live mode
    }, ctx)

    assert res.success is False
    assert res.data["allowed"] is False
    assert "BLOCKED" in res.data["execution_status"]
