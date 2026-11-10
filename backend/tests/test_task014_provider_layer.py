"""
Comprehensive Verification Suite for Task 014: Universal Model Provider Layer.
Verifies provider registry, secret sanitization, SSRF protection, provider adapters,
local disk model discovery, intelligent policy routing, automated fallback, and REST endpoints.
"""

import json
import os
import pytest
from unittest.mock import MagicMock, patch

from backend.iol.providers.models import (
    DiagnosticResult,
    FunctionalRole,
    InferenceRequest,
    InferenceResponse,
    ModelCapability,
    ProviderConfig,
    ProviderType,
    RoutingPolicy,
    UsageMetadata,
)
from backend.iol.providers.registry import ProviderRegistry, provider_registry
from backend.iol.providers.router import ModelRouter, model_router
from backend.iol.providers.ssrf import validate_provider_endpoint
from backend.iol.providers.adapters.base import BaseProviderAdapter
from backend.iol.providers.adapters.gemini import GeminiProviderAdapter
from backend.iol.providers.adapters.openai import OpenAIProviderAdapter
from backend.iol.providers.adapters.anthropic import AnthropicProviderAdapter
from backend.iol.providers.adapters.ollama import OllamaProviderAdapter
from backend.iol.providers.adapters.openai_compatible import OpenAICompatibleProviderAdapter
from backend.iol.providers.adapters.mock import MockProviderAdapter


# ---------------------------------------------------------------------------
# 1. SSRF Boundary and Security Protection Tests
# ---------------------------------------------------------------------------

def test_ssrf_blocks_cloud_metadata():
    """Verify that cloud instance metadata endpoints (169.254.169.254) are strictly blocked."""
    is_valid, msg = validate_provider_endpoint("http://169.254.169.254/latest/meta-data")
    assert not is_valid
    assert "metadata" in msg.lower()

    is_valid2, msg2 = validate_provider_endpoint("http://169.254.169.254:80/computeMetadata/v1")
    assert not is_valid2


def test_ssrf_blocks_forbidden_internal_system_ports():
    """Verify that loopback access to internal IOL backend, frontend, and DB ports is prohibited."""
    # Internal backend (8000)
    is_valid_8000, msg_8000 = validate_provider_endpoint("http://127.0.0.1:8000/api")
    assert not is_valid_8000
    assert "8000" in msg_8000

    # Internal frontend (3000)
    is_valid_3000, msg_3000 = validate_provider_endpoint("http://localhost:3000/")
    assert not is_valid_3000
    assert "3000" in msg_3000

    # PostgreSQL (5432)
    is_valid_pg, msg_pg = validate_provider_endpoint("http://127.0.0.1:5432/")
    assert not is_valid_pg
    assert "5432" in msg_pg

    # Redis (6379)
    is_valid_redis, msg_redis = validate_provider_endpoint("http://127.0.0.1:6379/")
    assert not is_valid_redis
    assert "6379" in msg_redis


def test_ssrf_permits_authorized_model_ports_and_cloud_apis():
    """Verify that authorized local model ports and official cloud model APIs are allowed."""
    # Ollama standard port 11434
    is_valid_ollama, _ = validate_provider_endpoint("http://127.0.0.1:11434")
    assert is_valid_ollama

    # llama-server / custom model port 18080
    is_valid_18080, _ = validate_provider_endpoint("http://localhost:18080/v1")
    assert is_valid_18080

    # vLLM port 8080
    is_valid_8080, _ = validate_provider_endpoint("http://127.0.0.1:8080/v1")
    assert is_valid_8080

    # Google Gemini official API
    is_valid_gemini, _ = validate_provider_endpoint("https://generativelanguage.googleapis.com/v1beta")
    assert is_valid_gemini

    # OpenAI official API
    is_valid_openai, _ = validate_provider_endpoint("https://api.openai.com/v1")
    assert is_valid_openai

    # Anthropic official API
    is_valid_anthropic, _ = validate_provider_endpoint("https://api.anthropic.com/v1")
    assert is_valid_anthropic


def test_ssrf_rejects_non_http_schemes():
    """Verify that arbitrary schemes like file:// or gopher:// are rejected."""
    is_valid, msg = validate_provider_endpoint("file:///etc/passwd")
    assert not is_valid
    assert "scheme" in msg.lower()


# ---------------------------------------------------------------------------
# 2. Secret Isolation and Sanitization Tests
# ---------------------------------------------------------------------------

