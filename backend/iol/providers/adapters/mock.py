"""
Deterministic Mock Provider Adapter for Offline CI and Integration Testing.
Strictly produces TEST_SYNTHESIZED plans with simulated usage metrics.
Never self-asserts MODEL_GENERATED foundation model provenance.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from backend.iol.providers.adapters.base import BaseProviderAdapter
from backend.iol.providers.models import (
    DiagnosticResult,
    InferenceRequest,
    InferenceResponse,
    ModelCapability,
    ProviderConfig,
    ProviderType,
    UsageMetadata,
)

logger = logging.getLogger("iol.providers.mock")


class MockProviderAdapter(BaseProviderAdapter):
    """Deterministic synthetic provider for testing and validation."""

    def __init__(self, config: Optional[ProviderConfig] = None):
        cfg = config or ProviderConfig(
            provider_id="mock",
            provider_type=ProviderType.MOCK,
            display_name="Test Synthesizer (Offline Mock)",
            base_url="mock://iol",
            default_model="iol-test-synthesizer-v1",
            available_models=["iol-test-synthesizer-v1"],
            capabilities=[ModelCapability.STRUCTURED_OUTPUT, ModelCapability.JSON_MODE],
        )
        super().__init__(cfg)

    async def check_health(self) -> DiagnosticResult:
        return DiagnosticResult(
            provider_id=self.config.provider_id,
            provider_type=ProviderType.MOCK,
            status="HEALTHY",
            is_connected=True,
            latency_ms=0.5,
            discovered_models=["iol-test-synthesizer-v1"],
            message="Deterministic mock provider ready for offline testing",
        )

    async def discover_models(self) -> List[str]:
        return ["iol-test-synthesizer-v1"]

    async def execute_inference(self, request: InferenceRequest) -> InferenceResponse:
        """Synthesizes valid deterministic JSON matching ExperiencePlan requirements."""
        t0 = time.perf_counter()
        intent = request.user_content.lower()

        # Build schema-compliant layout plan
        plan_dict = {
            "mode": "FULL_WORKSPACE",
            "title": "Model-Directed Analytical Workspace",
            "subtitle": "Synthesized via deterministic test synthesizer adapter",
            "components": [
                {
                    "id": "metric_strip_main",
                    "type": "metric_strip",
                    "props": {
                        "metrics": [
                            {"label": "Inference Origin", "value": "TEST_SYNTHESIZED", "badge_color": "gray"},
                            {"label": "Engine Status", "value": "SYNTHETIC_VERIFIED", "badge_color": "blue"},
                        ]
                    }
                },
                {
                    "id": "research_grid_main",
                    "type": "data_grid",
                    "props": {
                        "title": "Synthesized Intelligence Records",
                        "columns": [
                            {"key": "entity", "header": "Entity", "type": "text"},
                            {"key": "metric", "header": "Metric", "type": "badge"},
                        ],
                        "rows": [
                            {"entity": "Simulated Record A", "metric": "Active"},
                            {"entity": "Simulated Record B", "metric": "Verified"},
                        ],
                        "placeholder_count": 0,
                    }
                }
            ]
        }

        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        usage = UsageMetadata(
            prompt_tokens=len(request.user_content) // 4,
            completion_tokens=150,
            total_tokens=(len(request.user_content) // 4) + 150,
            usage_type="SIMULATED",
            is_estimated=True,
        )

        return InferenceResponse(
            raw_text=str(plan_dict),
            parsed_json=plan_dict,
            usage=usage,
            latency_ms=latency_ms,
            transport_ms=0.1,
            model_name=self.config.default_model,
            provider_id=self.config.provider_id,
            provider_type=ProviderType.MOCK,
            is_trusted_foundation_model=False,
            trust_reason="Explicit mock test synthesizer (TEST_SYNTHESIZED)",
        )
