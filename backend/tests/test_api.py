"""
Tests for IOL FastAPI REST Endpoints and SSE Event Streaming.
"""

import pytest
from starlette.testclient import TestClient
from backend.iol.api.app import app
from backend.iol.core.models import TaskStatus


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_health_check(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["capabilities_loaded"] >= 7


def test_capabilities_endpoint(client):
    res = client.get("/api/capabilities")
    assert res.status_code == 200
    caps = res.json()
    assert len(caps) >= 7
    cap_ids = [c["capability_id"] for c in caps]
    assert "research.entity_discovery" in cap_ids
    assert "research.verification" in cap_ids
    assert "content.constrained_personalization" in cap_ids
    assert "scheduling.destination_window" in cap_ids
    assert "security.human_approval_gateway" in cap_ids


def test_task_creation_and_retrieval(client):
    req_body = {
        "intent": "Research faculty at MIT for Summer 2027",
        "budget": {
            "max_duration_seconds": 120,
            "max_steps": 10
        }
    }
    create_res = client.post("/api/tasks", json=req_body)
    assert create_res.status_code == 201
    created_task = create_res.json()
    assert created_task["task_id"].startswith("task_")
    assert created_task["intent"] == req_body["intent"]
    task_id = created_task["task_id"]

    # Retrieve
    get_res = client.get(f"/api/tasks/{task_id}")
    assert get_res.status_code == 200
    retrieved = get_res.json()
    assert retrieved["task_id"] == task_id

    # List tasks
    list_res = client.get("/api/tasks")
    assert list_res.status_code == 200
    task_list = list_res.json()
    assert any(t["task_id"] == task_id for t in task_list)


def test_task_cancellation_endpoint(client):
    create_res = client.post("/api/tasks", json={"intent": "Cancellable task"})
    task_id = create_res.json()["task_id"]

    cancel_res = client.post(f"/api/tasks/{task_id}/cancel", json={"reason": "Test cancel"})
    assert cancel_res.status_code == 200
    data = cancel_res.json()
    assert data["cancelled"] is True
    assert data["current_status"] == TaskStatus.CANCELLED.value


def test_sse_event_stream_headers(client):
    create_res = client.post("/api/tasks", json={"intent": "Streaming task"})
    task_id = create_res.json()["task_id"]

    # Test SSE stream with a short read
    with client.stream("GET", f"/api/tasks/{task_id}/events") as stream_res:
        assert stream_res.status_code == 200
        assert "text/event-stream" in stream_res.headers["content-type"]
        # Read the first chunk (should contain TASK_CREATED)
        first_chunk = next(stream_res.iter_text())
        assert "event: TASK_CREATED" in first_chunk
        assert f"\"task_id\": \"{task_id}\"" in first_chunk
