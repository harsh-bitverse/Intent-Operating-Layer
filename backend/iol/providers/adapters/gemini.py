"""
Google Gemini Native API Provider Adapter.
Communicates directly with Google's Generative Language API using documented
x-goog-api-key headers, structured JSON schemas, and usage telemetry extraction.
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

logger = logging.getLogger("iol.providers.gemini")


class GeminiProviderAdapter(BaseProviderAdapter):
    """Adapter for Google Gemini API (Google AI Studio / Generative Language API)."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        if not self.config.capabilities:
            self.config.capabilities = [
                ModelCapability.STRUCTURED_OUTPUT,
                ModelCapability.JSON_MODE,
                ModelCapability.MULTIMODAL,
                ModelCapability.STREAMING,
                ModelCapability.TOOL_CALLING,
            ]

    async def check_health(self) -> DiagnosticResult:
        """Probes Gemini API models endpoint using x-goog-api-key."""
        t0 = time.perf_counter()
        base_url = self.config.base_url.rstrip("/")
        api_key = self.config.api_key or ""
        endpoint = f"{base_url}/models"

        if not api_key:
            return DiagnosticResult(
                provider_id=self.config.provider_id,
                provider_type=ProviderType.GEMINI,
                status="BLOCKED",
                is_connected=False,
                message="No GEMINI_API_KEY configured",
                error_reason="MISSING_CREDENTIALS",
            )

        req = urllib.request.Request(
            endpoint,
            headers={
                "User-Agent": "Intent-Operating-Layer/0.9",
                "x-goog-api-key": api_key,
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
                    models = [m.get("name", "").replace("models/", "") for m in data.get("models", [])]
                    return DiagnosticResult(
                        provider_id=self.config.provider_id,
                        provider_type=ProviderType.GEMINI,
                        status="HEALTHY",
                        is_connected=True,
                        latency_ms=lat,
                        discovered_models=models[:10],
                        message=f"Gemini API verified healthy ({len(models)} models available)",
                    )
            except urllib.error.HTTPError as e:
                lat = round((time.perf_counter() - t0) * 1000, 2)
                err_body = e.read().decode("utf-8", errors="replace")
                try:
                    err_json = json.loads(err_body).get("error", {})
                    reason = err_json.get("message") or str(e)
                except Exception:
                    reason = str(e)
                return DiagnosticResult(
                    provider_id=self.config.provider_id,
                    provider_type=ProviderType.GEMINI,
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
                    provider_type=ProviderType.GEMINI,
                    status="UNHEALTHY",
                    is_connected=False,
                    latency_ms=lat,
                    message=f"Connection failure: {e}",
                    error_reason=type(e).__name__,
                )

        return await loop.run_in_executor(None, _probe)

    async def discover_models(self) -> List[str]:
        """Discovers available models from the Google Generative Language API."""
        diag = await self.check_health()
        if diag.is_connected and diag.discovered_models:
            return diag.discovered_models
        # Return standard recommended models if discovery call fails or unconfigured
        return ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-4-argon", "gemini-2.5-flash"]

    async def execute_inference(self, request: InferenceRequest) -> InferenceResponse:
        """Executes native Gemini completion with structured output."""
        t0 = time.perf_counter()
        base_url = self.config.base_url.rstrip("/")
        api_key = self.config.api_key or ""
        model = request.model or self.config.default_model or "gemini-3.8-flash"

        endpoint = f"{base_url}/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{request.system_prompt}\n\n{request.user_content}"}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens,
            }
        }
        if request.require_json:
            payload["generationConfig"]["responseMimeType"] = "application/json"

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=data_bytes,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": api_key,
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
                req_id = resp_headers.get("x-goog-request-id") or resp_headers.get("request-id")
                raw_json = json.loads(resp.read().decode("utf-8"))

                candidates = raw_json.get("candidates", [])
                if not candidates or "content" not in candidates[0]:
                    raise ValueError("Gemini returned response without candidate content")

                text = candidates[0]["content"]["parts"][0]["text"]
                usage_meta = raw_json.get("usageMetadata", {})

                usage = UsageMetadata(
                    prompt_tokens=usage_meta.get("promptTokenCount", 0),
                    completion_tokens=usage_meta.get("candidatesTokenCount", 0),
                    total_tokens=usage_meta.get("totalTokenCount", 0),
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
                    request_id=req_id,
                    model_name=model,
                    provider_id=self.config.provider_id,
                    provider_type=ProviderType.GEMINI,
                    is_trusted_foundation_model=True,
                    trust_reason="Official Google Gemini cloud runtime with authenticated token usage",
                )

        return await loop.run_in_executor(None, _do_call)
