"""
Tests for IOL Background Worker.
Validates asynchronous task execution, budget tracking, UI state generation, and cancellation handling.
"""

import asyncio
import tempfile
from pathlib import Path
import pytest

from backend.iol.adapters.outreach.adapter import register_outreach_capabilities
from backend.iol.agent.orchestrator import IntentOrchestrator
from backend.iol.capabilities.registry import CapabilityRegistry
from backend.iol.core.models import ExecutionBudget, TaskStatus
from backend.iol.core.store import DurableTaskStore
from backend.iol.worker.background_worker import BackgroundWorker


@pytest.fixture
def worker_setup():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "worker_test.db"
        store = DurableTaskStore(db_path=db_path)
        registry = CapabilityRegistry()
        register_outreach_capabilities(registry)
        planner = IntentOrchestrator()
        worker = BackgroundWorker(store=store, registry=registry, planner=planner)
        yield worker, store


@pytest.mark.asyncio
async def test_worker_end_to_end_execution(worker_setup):
    worker, store = worker_setup
    task = store.create_task(
        intent="Research MIT AI professors for Summer 2027",
        budget=ExecutionBudget(max_duration_seconds=30, max_steps=10)
    )

    # Process task directly through worker
    await worker.process_task(task.task_id)

    # Check updated task state
    completed_task = store.get_task(task.task_id)
    assert completed_task.status == TaskStatus.COMPLETED
    assert completed_task.current_step == completed_task.total_steps
    assert completed_task.completed_at is not None

    # Check declarative UI state
    ui = completed_task.ui_state
    assert ui is not None
    assert len(ui.components) >= 3  # Metric summary, Timeline, Candidate table, etc.

    # Check that events were logged sequentially
    events = store.get_events(task.task_id)
    event_types = [e.event_type for e in events]
    assert "TASK_CREATED" in event_types
    assert "TASK_STARTED" in event_types
    assert "PLAN_GENERATED" in event_types
    assert "STEP_STARTED" in event_types
    assert "UI_UPDATED" in event_types
    assert "TASK_COMPLETED" in event_types


@pytest.mark.asyncio
async def test_worker_cancellation_during_execution(worker_setup):
    worker, store = worker_setup
    task = store.create_task(intent="Long crawl to cancel")

    # Cancel before processing
    store.cancel_task(task.task_id, reason="User cancelled early")

    await worker.process_task(task.task_id)
    t = store.get_task(task.task_id)
    assert t.status == TaskStatus.CANCELLED


@pytest.mark.asyncio
async def test_worker_execution_continues_when_experience_inference_fails(worker_setup, monkeypatch):
    """Verify Execution Engine continues independently if experience inference is slow, unavailable or invalid."""
    worker, store = worker_setup
    task = store.create_task(
        intent="Research Stanford AI professors for Fall 2027",
        budget=ExecutionBudget(max_duration_seconds=30, max_steps=10)
    )

    from backend.iol.experience import experience_planner

    def mock_failing_plan_experience(*args, **kwargs):
        raise RuntimeError("Simulated remote experience inference failure or timeout")

    monkeypatch.setattr(experience_planner, "plan_experience", mock_failing_plan_experience)

    # Process task directly through worker - must complete successfully
    await worker.process_task(task.task_id)

    completed_task = store.get_task(task.task_id)
    assert completed_task.status == TaskStatus.COMPLETED
    assert completed_task.current_step == completed_task.total_steps
    assert completed_task.completed_at is not None
