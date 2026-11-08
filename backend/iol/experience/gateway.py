"""
Model Provider Gateway for IOL Experience Engine.
Invokes foundation model inference with strict JSON schema guardrails for generative workspace creation.
Gracefully falls back to recipe adaptation when no API key is configured or inference fails,
guaranteeing that fallbacks are never falsely labeled as MODEL_GENERATED.
"""

from datetime import datetime, timezone
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple
import urllib.request
import urllib.error

from backend.iol.experience.models import ExperienceComponent, ExperienceMode, ExperiencePlan
from backend.iol.experience.validator import experience_plan_validator

logger = logging.getLogger("iol.experience.gateway")

CATALOG_SCHEMA_SUMMARY = """
Allowed component types and required prop structure:
1. workspace_layout: { "layout": "grid" | "stacked" | "split" }
2. metric_strip: { "metrics": [ { "label": string, "value": string | number, "badge_color": "blue"|"green"|"emerald"|"purple"|"amber"|"cyan"|"gray" } ] }
3. data_grid: { "title": string, "columns": [ { "key": string, "header": string, "type": "text"|"badge"|"number"|"link"|"score" } ], "rows": list[dict], "placeholder_count": int }
4. comparison_matrix: { "title": string, "columns": list[dict], "rows": list[dict] }
5. interactive_canvas_2d: { "title": string, "architecture": dict, "nodes": list, "edges": list, "steps_detail": list }
6. form_draft: { "title": string, "status": "LOCAL_DRAFT", "official_portal_url": string, "fields": list[dict] }
7. timeline_view: { "title": string, "items": list[dict] }
8. action_panel: { "action_type": string, "effect": string, "target_url": string, "explanation": string, "parameters": dict }

Constraints:
- Root component must be workspace_layout, metric_strip, or data_grid.
- Max 15 components. Max tree depth 4.
- No <script> tags or executable javascript in props.
"""


