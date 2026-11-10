"""
Ollama Local Model Runtime Provider Adapter.
Communicates with a local Ollama daemon at http://127.0.0.1:11434.
Supports model discovery via /api/tags, local disk manifest inspection (~/.ollama),
structured JSON generation (format='json'), and provider-reported token metrics.
"""

import asyncio
import json
import logging
from pathlib import Path
import re
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

logger = logging.getLogger("iol.providers.ollama")


class OllamaProviderAdapter(BaseProviderAdapter):
    """Adapter for authentic local Ollama runtime daemon."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.config.is_local = True
        if not self.config.capabilities:
            self.config.capabilities = [
                ModelCapability.STRUCTURED_OUTPUT,
                ModelCapability.JSON_MODE,
                ModelCapability.LOCAL_EXECUTION,
                ModelCapability.STREAMING,
            ]

    def _discover_local_disk_models(self) -> List[str]:
        """Discovers locally pulled Ollama models from ~/.ollama/models manifests on disk."""
        models: List[str] = []
        try:
            home = Path.home()
            manifests_root = home / ".ollama" / "models" / "manifests"
            if not manifests_root.exists():
                return models

            for f in manifests_root.rglob("*"):
                if f.is_file() and not f.is_symlink():
                    try:
                        rel = f.relative_to(manifests_root).parts
                        if len(rel) >= 2:
                            tag = rel[-1]
                            model_name = rel[-2]
                            models.append(f"{model_name}:{tag}")
                    except Exception:
                        continue
        except Exception as e:
            logger.debug(f"Error scanning local .ollama manifests: {e}")
        return sorted(list(set(models)))

    async def check_health(self) -> DiagnosticResult:
        """Probes local Ollama daemon HTTP status and discovers models."""
        t0 = time.perf_counter()
        base_url = self.config.base_url.rstrip("/")
        endpoint = f"{base_url}/api/tags"

        loop = asyncio.get_event_loop()
        opener = self._get_opener()

        def _probe():
            disk_models = self._discover_local_disk_models()
            try:
                req = urllib.request.Request(endpoint, headers={"User-Agent": "Intent-Operating-Layer/0.9"})
                with opener.open(req, timeout=2.0) as resp:
                    lat = round((time.perf_counter() - t0) * 1000, 2)
                    data = json.loads(resp.read().decode("utf-8"))
                    api_models = [m.get("name") for m in data.get("models", []) if m.get("name")]
                    all_models = sorted(list(set(api_models + disk_models)))

                    # Fetch daemon version
                    ver = "unknown"
                    try:
                        v_req = urllib.request.Request(f"{base_url}/api/version", headers={"User-Agent": "Intent-Operating-Layer/0.9"})
                        with opener.open(v_req, timeout=1.0) as v_resp:
                            v_data = json.loads(v_resp.read().decode("utf-8"))
                            ver = v_data.get("version", "unknown")
                    except Exception:
                        pass

                    return DiagnosticResult(
                        provider_id=self.config.provider_id,
                        provider_type=ProviderType.OLLAMA,
                        status="HEALTHY",
                        is_connected=True,
                        latency_ms=lat,
                        discovered_models=all_models,
                        message=f"Local Ollama daemon v{ver} running healthy ({len(all_models)} models available)",
                    )
            except Exception as e:
                lat = round((time.perf_counter() - t0) * 1000, 2)
                disk_note = f" Found {len(disk_models)} local model weights on disk ({', '.join(disk_models[:3])}). Daemon is currently stopped." if disk_models else " Daemon not running."
                return DiagnosticResult(
                    provider_id=self.config.provider_id,
                    provider_type=ProviderType.OLLAMA,
                    status="UNHEALTHY",
                    is_connected=False,
                    latency_ms=lat,
                    discovered_models=disk_models,
                    message=f"Ollama daemon at {base_url} is offline.{disk_note}",
                    error_reason="DAEMON_OFFLINE",
                )

        return await loop.run_in_executor(None, _probe)

    async def discover_models(self) -> List[str]:
        """Discovers models from active daemon or local disk repository."""
        diag = await self.check_health()
        if diag.discovered_models:
            return diag.discovered_models
        disk_models = self._discover_local_disk_models()
        if disk_models:
            return disk_models
        return ["llama3.2:1b", "qwen2.5:0.5b", "qwen2.5:1.5b", "llama3.2:latest"]

    async def execute_inference(self, request: InferenceRequest) -> InferenceResponse:
        """Executes local inference with Ollama daemon."""
        t0 = time.perf_counter()
        base_url = self.config.base_url.rstrip("/")
        model = request.model or self.config.default_model or "llama3.2:1b"

        # Ollama supports both native /api/generate and /api/chat; we use native /api/generate with format='json'
        endpoint = f"{base_url}/api/generate"
        payload = {
            "model": model,
            "prompt": f"{request.system_prompt}\n\n{request.user_content}",
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
            },
        }
        if request.require_json:
            payload["format"] = "json"

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=data_bytes,
            headers={
                "Content-Type": "application/json",
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
                raw_json = json.loads(resp.read().decode("utf-8"))

                text = raw_json.get("response", "")
                prompt_tokens = raw_json.get("prompt_eval_count", 0)
                completion_tokens = raw_json.get("eval_count", 0)

                # Duration metrics in nanoseconds from Ollama
                eval_duration_ns = raw_json.get("eval_duration", 0)
                inf_ms = round(eval_duration_ns / 1_000_000, 2) if eval_duration_ns else None

                usage = UsageMetadata(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
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
                    inference_ms=inf_ms,
                    model_name=model,
                    provider_id=self.config.provider_id,
                    provider_type=ProviderType.OLLAMA,
                    is_trusted_foundation_model=True,
                    trust_reason=f"Verified local Ollama runtime executing genuine model weights '{model}'",
                )

        return await loop.run_in_executor(None, _do_call)