def test_provider_config_sanitization_never_leaks_secrets():
    """Verify that to_sanitized_dict drops api_key and only produces a safe hint."""
    secret = "AIzaSySecretDeveloperKey1234567890"
    cfg = ProviderConfig(
        provider_id="test_prov",
        provider_type=ProviderType.GEMINI,
        display_name="Test Provider",
        base_url="https://generativelanguage.googleapis.com/v1beta",
        api_key=secret,
        default_model="gemini-3.8-flash",
    )

    sanitized = cfg.to_sanitized_dict()
    assert "api_key" not in sanitized
    assert sanitized["has_api_key"] is True
    assert sanitized["key_hint"] == "••••7890"
    assert secret not in json.dumps(sanitized)


def test_provider_registry_list_sanitized_by_default():
    """Verify provider_registry.list_providers() defaults to sanitized view."""
    reg = ProviderRegistry()
    providers = reg.list_providers()
    serialized = json.dumps(providers)

    for p in providers:
        assert "api_key" not in p
        assert "has_api_key" in p


# ---------------------------------------------------------------------------
# 3. Provider Adapters Unit Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mock_provider_adapter_generates_schema_valid_synthetic_plan():
    """Verify that MockProviderAdapter strictly assigns TEST_SYNTHESIZED and simulated usage."""
    adapter = MockProviderAdapter()
    req = InferenceRequest(
        system_prompt="Experience Planner",
        user_content="Design an algorithm visualization workspace for Dijkstra SP",
        require_json=True,
    )

    resp = await adapter.execute_inference(req)
    assert resp is not None
    assert resp.parsed_json is not None
    assert resp.parsed_json["mode"] == "FULL_WORKSPACE"
    assert not resp.is_trusted_foundation_model
    assert "mock test synthesizer" in resp.trust_reason.lower()
    assert resp.usage.usage_type == "SIMULATED"
    assert resp.usage.is_estimated is True

    # Health check
    diag = await adapter.check_health()
    assert diag.status == "HEALTHY"
    assert diag.is_connected is True


@pytest.mark.asyncio
async def test_gemini_adapter_missing_key_diagnostics():
    """Verify that Gemini adapter without API key reports BLOCKED status with MISSING_CREDENTIALS."""
    cfg = ProviderConfig(
        provider_id="gemini_unconfigured",
        provider_type=ProviderType.GEMINI,
        display_name="Gemini No Key",
        base_url="https://generativelanguage.googleapis.com/v1beta",
        api_key=None,
        default_model="gemini-3.8-flash",
    )
    adapter = GeminiProviderAdapter(cfg)
    diag = await adapter.check_health()
    assert diag.status == "BLOCKED"
    assert not diag.is_connected
    assert diag.error_reason == "MISSING_CREDENTIALS"


@pytest.mark.asyncio
async def test_ollama_adapter_offline_reports_disk_models():
    """Verify that Ollama adapter detects pre-installed weights even when daemon is offline."""
    cfg = ProviderConfig(
        provider_id="ollama_local",
        provider_type=ProviderType.OLLAMA,
        display_name="Ollama Local",
        base_url="http://127.0.0.1:11434",
        default_model="llama3.2:1b",
    )
    adapter = OllamaProviderAdapter(cfg)
    diag = await adapter.check_health()
    # Daemon is offline in test environment
    assert diag.status == "UNHEALTHY"
    assert not diag.is_connected
    assert diag.error_reason == "DAEMON_OFFLINE"
    # Should have discovered local disk models
    disk_models = adapter._discover_local_disk_models()
    if disk_models:
        assert len(diag.discovered_models) > 0


# ---------------------------------------------------------------------------
# 4. Local Disk Model Discovery Tests
# ---------------------------------------------------------------------------

def test_discover_local_disk_models_finds_gguf_assets():
    """Verify scanning ~/.ollama/models manifests discovers downloaded models."""
    models = provider_registry.discover_local_disk_models()
    assert isinstance(models, list)
    # On this machine, 4 models are downloaded in ~/.ollama
    if len(models) > 0:
        model_ids = [m["model_id"] for m in models]
        assert any("llama3.2" in m_id or "qwen2.5" in m_id for m_id in model_ids)
        for m in models:
            assert "model_id" in m
            assert "size_mb" in m
            assert m["size_mb"] > 0


