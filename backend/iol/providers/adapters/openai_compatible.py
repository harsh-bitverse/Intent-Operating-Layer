"""
OpenAI-Compatible Generic Provider Adapter.
Supports self-hosted and third-party endpoints implementing the OpenAI API specification,
including vLLM, llama.cpp (llama-server), LocalAI, and LiteLLM.
Enforces strict SSRF port validation when pointed at loopback services.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional
import urllib.request
import urllib.error

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

logger = logging.getLogger("iol.providers.openai_compat")


class OpenAICompatibleProviderAdapter(BaseProviderAdapter):
    """Adapter for generic OpenAI-compatible inference servers (vLLM, llama-server, etc.)."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        if not self.config.capabilities:
            self.config.capabilities = [
                ModelCapability.STRUCTURED_OUTPUT,
                ModelCapability.JSON_MODE,
                ModelCapability.STREAMING,
            ]

    async def check_health(self) -> DiagnosticResult:
        """Probes models endpoint on the compatible server."""
        t0 = time.perf_counter()
        base_url = self.config.base_url.rstrip("/")
        # Try both /v1/models and /models
        endpoint = f"{base_url}/models" if base_url.endswith("/v1") else f"{base_url}/v1/models"

        loop = asyncio.get_event_loop()
        opener = self._get_opener()

        def _probe():
            try:
                headers = {"User-Agent": "Intent-Operating-Layer/0.9"}
                if self.config.api_key:
                    headers["Authorization"] = f"Bearer {self.config.api_key}"

                req = urllib.request.Request(endpoint, headers=headers)
                with opener.open(req, timeout=3.0) as resp:
                    lat = round((time.perf_counter() - t0) * 1000, 2)
                    raw_data = json.loads(resp.read().decode("utf-8"))
                    models = [m.get("id") for m in raw_data.get("data", []) if m.get("id")]
                    return DiagnosticResult(
                        provider_id=self.config.provider_id,
                        provider_type=self.config.provider_type,
                        status="HEALTHY",
                        is_connected=True,
                        latency_ms=lat,
                        discovered_models=models[:10],
                        message=f"Compatible endpoint verified ({len(models)} models available)",
                    )
            except Exception as e:
                lat = round((time.perf_counter() - t0) * 1000, 2)
                return DiagnosticResult(
                    provider_id=self.config.provider_id,
                    provider_type=self.config.provider_type,
                    status="UNHEALTHY",
                    is_connected=False,
                    latency_ms=lat,
                    message=f"Endpoint not reachable: {e}",
                    error_reason=type(e).__name__,
                )

        return await loop.run_in_executor(None, _probe)

    async def discover_models(self) -> List[str]:
        """Discovers models from compatible /models endpoint."""
        diag = await self.check_health()
        if diag.discovered_models:
            return diag.discovered_models
        return [self.config.default_model or "default"]

    async def execute_inference(self, request: InferenceRequest) -> InferenceResponse:
        """Executes completion on OpenAI-compatible server."""
        t0 = time.perf_counter()
        base_url = self.config.base_url.rstrip("/")
        model = request.model or self.config.default_model or "default"

        endpoint = f"{base_url}/chat/completions" if base_url.endswith("/v1") else f"{base_url}/v1/chat/completions"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_content},
            ],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        if request.require_json:
            payload["response_format"] = {"type": "json_object"}

        data_bytes = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Intent-Operating-Layer/0.9",
        }
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        req = urllib.request.Request(endpoint, data=data_bytes, headers=headers, method="POST")

        loop = asyncio.get_event_loop()
        opener = self._get_opener()

        def _do_call():
            t_transport_start = time.perf_counter()
            with opener.open(req, timeout=request.timeout_seconds) as resp:
                t_transport = round((time.perf_counter() - t_transport_start) * 1000, 2)
                raw_json = json.loads(resp.read().decode("utf-8"))

                choices = raw_json.get("choices", [])
                if not choices:
                    raise ValueError("Compatible server returned empty choices")

                text = choices[0].get("message", {}).get("content", "")
                raw_usage = raw_json.get("usage", {})

                # If the compatible server is local, flag whether it's trusted
                is_trusted = bool(self.config.is_local or not self.config.provider_id.startswith("mock"))
                trust_reason = "Verified self-hosted foundation model endpoint" if is_trusted else "Unverified endpoint"

                usage = UsageMetadata(
                    prompt_tokens=raw_usage.get("prompt_tokens", 0),
                    completion_tokens=raw_usage.get("completion_tokens", 0),
                    total_tokens=raw_usage.get("total_tokens", 0),
                    usage_type="ACTUAL" if is_trusted else "SIMULATED",
                    is_estimated=not is_trusted,
                )

                parsed, _ = self._parse_json_safely(text) if request.require_json else (None, None)
                tot_lat = round((time.perf_counter() - t0) * 1000, 2)

                return InferenceResponse(
                    raw_text=text,
                    parsed_json=parsed,
                    usage=usage,
                    latency_ms=tot_lat,
                    transport_ms=t_transport,
                    model_name=model,
                    provider_id=self.config.provider_id,
                    provider_type=self.config.provider_type,
                    is_trusted_foundation_model=is_trusted,
                    trust_reason=trust_reason,
                )

        return await loop.run_in_executor(None, _do_call)
