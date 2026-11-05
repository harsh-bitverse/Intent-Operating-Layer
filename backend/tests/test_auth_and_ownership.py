"""
Automated Authentication, Multi-Tenant Authorization, and SSRF Hardening Tests.
Verifies server-derived identity enforcement, cross-user task access isolation,
admin overrides, and outbound SSRF protections.
"""

from unittest.mock import MagicMock, patch
import pytest
from starlette.testclient import TestClient

from backend.iol.api.auth import PRECONFIGURED_API_KEYS
from backend.iol.api.app import app
from backend.iol.core.models import TaskStatus
from backend.iol.core.security import SSRFSecurityError, safe_http_get, validate_url_safety
from backend.iol.core.store import task_store


@pytest.fixture
def api_client():
    with TestClient(app) as client:
        yield client


# ==============================================================================
# 1. Server-Derived Identity Enforcement & Spoofing Immunity
# ==============================================================================
def test_user_id_derived_from_server_ignoring_client_payload(api_client):
    """
    Verifies that client-provided user_id in the JSON body is ignored,
    and the task is strictly bound to the authenticated user from the API key.
    """
    headers_user_a = {"X-API-Key": "iol_key_user_alpha"}

    # Client maliciously attempts to claim user_id="admin" or user_id="user_b"
    payload = {
        "intent": "Find 5 AI developer tools",
        "user_id": "malicious_spoofed_admin"
    }

    resp = api_client.post("/api/tasks", json=payload, headers=headers_user_a)
    assert resp.status_code == 201
    data = resp.json()

    # The resulting task MUST be owned by user_a, NOT malicious_spoofed_admin
    assert data["user_id"] == "user_a"
    assert data["metadata"]["user_id"] == "user_a"

    persisted = task_store.get_task(data["task_id"])
    assert persisted is not None
    assert persisted.user_id == "user_a"


# ==============================================================================
# 2. Multi-Tenant Cross-User Isolation (Negative Tests: 403 Forbidden)
# ==============================================================================
def test_cross_user_task_access_forbidden(api_client):
    """
    Verifies that User Beta cannot view, cancel, or stream User Alpha's tasks.
    """
    headers_user_a = {"X-API-Key": "iol_key_user_alpha"}
    headers_user_b = {"X-API-Key": "iol_key_user_beta"}

    # 1. User Alpha creates a task
    create_resp = api_client.post(
        "/api/tasks",
        json={"intent": "Research private datasets"},
        headers=headers_user_a
    )
    assert create_resp.status_code == 201
    task_a_id = create_resp.json()["task_id"]

    # 2. User Beta attempts to GET User Alpha's task -> 403 Forbidden
    get_resp = api_client.get(f"/api/tasks/{task_a_id}", headers=headers_user_b)
    assert get_resp.status_code == 403
    assert "Access denied" in get_resp.json()["detail"]

    # 3. User Beta attempts to CANCEL User Alpha's task -> 403 Forbidden
    cancel_resp = api_client.post(f"/api/tasks/{task_a_id}/cancel", headers=headers_user_b)
    assert cancel_resp.status_code == 403
    assert "Access denied" in cancel_resp.json()["detail"]

    # 4. User Beta attempts to stream User Alpha's events -> 403 Forbidden
    stream_resp = api_client.get(f"/api/tasks/{task_a_id}/events", headers=headers_user_b)
    assert stream_resp.status_code == 403
    assert "Access denied" in stream_resp.json()["detail"]


# ==============================================================================
# 3. Scoped Task Listing Isolation
# ==============================================================================
def test_scoped_task_listing_per_user(api_client):
    """
    Verifies that GET /api/tasks returns only the tasks owned by the requesting user.
    """
    headers_user_a = {"X-API-Key": "iol_key_user_alpha"}
    headers_user_b = {"X-API-Key": "iol_key_user_beta"}

    # User Alpha creates a task
    resp_a = api_client.post("/api/tasks", json={"intent": "Alpha Task 1"}, headers=headers_user_a)
    task_a_id = resp_a.json()["task_id"]

    # User Beta creates a task
    resp_b = api_client.post("/api/tasks", json={"intent": "Beta Task 1"}, headers=headers_user_b)
    task_b_id = resp_b.json()["task_id"]

    # User Alpha lists tasks -> should see task_a, but NOT task_b
    list_a = api_client.get("/api/tasks", headers=headers_user_a).json()
    task_ids_seen_by_a = [t["task_id"] for t in list_a]
    assert task_a_id in task_ids_seen_by_a
    assert task_b_id not in task_ids_seen_by_a

    # User Beta lists tasks -> should see task_b, but NOT task_a
    list_b = api_client.get("/api/tasks", headers=headers_user_b).json()
    task_ids_seen_by_b = [t["task_id"] for t in list_b]
    assert task_b_id in task_ids_seen_by_b
    assert task_a_id not in task_ids_seen_by_b


