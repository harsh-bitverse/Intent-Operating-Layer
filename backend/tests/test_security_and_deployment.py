"""
Tests for Workstream E: Security Guardrails, SSRF Protection, Tenant Scoping, and Deployment Health Checks.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from backend.iol.api.app import app
from backend.iol.core.security import (
    SSRFSecurityError,
    safe_http_get,
    sanitize_extracted_string,
    validate_url_safety,
)


def test_ssrf_blocks_loopback_and_metadata():
    """Verify SSRF boundary blocks loopback, private ranges, and cloud metadata."""
    forbidden_urls = [
        "http://127.0.0.1:8000/secret",
        "http://localhost/admin",
        "http://127.0.0.2:80",
        "http://169.254.169.254/latest/meta-data",  # AWS/GCP metadata endpoint
        "http://10.0.0.1/internal",
        "http://192.168.1.1/router",
        "http://172.16.0.1/internal-docker",
        "file:///etc/passwd",
        "ftp://internal-server/data",
    ]

    for url in forbidden_urls:
        is_safe, reason = validate_url_safety(url)
        assert is_safe is False, f"URL '{url}' should have been blocked by SSRF filter"
        assert reason is not None


def test_ssrf_allows_public_domains():
    """Verify SSRF boundary permits legitimate public internet hostnames."""
    permitted_urls = [
        "https://api.openalex.org/works",
        "https://api.github.com/search/repositories",
        "https://stanford.edu",
        "https://mit.edu",
    ]

    for url in permitted_urls:
        is_safe, _ = validate_url_safety(url)
        assert is_safe is True, f"Legitimate public URL '{url}' was improperly blocked"


def test_safe_http_get_raises_ssrf_exception():
    """Verify safe_http_get raises SSRFSecurityError when targeting prohibited IP."""
    with pytest.raises(SSRFSecurityError):
        safe_http_get("http://169.254.169.254/latest/meta-data")

    with pytest.raises(SSRFSecurityError):
        safe_http_get("http://127.0.0.1:8000/internal")


def test_string_sanitizer():
    """Verify string sanitizer removes control characters and null bytes."""
    malformed = "Dr. Jane \x00Doe\r\n\x08 Professor"
    clean = sanitize_extracted_string(malformed)
    assert "\x00" not in clean
    assert "\x08" not in clean
    assert clean == "Dr. Jane Doe Professor"


def test_health_check_endpoints():
    """Verify both /api/health and /healthz endpoints respond properly."""
    from starlette.testclient import TestClient
    with TestClient(app) as client:
        # 1. API Health Check
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["capabilities_loaded"] >= 7

        # 2. Container Health Probe (/healthz)
        resp_z = client.get("/healthz")
        assert resp_z.status_code == 200
        data_z = resp_z.json()
        assert data_z["status"] == "ok"
        assert data_z["service"] == "iol-backend"


def test_tenant_user_scoping_in_task_creation():
    """Verify tasks support multi-tenant user_id scoping via server-derived credentials."""
    from starlette.testclient import TestClient
    with TestClient(app) as client:
        payload = {
            "intent": "Find 5 open-source AI developer tools",
            "metadata": {"org": "Bitverse Labs"},
        }
        resp = client.post(
            "/api/tasks",
            json=payload,
            headers={"X-API-Key": "iol_key_tenant_enterprise_42"}
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["user_id"] == "tenant_enterprise_42"
        assert data["metadata"]["user_id"] == "tenant_enterprise_42"
        assert data["metadata"]["org"] == "Bitverse Labs"

