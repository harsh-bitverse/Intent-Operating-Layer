"""
Policy-Driven Model Router for Intent Operating Layer.
Directs inference requests to appropriate foundation models based on functional role,
task constraints, local vs. cloud privacy requirements, cost limits, and automated fallback.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple

from backend.iol.providers.models import (
    FunctionalRole,
    InferenceRequest,
    InferenceResponse,
    ModelCapability,
    ProviderType,
    RoutingPolicy,
)
from backend.iol.providers.registry import ProviderRegistry, provider_registry

logger = logging.getLogger("iol.providers.router")


class ModelRouter:
    """Intelligent router selecting optimal model providers for distinct IOL functional roles."""

    def __init__(self, registry: Optional[ProviderRegistry] = None):
        self.registry = registry or provider_registry
        self._policies: Dict[FunctionalRole, RoutingPolicy] = self._default_policies()

    def _default_policies(self) -> Dict[FunctionalRole, RoutingPolicy]:
        """Sets deterministic default routing policies across IOL subsystems."""
        # Check available providers to set intelligent defaults
        gemini_cfg = self.registry.get_config("gemini")
        openai_cfg = self.registry.get_config("openai")
        ollama_cfg = self.registry.get_config("ollama")

        # Pick default primary provider based on availability
        default_primary = "gemini" if (gemini_cfg and gemini_cfg.is_enabled) else (
            "openai" if (openai_cfg and openai_cfg.is_enabled) else "ollama"
        )
        default_fallback = "ollama" if default_primary != "ollama" else "mock"

        policies: Dict[FunctionalRole, RoutingPolicy] = {}
        for role in FunctionalRole:
            policies[role] = RoutingPolicy(
                role=role,
                primary_provider_id=default_primary,
                fallback_provider_id=default_fallback,
                allow_cloud=True,
                allow_local=True,
                max_latency_ms=30000.0,
                require_structured_output=True,
            )
        return policies

    def get_policy(self, role: FunctionalRole) -> RoutingPolicy:
        """Returns the active routing policy for a given functional role."""
        return self._policies.get(role, self._policies[FunctionalRole.EXPERIENCE_SYNTHESIS])

    def set_policy(self, role: FunctionalRole, policy: RoutingPolicy) -> None:
        """Updates routing policy for a functional role."""
        self._policies[role] = policy

    def get_all_policies(self) -> Dict[str, RoutingPolicy]:
        """Returns all configured functional role policies."""
        return {r.value: p for r, p in self._policies.items()}

    async def execute_role(
        self,
        role: FunctionalRole,
        request: InferenceRequest,
        context_override_provider: Optional[str] = None,
    ) -> Tuple[Optional[InferenceResponse], str]:
        """
        Executes an inference request for a functional role with policy-based routing and automated fallback.
        Returns (response, execution_status_message).
        """
        policy = self.get_policy(role)
        primary_id = context_override_provider or policy.primary_provider_id
        fallback_id = policy.fallback_provider_id

        # 1. Attempt Primary Provider
        primary_adapter = self.registry.get_adapter(primary_id)
        if primary_adapter:
            cfg = primary_adapter.config
            # Privacy check
            if cfg.is_local or policy.allow_cloud:
                try:
                    logger.info(f"Routing [{role.value}] to primary provider '{primary_id}' (model: {cfg.default_model})")
                    resp = await primary_adapter.execute_inference(request)
                    if resp and (not request.require_json or resp.parsed_json is not None):
                        return resp, f"Executed via primary provider '{primary_id}'"
                except Exception as e:
                    logger.warning(f"Primary provider '{primary_id}' inference failed for [{role.value}]: {e}")

        # 2. Attempt Fallback Provider if configured and different
        if fallback_id and fallback_id != primary_id:
            fallback_adapter = self.registry.get_adapter(fallback_id)
            if fallback_adapter:
                f_cfg = fallback_adapter.config
                if f_cfg.is_local or policy.allow_cloud:
                    try:
                        logger.info(f"Failing over [{role.value}] to fallback provider '{fallback_id}'")
                        resp = await fallback_adapter.execute_inference(request)
                        if resp and (not request.require_json or resp.parsed_json is not None):
                            return resp, f"Executed via fallback provider '{fallback_id}'"
                    except Exception as fe:
                        logger.warning(f"Fallback provider '{fallback_id}' inference also failed: {fe}")

        return None, "All candidate providers failed or unconfigured"


# Global singleton instance
model_router = ModelRouter()
