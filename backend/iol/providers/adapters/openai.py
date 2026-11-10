"""
OpenAI Native API Provider Adapter.
Handles OpenAI endpoints (api.openai.com / Azure OpenAI) with bearer authentication,
JSON mode, latency headers, and verified token metrics.
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

logger = logging.getLogger("iol.providers.openai")


class OpenAIProviderAdapter(BaseProviderAdapter):
    """Adapter for official OpenAI cloud runtime."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        if not self.config.capabilities:
            self.config.capabilities = [
                ModelCapability.STRUCTURED_OUTPUT,
                ModelCapability.JSON_MODE,
                ModelCapability.TOOL_CALLING,
                ModelCapability.STREAMING,
            ]

    async def check_health(self) -> DiagnosticResult:
        """Probes OpenAI models endpoint."""
        t0 = time.perf_counter()
        base_url = self.config.base_url.rstrip("/")
        api_key = self.config.api_key or ""
        endpoint = f"{base_url}/models"

        if not api_key:
            return DiagnosticResult(
                provider_id=self.config.provider_id,
                provider_type=ProviderType.OPENAI,
                status="BLOCKED",
                is_connected=False,
                message="No OPENAI_API_KEY configured",
                error_reason="MISSING_CREDENTIALS",
            )

        req = urllib.request.Request(
            endpoint,
            headers={
                "User-Agent": "Intent-Operating-Layer/0.9",
                "Authorization": f"Bearer {api_key}",
            },
            method="GET",
        )

        loop = asyncio.get_event_loop()
        opener = self._get_opener()

        def _probe():
            try:
                with opener.open(req, timeout=5.0) as resp:
                    lat = round((time.perf_counter() - t0) * 1000, 2)
                    data = json.loads(resp.read().decode("utf-8"))
                    models = [m.get("id") for m in data.get("data", []) if m.get("id")]
                    return DiagnosticResult(
                        provider_id=self.config.provider_id,
                        provider_type=ProviderType.OPENAI,
                        status="HEALTHY",
                        is_connected=True,
                        latency_ms=lat,
                        discovered_models=models[:10],
                        message=f"OpenAI API verified healthy ({len(models)} models available)",
                    )
            except urllib.error.HTTPError as e:
                lat = round((time.perf_counter() - t0) * 1000, 2)
                err_body = e.read().decode("utf-8", errors="replace")
                try:
                    reason = json.loads(err_body).get("error", {}).get("message") or str(e)
                except Exception:
                    reason = str(e)
                return DiagnosticResult(
                    provider_id=self.config.provider_id,
                    provider_type=ProviderType.OPENAI,
                    status="UNHEALTHY" if e.code != 401 else "BLOCKED",
                    is_connected=False,
                    latency_ms=lat,
                    message=f"HTTP {e.code}: {reason}",
                    error_reason=f"HTTP_{e.code}",
                )
            except Exception as e:
                lat = round((time.perf_counter() - t0) * 1000, 2)
                return DiagnosticResult(
                    provider_id=self.config.provider_id,
                    provider_type=ProviderType.OPENAI,
                    status="UNHEALTHY",
                    is_connected=False,
                    latency_ms=lat,
                    message=f"Connection failure: {e}",
                    error_reason=type(e).__name__,
                )

        return await loop.run_in_executor(None, _probe)

    async def discover_models(self) -> List[str]:
        """Discovers available models from OpenAI."""
        diag = await self.check_health()
        if diag.is_connected and diag.discovered_models:
            return diag.discovered_models
        return ["gpt-4o-mini", "gpt-4o", "o1", "o3-mini"]

    async def execute_inference(self, request: InferenceRequest) -> InferenceResponse:
        """Executes OpenAI chat completion."""
        t0 = time.perf_counter()
        base_url = self.config.base_url.rstrip("/")
        api_key = self.config.api_key or ""
        model = request.model or self.config.default_model or "gpt-4o-mini"

        endpoint = f"{base_url}/chat/completions"
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
        req = urllib.request.Request(
            endpoint,
            data=data_bytes,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "User-Agent": "Intent-Operating-Layer/0.9",
            },
            method="POST",
        )

        loop = asyncio.get_event_loop()
        opener = self._get_opener()

        def _do_call():
            t_transport_start = time.perf_counter()
            with opener.open(req, timeout=request.timeout_seconds) as resp:
                t_transport = round((time.perf_counter() - t_transport_start) * 1000, 2)
                resp_headers = dict(resp.headers)
                req_id = resp_headers.get("x-request-id") or resp_headers.get("request-id")
                inf_latency = None
                if "openai-processing-ms" in resp_headers:
                    try:
                        inf_latency = float(resp_headers["openai-processing-ms"])
                    except Exception:
                        pass

                raw_json = json.loads(resp.read().decode("utf-8"))
                choices = raw_json.get("choices", [])
                if not choices or "message" not in choices[0]:
                    raise ValueError("OpenAI returned response without choices")

                text = choices[0]["message"].get("content", "")
                raw_usage = raw_json.get("usage", {})

                usage = UsageMetadata(
                    prompt_tokens=raw_usage.get("prompt_tokens", 0),
                    completion_tokens=raw_usage.get("completion_tokens", 0),
                    total_tokens=raw_usage.get("total_tokens", 0),
                    usage_type="ACTUAL",
                    is_estimated=False,
                )

                parsed, _ = self._parse_json_safely(text) if request.require_json else (None, None)
                tot_lat = round((time.perf_counter() - t0) * 1000, 2)

                return InferenceResponse(
                    raw_text=text,
                    parsed_json=parsed,
                    usage=usage,
                    latency_ms=tot_lat,
                    transport_ms=t_transport,
                    inference_ms=inf_latency,
                    request_id=req_id,
                    model_name=model,
                    provider_id=self.config.provider_id,
                    provider_type=ProviderType.OPENAI,
                    is_trusted_foundation_model=True,
                    trust_reason="Official OpenAI cloud runtime with authenticated token usage",
                )

        return await loop.run_in_executor(None, _do_call)
