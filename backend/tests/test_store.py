"""
Tests for IOL Durable Task and Event Store.
Validates task CRUD, state transitions, cancellation, and SSE event replay.
"""

import tempfile
from pathlib import Path
import pytest
from backend.iol.core.models import ExecutionBudget, TaskStatus
from backend.iol.core.store import DurableTaskStore


@pytest.fixture
def temp_store():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_tasks.db"
        store = DurableTaskStore(db_path=db_path)
        yield store


def test_task_lifecycle(temp_store):
    task = temp_store.create_task(
        intent="Research machine learning faculty",
        budget=ExecutionBudget(max_duration_seconds=60, max_steps=10)
    )
    assert task.task_id.startswith("task_")
    assert task.status == TaskStatus.PENDING
    assert task.current_step == 0

    # Retrieve
    retrieved = temp_store.get_task(task.task_id)
    assert retrieved is not None
    assert retrieved.intent == "Research machine learning faculty"

    # Update to RUNNING
    temp_store.update_task_status(task.task_id, TaskStatus.RUNNING)
    assert temp_store.get_task(task.task_id).status == TaskStatus.RUNNING

    # Update Progress
    temp_store.update_task_progress(task.task_id, current_step=3, total_steps=6)
    p_task = temp_store.get_task(task.task_id)
    assert p_task.current_step == 3
    assert p_task.total_steps == 6

    # Update to COMPLETED
    temp_store.update_task_status(task.task_id, TaskStatus.COMPLETED)
    assert temp_store.get_task(task.task_id).status == TaskStatus.COMPLETED


def test_task_cancellation(temp_store):
    task = temp_store.create_task(intent="Long running crawl")
    assert not temp_store.is_task_cancelled(task.task_id)

    cancelled = temp_store.cancel_task(task.task_id, reason="User clicked stop")
    assert cancelled is True
    assert temp_store.is_task_cancelled(task.task_id)

    # Re-cancelling completed/cancelled task returns False
    assert temp_store.cancel_task(task.task_id) is False


def test_event_stream_and_replay(temp_store):
    task = temp_store.create_task(intent="Test streaming")

    # Initial event emitted on create
    events = temp_store.get_events(task.task_id)
    assert len(events) == 1
    assert events[0].event_type == "TASK_CREATED"
    first_id = events[0].event_id

    # Append sequential events
    ev2 = temp_store.append_event(task.task_id, "STEP_STARTED", {"step": 1})
    ev3 = temp_store.append_event(task.task_id, "STEP_COMPLETED", {"step": 1})
    assert ev2.event_id == first_id + 1
    assert ev3.event_id == first_id + 2

    # Replay all events strictly after first_id
    replayed = temp_store.get_events(task.task_id, since_event_id=first_id)
    assert len(replayed) == 2
    assert replayed[0].event_type == "STEP_STARTED"
    assert replayed[1].event_type == "STEP_COMPLETED"