# ==============================================================================
# 4. Administrator Full Access Override
# ==============================================================================
def test_admin_full_access_override(api_client):
    """
    Verifies that a user with admin credentials can view and list any user's task.
    """
    headers_user_a = {"X-API-Key": "iol_key_user_alpha"}
    headers_admin = {"X-API-Key": "iol_admin_secret_key_prod_2026"}

    # User Alpha creates a task
    resp_a = api_client.post("/api/tasks", json={"intent": "Alpha Secret Task"}, headers=headers_user_a)
    task_a_id = resp_a.json()["task_id"]

    # Admin accesses User Alpha's task -> 200 OK
    admin_get = api_client.get(f"/api/tasks/{task_a_id}", headers=headers_admin)
    assert admin_get.status_code == 200
    assert admin_get.json()["task_id"] == task_a_id

    # Admin lists tasks -> sees tasks across all tenants
    admin_list = api_client.get("/api/tasks", headers=headers_admin).json()
    all_ids = [t["task_id"] for t in admin_list]
    assert task_a_id in all_ids


# ==============================================================================
# 5. Invalid Credentials Rejection (401 Unauthorized)
# ==============================================================================
def test_invalid_api_key_returns_unauthorized(api_client):
    """
    Verifies that invalid or forged API keys are rejected with 401 Unauthorized.
    """
    bad_headers = {"X-API-Key": "forged_non_existent_key_999"}
    resp = api_client.get("/api/tasks", headers=bad_headers)
    assert resp.status_code == 401
    assert "Invalid or unrecognized API key" in resp.json()["detail"]


# ==============================================================================
# 6. SSRF Hardening: Redirect-Following and IPv6 Prohibitions
# ==============================================================================
def test_ssrf_blocks_cloud_metadata_and_ipv6_loopbacks():
    """
    Validates that cloud metadata IPs, loopbacks, and IPv4-mapped IPv6 are blocked.
    """
    # Cloud metadata IP
    is_safe, reason = validate_url_safety("http://169.254.169.254/latest/meta-data")
    assert is_safe is False
    assert "169.254.169.254" in reason

    # Localhost and IPv6 loopback
    is_safe, reason = validate_url_safety("http://127.0.0.1:8000/api/tasks")
    assert is_safe is False

    is_safe, reason = validate_url_safety("http://[::1]:8000/api/tasks")
    assert is_safe is False

    # IPv4-mapped IPv6 loopback
    is_safe, reason = validate_url_safety("http://[::ffff:127.0.0.1]:8000/")
    assert is_safe is False


def test_ssrf_blocks_malicious_redirect_to_internal_metadata():
    """
    Verifies that safe_http_get catches and halts an HTTP 302 redirect
    targeting internal cloud metadata or local loopback.
    """
    # Mock response: First request returns 302 pointing to 169.254.169.254
    redirect_resp = MagicMock()
    redirect_resp.status_code = 302
    redirect_resp.headers = {"Location": "http://169.254.169.254/latest/meta-data"}

    with patch("backend.iol.core.security.validate_url_safety") as mock_validate:
        # First call is safe (e.g. public URL), second call (redirect target) is blocked
        mock_validate.side_effect = [
            (True, None),
            (False, "Access to cloud metadata service (169.254.169.254) is strictly prohibited.")
        ]
        with patch("requests.get", return_value=redirect_resp):
            with pytest.raises(SSRFSecurityError) as exc_info:
                safe_http_get("https://public-service.org/short-url")

            assert "Access to cloud metadata service" in str(exc_info.value)