class ModelProviderGateway:
    """
    Manages structured model inference for ExperiencePlan synthesis.
    Supports OpenAI, Anthropic, Gemini, or local OpenAI-compatible endpoints (Ollama/vLLM).
    """

    def __init__(self):
        self.default_timeout_seconds = 5.0

    def get_configured_provider(self, context_metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, str]]:
        """
        Determines if an inference provider is configured via environment or task metadata.
        Does NOT log or expose the secret key.
        """
        meta = context_metadata or {}

        # 1. Check user-supplied metadata
        if meta.get("model_api_key"):
            return {
                "provider": meta.get("model_provider", "openai_compatible"),
                "api_key": meta["model_api_key"],
                "base_url": meta.get("model_base_url", "https://api.openai.com/v1"),
                "model": meta.get("model_name", "gpt-4o-mini"),
            }

        # 2. Check environment variables
        if os.environ.get("OPENAI_API_KEY"):
            return {
                "provider": "openai",
                "api_key": os.environ["OPENAI_API_KEY"],
                "base_url": os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                "model": os.environ.get("IOL_EXP_MODEL", "gpt-4o-mini"),
            }

        if os.environ.get("ANTHROPIC_API_KEY"):
            return {
                "provider": "anthropic",
                "api_key": os.environ["ANTHROPIC_API_KEY"],
                "base_url": "https://api.anthropic.com/v1",
                "model": os.environ.get("IOL_EXP_MODEL", "claude-3-5-haiku-20241022"),
            }

        # 3. Check local Ollama or OpenAI-compatible local proxy
        if os.environ.get("OLLAMA_HOST"):
            return {
                "provider": "ollama",
                "api_key": "ollama_local",
                "base_url": f"{os.environ['OLLAMA_HOST'].rstrip('/')}/v1",
                "model": os.environ.get("IOL_EXP_MODEL", "llama3.2"),
            }

        return None

    async def generate_plan(
        self,
        task_id: str,
        intent: str,
        expected_shape: str = "collection",
        context_metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[ExperiencePlan]:
        """
        Attempts model-directed synthesis of an ExperiencePlan.
        Returns a validated ExperiencePlan with plan_origin="MODEL_GENERATED" on success,
        or None if no provider is configured or inference fails.
        """
        provider_info = self.get_configured_provider(context_metadata)
        if not provider_info:
            logger.info("No LLM provider configured for experience planning; using recipe adaptation.")
            return None

        t0 = time.perf_counter()
        try:
            call_result = await self._call_provider(provider_info, intent, expected_shape)
            if not call_result:
                return None

            raw_plan_dict, usage_info = call_result

            # Add required identifiers if missing
            raw_plan_dict["task_id"] = task_id
            if "plan_id" not in raw_plan_dict:
                raw_plan_dict["plan_id"] = f"exp_model_{int(time.time())}"
            raw_plan_dict["status"] = "ACTIVE"
            raw_plan_dict["plan_origin"] = "MODEL_GENERATED"
            raw_plan_dict["version"] = 1

            latency_ms = round((time.perf_counter() - t0) * 1000, 2)
            raw_plan_dict["model_metadata"] = {
                "provider": provider_info["provider"],
                "model": provider_info.get("model", "unknown"),
                "status": "SUCCESS",
                "latency_ms": latency_ms,
                "usage": usage_info or {},
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

            # Parse and strictly validate against the catalog
            plan = ExperiencePlan(**raw_plan_dict)
            is_valid, validation_errors = experience_plan_validator.validate_plan(plan)
            if not is_valid:
                logger.warning(
                    f"Model-generated ExperiencePlan failed schema validation: {validation_errors}. "
                    "Rejecting untrusted plan."
                )
                return None

            return plan

        except Exception as e:
            logger.warning(f"Experience model generation failed or timed out: {e}")
            return None

    async def _call_provider(
        self,
        provider_info: Dict[str, str],
        intent: str,
        expected_shape: str,
    ) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
        """Makes an HTTP POST request to the provider endpoint with JSON schema output prompt."""
        system_prompt = (
            "You are the Intent Operating Layer Experience Planner. "
            "Your job is to generate a declarative JSON ExperiencePlan for a user intent.\n"
            f"{CATALOG_SCHEMA_SUMMARY}\n"
            "Return strictly valid JSON conforming to the ExperiencePlan model: "
            "{ 'mode': 'FULL_WORKSPACE'|'INLINE_VISUAL', 'title': str, 'subtitle': str, 'components': [ {'id': str, 'type': str, 'props': dict} ] }."
        )

        user_content = (
            f"User Intent: {intent}\n"
            f"Expected Outcome Shape: {expected_shape}\n"
            "Generate an optimal ExperiencePlan layout with appropriate metric_strip and data_grid/comparison_matrix."
        )

        base_url = provider_info.get("base_url", "https://api.openai.com/v1").rstrip("/")
        api_key = provider_info.get("api_key", "")
        model = provider_info.get("model", "gpt-4o-mini")
        provider_type = provider_info.get("provider", "openai")

        # Test/Mock provider for verified offline integration testing
        if provider_type in ("mock", "test_mock"):
            mock_plan = {
                "mode": "FULL_WORKSPACE",
                "title": f"Generative Workspace: {intent[:50]}",
                "subtitle": f"Model-directed workspace tailored for {expected_shape} outcomes",
                "components": [
                    {
                        "id": "model_metrics_strip",
                        "type": "metric_strip",
                        "props": {
                            "metrics": [
                                {"label": "Synthesis Status", "value": "MODEL_GENERATED", "badge_color": "emerald"},
                                {"label": "Target Shape", "value": expected_shape.upper(), "badge_color": "blue"},
                                {"label": "Interactive Controls", "value": "ENABLED", "badge_color": "purple"}
                            ]
                        }
                    },
                    {
                        "id": "model_data_grid",
                        "type": "data_grid",
                        "props": {
                            "title": "Autonomous Model Intelligence Grid",
                            "columns": [
                                {"key": "name", "header": "Synthesized Attribute", "type": "text"},
                                {"key": "value", "header": "Model Assessment", "type": "text"},
                                {"key": "confidence", "header": "Inference Confidence", "type": "score"},
                                {"key": "status", "header": "Status", "type": "badge"}
                            ],
                            "rows": [
                                {"name": "Inference Engine", "value": model, "confidence": 0.98, "status": "VERIFIED"},
                                {"name": "Intent Context", "value": intent[:40], "confidence": 0.95, "status": "ALIGNED"},
                            ],
                            "placeholder_count": 0
                        }
                    }
                ]
            }
            return mock_plan, {"prompt_tokens": 120, "completion_tokens": 180, "total_tokens": 300}

        import asyncio
        loop = asyncio.get_event_loop()

        if provider_type == "anthropic":
            endpoint = f"{base_url}/messages"
            payload = {
                "model": model,
                "max_tokens": 1500,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_content}],
            }
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "User-Agent": "Intent-Operating-Layer/0.9",
                },
                method="POST",
            )

            def _do_anthropic():
                with urllib.request.urlopen(req, timeout=self.default_timeout_seconds) as resp:
                    res_data = json.loads(resp.read().decode("utf-8"))
                    text = res_data["content"][0]["text"].strip()
                    if text.startswith("```"):
                        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                    usage = res_data.get("usage", {})
                    return json.loads(text), {
                        "prompt_tokens": usage.get("input_tokens", 0),
                        "completion_tokens": usage.get("output_tokens", 0),
                        "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
                    }

            return await loop.run_in_executor(None, _do_anthropic)

        else:
            # OpenAI / OpenAI-compatible endpoint
            endpoint = f"{base_url}/chat/completions"
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.2,
                "max_tokens": 1500,
            }

            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                    "User-Agent": "Intent-Operating-Layer/0.9",
                },
                method="POST",
            )

            def _do_openai():
                with urllib.request.urlopen(req, timeout=self.default_timeout_seconds) as resp:
                    res_data = json.loads(resp.read().decode("utf-8"))
                    content = res_data["choices"][0]["message"]["content"].strip()
                    if content.startswith("```"):
                        content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                    usage = res_data.get("usage", {})
                    return json.loads(content), {
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0),
                    }

            return await loop.run_in_executor(None, _do_openai)


model_provider_gateway = ModelProviderGateway()
