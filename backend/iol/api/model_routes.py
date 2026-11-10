"""
Model Provider and Routing Management Endpoints for IOL.
Provides secure, sanitized APIs for inspecting configured providers, testing connectivity,
discovering local models, updating SSRF-validated endpoints, and configuring role-based model routing.
"""

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.iol.api.auth import UserContext, get_current_user
from backend.iol.providers.models import (
    DiagnosticResult,
    FunctionalRole,
    InferenceRequest,
    ModelCapability,
    ProviderConfig,
    ProviderType,
    RoutingPolicy,
)
from backend.iol.providers.registry import provider_registry
from backend.iol.providers.router import model_router
from backend.iol.providers.ssrf import validate_provider_endpoint

logger = logging.getLogger("iol.api.model_routes")

model_api_router = APIRouter(prefix="/models", tags=["Model Providers"])


class UpdateProviderRequest(BaseModel):
    """Payload to register or update a model provider configuration."""
    provider_id: str
    provider_type: ProviderType
    display_name: str
    base_url: str
    api_key: Optional[str] = None
    default_model: str
    available_models: List[str] = Field(default_factory=list)
    capabilities: List[ModelCapability] = Field(default_factory=list)
    is_local: bool = False
    is_enabled: bool = True
    timeout_seconds: float = 15.0


class TestInferenceRequest(BaseModel):
    """Payload to test real structured inference through the model router."""
    role: FunctionalRole = FunctionalRole.EXPERIENCE_SYNTHESIS
    intent: str
    provider_override: Optional[str] = None


@model_api_router.get("/providers", response_model=List[Dict[str, Any]])
async def list_providers(
    current_user: UserContext = Depends(get_current_user)
):
    """
    Lists all registered model providers.
    Outputs strictly sanitized metadata with API keys masked to prevent leakage.
    """
    return provider_registry.list_providers(sanitized=True)


@model_api_router.post("/providers", response_model=Dict[str, Any], status_code=status.HTTP_200_OK)
async def register_or_update_provider(
    req: UpdateProviderRequest,
    current_user: UserContext = Depends(get_current_user)
):
    """
    Registers or updates a model provider configuration with strict SSRF validation.
    Loopback access is limited to authorized local model ports (e.g. 11434, 18080).
    System ports (8000, 3000, 5432, 6379) and cloud metadata services are blocked.
    """
    if req.provider_type != ProviderType.MOCK:
        is_valid, err_msg = validate_provider_endpoint(req.base_url)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Security SSRF Violation: {err_msg}"
            )

    # Preserve existing key if new key not provided
    final_key = req.api_key
    existing_cfg = provider_registry.get_config(req.provider_id)
    if not final_key and existing_cfg and existing_cfg.api_key:
        final_key = existing_cfg.api_key

    config = ProviderConfig(
        provider_id=req.provider_id,
        provider_type=req.provider_type,
        display_name=req.display_name,
        base_url=req.base_url,
        api_key=final_key,
        default_model=req.default_model,
        available_models=req.available_models,
        capabilities=req.capabilities,
        is_local=req.is_local,
        is_enabled=req.is_enabled,
        timeout_seconds=req.timeout_seconds,
    )

    try:
        provider_registry.register_provider(config)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return {
        "status": "REGISTERED",
        "provider": config.to_sanitized_dict(),
        "message": f"Provider '{req.provider_id}' successfully updated and verified.",
    }


@model_api_router.post("/providers/{provider_id}/test", response_model=DiagnosticResult)
async def test_provider_connectivity(
    provider_id: str,
    current_user: UserContext = Depends(get_current_user)
):
    """
    Executes live diagnostic health check and model discovery for a specific provider.
    """
    adapter = provider_registry.get_adapter(provider_id)
    if not adapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{provider_id}' is not registered."
        )

    diag = await adapter.check_health()
    return diag


@model_api_router.get("/routes", response_model=Dict[str, RoutingPolicy])
async def get_routing_policies(
    current_user: UserContext = Depends(get_current_user)
):
    """
    Returns the routing policy configurations across all 6 IOL functional roles.
    """
    return model_router.get_all_policies()


@model_api_router.put("/routes", response_model=Dict[str, Any])
async def update_routing_policy(
    policy: RoutingPolicy,
    current_user: UserContext = Depends(get_current_user)
):
    """
    Updates routing policy for a specific functional role (e.g. experience_synthesis, planning).
    """
    model_router.set_policy(policy.role, policy)
    return {
        "status": "UPDATED",
        "role": policy.role.value,
        "policy": policy.model_dump(),
        "message": f"Routing policy for role '{policy.role.value}' successfully saved.",
    }


@model_api_router.get("/local", response_model=List[Dict[str, Any]])
async def discover_local_models(
    current_user: UserContext = Depends(get_current_user)
):
    """
    Scans local disk (~/.ollama/models) to discover pre-installed model assets and weights.
    """
    return provider_registry.discover_local_disk_models()


@model_api_router.post("/test-inference", response_model=Dict[str, Any])
async def test_role_inference(
    req: TestInferenceRequest,
    current_user: UserContext = Depends(get_current_user)
):
    """
    Executes a test inference request for a given functional role through the intelligent model router.
    """
    system_prompt = (
        "You are the IOL Experience Synthesizer. "
        "Return strictly valid JSON conforming to: "
        "{ 'mode': 'FULL_WORKSPACE', 'title': str, 'subtitle': str, 'components': list }."
    )
    user_content = f"User Intent: {req.intent}\nSynthesize an analytical workspace layout."

    inf_req = InferenceRequest(
        system_prompt=system_prompt,
        user_content=user_content,
        require_json=True,
        timeout_seconds=10.0,
        role=req.role,
    )

    resp, status_msg = await model_router.execute_role(
        role=req.role,
        request=inf_req,
        context_override_provider=req.provider_override,
    )

    if not resp:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Inference failed across primary and fallback routes: {status_msg}"
        )

    return {
        "status": "SUCCESS",
        "router_status": status_msg,
        "provider_id": resp.provider_id,
        "model_name": resp.model_name,
        "is_trusted_foundation_model": resp.is_trusted_foundation_model,
        "trust_reason": resp.trust_reason,
        "latency_ms": resp.latency_ms,
        "transport_ms": resp.transport_ms,
        "usage": resp.usage.model_dump(),
        "parsed_json": resp.parsed_json,
    }