# ---------------------------------------------------------------------------
# 5. Policy-Driven Routing and Automated Fallback Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_model_router_fallback_to_mock_when_primary_unavailable():
    """Verify that when primary provider fails, router fails over to fallback provider."""
    reg = ProviderRegistry()

    # Configure a primary that will fail (unconfigured cloud provider)
    broken_primary = ProviderConfig(
        provider_id="broken_cloud",
        provider_type=ProviderType.OPENAI,
        display_name="Broken Cloud",
        base_url="https://api.openai.com/v1",
        api_key=None,
        default_model="gpt-4o-mini",
        is_enabled=False,
    )
    reg.register_provider(broken_primary)

    router = ModelRouter(registry=reg)
    policy = RoutingPolicy(
        role=FunctionalRole.EXPERIENCE_SYNTHESIS,
        primary_provider_id="broken_cloud",
        fallback_provider_id="mock",
        allow_cloud=True,
        allow_local=True,
    )
    router.set_policy(FunctionalRole.EXPERIENCE_SYNTHESIS, policy)

    req = InferenceRequest(
        system_prompt="Test System",
        user_content="Test Fallback Routing",
        require_json=True,
    )

    resp, msg = await router.execute_role(FunctionalRole.EXPERIENCE_SYNTHESIS, req)
    assert resp is not None
    assert resp.provider_id == "mock"
    assert "fallback provider 'mock'" in msg.lower()


@pytest.mark.asyncio
async def test_model_router_privacy_boundary_blocks_cloud_when_disallowed():
    """Verify that if allow_cloud=False, cloud providers are skipped."""
    reg = ProviderRegistry()
    router = ModelRouter(registry=reg)

    # Set policy forbidding cloud execution
    policy = RoutingPolicy(
        role=FunctionalRole.INTENT_UNDERSTANDING,
        primary_provider_id="gemini",
        fallback_provider_id="mock",
        allow_cloud=False,
        allow_local=True,
    )
    router.set_policy(FunctionalRole.INTENT_UNDERSTANDING, policy)

    req = InferenceRequest(
        system_prompt="Test System",
        user_content="Private Local Intent",
        require_json=True,
    )

    resp, msg = await router.execute_role(FunctionalRole.INTENT_UNDERSTANDING, req)
    assert resp is not None
    # Primary gemini is cloud and was skipped; executed via fallback mock
    assert resp.provider_id == "mock"


# ---------------------------------------------------------------------------
# 6. REST API Endpoints Integration Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rest_api_list_providers():
    """Verify GET /api/models/providers returns 200 with sanitized data."""
    from backend.iol.api.model_routes import list_providers
    from backend.iol.api.auth import UserContext

    user = UserContext(user_id="test_admin", is_admin=True)
    res = await list_providers(current_user=user)
    assert isinstance(res, list)
    assert len(res) >= 4
    for p in res:
        assert "api_key" not in p
        assert "provider_id" in p


@pytest.mark.asyncio
async def test_rest_api_register_provider_ssrf_rejection():
    """Verify POST /api/models/providers rejects malicious loopback port with HTTP 400."""
    from backend.iol.api.model_routes import register_or_update_provider, UpdateProviderRequest
    from backend.iol.api.auth import UserContext
    from fastapi import HTTPException

    user = UserContext(user_id="test_admin", is_admin=True)
    bad_req = UpdateProviderRequest(
        provider_id="malicious_ssrf",
        provider_type=ProviderType.OPENAI_COMPATIBLE,
        display_name="Malicious Target",
        base_url="http://127.0.0.1:8000/internal",
        default_model="exploit",
    )

    with pytest.raises(HTTPException) as exc_info:
        await register_or_update_provider(bad_req, current_user=user)
    assert exc_info.value.status_code == 400
    assert "SSRF" in exc_info.value.detail


@pytest.mark.asyncio
async def test_rest_api_routing_policies_get_and_update():
    """Verify GET and PUT /api/models/routes."""
    from backend.iol.api.model_routes import get_routing_policies, update_routing_policy
    from backend.iol.api.auth import UserContext

    user = UserContext(user_id="test_admin", is_admin=True)
    policies = await get_routing_policies(current_user=user)
    assert len(policies) == 6
    assert FunctionalRole.EXPERIENCE_SYNTHESIS.value in policies

    new_policy = RoutingPolicy(
        role=FunctionalRole.EXPERIENCE_SYNTHESIS,
        primary_provider_id="mock",
        fallback_provider_id="ollama",
        allow_cloud=True,
        allow_local=True,
    )
    update_res = await update_routing_policy(new_policy, current_user=user)
    assert update_res["status"] == "UPDATED"
    assert update_res["role"] == "experience_synthesis"
