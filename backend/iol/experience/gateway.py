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
import re
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

        if meta.get("model_provider") in ("mock", "test_mock"):
            return {
                "provider": meta.get("model_provider"),
                "api_key": "test_mock_key",
                "base_url": "mock://iol",
                "model": meta.get("model_name", "iol-test-synthesizer-v1"),
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

        if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
            return {
                "provider": "gemini",
                "api_key": os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"),
                "base_url": "https://generativelanguage.googleapis.com/v1beta",
                "model": os.environ.get("IOL_EXP_MODEL", "gemini-1.5-flash"),
            }

        # 3. Check local Ollama or OpenAI-compatible local proxy
        if os.environ.get("OLLAMA_HOST"):
            return {
                "provider": "ollama",
                "api_key": "ollama_local",
                "base_url": f"{os.environ['OLLAMA_HOST'].rstrip('/')}/v1",
                "model": os.environ.get("IOL_EXP_MODEL", "llama3.2"),
            }

        # 4. Explicit test provider override
        if os.environ.get("IOL_TEST_MODEL_PROVIDER") in ("mock", "test_mock"):
            return {
                "provider": os.environ["IOL_TEST_MODEL_PROVIDER"],
                "api_key": "test_mock_key",
                "base_url": "mock://iol",
                "model": os.environ.get("IOL_EXP_MODEL", "iol-test-synthesizer-v1"),
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
            is_mock = provider_info.get("provider") in ("mock", "test_mock")
            raw_plan_dict["plan_origin"] = "TEST_SYNTHESIZED" if is_mock else "MODEL_GENERATED"
            raw_plan_dict["version"] = 1

            latency_ms = round((time.perf_counter() - t0) * 1000, 2)
            usage_dict = dict(usage_info) if usage_info else {}
            usage_type = "SIMULATED" if is_mock else "ACTUAL"
            is_estimated = True if is_mock else False
            usage_dict["usage_type"] = usage_type
            usage_dict["is_estimated"] = is_estimated

            raw_plan_dict["model_metadata"] = {
                "provider": provider_info["provider"],
                "model": provider_info.get("model", "unknown"),
                "status": "SUCCESS",
                "latency_ms": latency_ms,
                "usage": usage_dict,
                "usage_type": usage_type,
                "is_estimated": is_estimated,
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
            return self._mock_synthesize_plan(intent, expected_shape, model)

        import asyncio
        loop = asyncio.get_event_loop()

        # For localhost or local Ollama endpoints, build an opener that bypasses any HTTP proxy
        is_local = "127.0.0.1" in base_url or "localhost" in base_url
        def _get_opener():
            if is_local:
                return urllib.request.build_opener(urllib.request.ProxyHandler({}))
            return urllib.request.build_opener()

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
                opener = _get_opener()
                with opener.open(req, timeout=self.default_timeout_seconds) as resp:
                    res_data = json.loads(resp.read().decode("utf-8"))
                    text = res_data["content"][0]["text"].strip()
                    if text.startswith("```"):
                        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                    usage = res_data.get("usage", {})
                    return json.loads(text), {
                        "prompt_tokens": usage.get("input_tokens", 0),
                        "completion_tokens": usage.get("output_tokens", 0),
                        "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
                        "usage_type": "ACTUAL",
                        "is_estimated": False,
                    }

            return await loop.run_in_executor(None, _do_anthropic)

        elif provider_type == "gemini":
            endpoint = f"{base_url}/models/{model}:generateContent?key={api_key}"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": f"{system_prompt}\n\n{user_content}"}
                        ]
                    }
                ],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "temperature": 0.2
                }
            }
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )

            def _do_gemini():
                opener = _get_opener()
                with opener.open(req, timeout=self.default_timeout_seconds) as resp:
                    res_data = json.loads(resp.read().decode("utf-8"))
                    text = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    if text.startswith("```"):
                        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                    usage = res_data.get("usageMetadata", {})
                    return json.loads(text), {
                        "prompt_tokens": usage.get("promptTokenCount", 0),
                        "completion_tokens": usage.get("candidatesTokenCount", 0),
                        "total_tokens": usage.get("totalTokenCount", 0),
                        "usage_type": "ACTUAL",
                        "is_estimated": False,
                    }

            return await loop.run_in_executor(None, _do_gemini)

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
                opener = _get_opener()
                with opener.open(req, timeout=self.default_timeout_seconds) as resp:
                    res_data = json.loads(resp.read().decode("utf-8"))
                    content = res_data["choices"][0]["message"]["content"].strip()
                    if content.startswith("```"):
                        content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                    usage = res_data.get("usage", {})
                    return json.loads(content), {
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0),
                        "usage_type": "ACTUAL",
                        "is_estimated": False,
                    }

            return await loop.run_in_executor(None, _do_openai)

    def _mock_synthesize_plan(
        self, intent: str, expected_shape: str, model: str
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Synthesizes a domain-tailored, schema-compliant ExperiencePlan for test/mock provider mode.
        Dynamically selects components (canvas, matrix, timeline, document, form, grid) based on intent.
        """
        intent_lower = intent.lower()

        # 1. Dijkstra / Algorithm / Graph Simulation
        if any(w in intent_lower for w in ["dijkstra", "shortest path", "graph", "algorithm", "network routing"]):
            plan = {
                "mode": "FULL_WORKSPACE",
                "title": "Algorithm Simulation: Dijkstra Shortest Path",
                "subtitle": "Interactive step-by-step shortest path computation with real-time distance relaxation",
                "components": [
                    {
                        "id": "model_metrics_strip",
                        "type": "metric_strip",
                        "props": {
                            "metrics": [
                                {"label": "Algorithm", "value": "Dijkstra SP", "badge_color": "emerald"},
                                {"label": "Graph Topology", "value": "5 Vertices / 6 Edges", "badge_color": "blue"},
                                {"label": "Source -> Target", "value": "A -> E", "badge_color": "cyan"},
                                {"label": "Optimal Cost", "value": "7", "badge_color": "purple"}
                            ]
                        }
                    },
                    {
                        "id": "model_interactive_canvas",
                        "type": "interactive_canvas_2d",
                        "props": {
                            "title": "Dijkstra Directed Graph Relaxation Canvas",
                            "architecture": {
                                "type": "DIJKSTRA_GRAPH",
                                "source": "A",
                                "target": "E",
                                "vertex_count": 5,
                                "edge_count": 6
                            },
                            "nodes": [
                                {"id": "A", "label": "A (Source)", "layer": "input", "cx": 90, "cy": 160, "val": 0},
                                {"id": "B", "label": "B", "layer": "hidden", "cx": 250, "cy": 80, "val": 3},
                                {"id": "C", "label": "C", "layer": "hidden", "cx": 250, "cy": 240, "val": 2},
                                {"id": "D", "label": "D", "layer": "hidden", "cx": 420, "cy": 80, "val": 8},
                                {"id": "E", "label": "E (Target)", "layer": "output", "cx": 420, "cy": 240, "val": 7}
                            ],
                            "edges": [
                                {"id": "e_AB", "x1": 90, "y1": 160, "x2": 250, "y2": 80, "w": 4, "from": "A", "to": "B"},
                                {"id": "e_AC", "x1": 90, "y1": 160, "x2": 250, "y2": 240, "w": 2, "from": "A", "to": "C"},
                                {"id": "e_CB", "x1": 250, "y1": 240, "x2": 250, "y2": 80, "w": 1, "from": "C", "to": "B"},
                                {"id": "e_BD", "x1": 250, "y1": 80, "x2": 420, "y2": 80, "w": 5, "from": "B", "to": "D"},
                                {"id": "e_BE", "x1": 250, "y1": 80, "x2": 420, "y2": 240, "w": 4, "from": "B", "to": "E"},
                                {"id": "e_CE", "x1": 250, "y1": 240, "x2": 420, "y2": 240, "w": 8, "from": "C", "to": "E"}
                            ],
                            "current_step": 0,
                            "total_steps": 5,
                            "steps_detail": [
                                {
                                    "step_idx": 0,
                                    "phase": "INIT",
                                    "description": "Initialize distance vector: dist(A)=0, all unvisited vertices dist=\u221e.",
                                    "active_layer": "input",
                                    "activations": {"A": 0, "B": 999, "C": 999, "D": 999, "E": 999},
                                    "loss": 0.0,
                                    "weights": {"w_AB": 4, "w_AC": 2, "w_CB": 1, "w_BD": 5, "w_BE": 4, "w_CE": 8},
                                    "formula": "dist[v] = \u221e \u2200 v \u2260 s; dist[A] = 0"
                                },
                                {
                                    "step_idx": 1,
                                    "phase": "RELAX_A",
                                    "description": "Visit A. Relax edge (A,B)=4, (A,C)=2. Next min distance unvisited node is C (dist 2).",
                                    "active_layer": "hidden",
                                    "activations": {"A": 0, "B": 4, "C": 2, "D": 999, "E": 999},
                                    "loss": 0.0,
                                    "weights": {"w_AB": 4, "w_AC": 2, "w_CB": 1, "w_BD": 5, "w_BE": 4, "w_CE": 8},
                                    "formula": "dist[C] = min(\u221e, 0 + 2) = 2; dist[B] = min(\u221e, 0 + 4) = 4"
                                },
                                {
                                    "step_idx": 2,
                                    "phase": "RELAX_C",
                                    "description": "Visit C. Relax (C,B): 2+1=3 < 4 (shorter!). Relax (C,E): 2+8=10. Next min unvisited is B (dist 3).",
                                    "active_layer": "hidden",
                                    "activations": {"A": 0, "B": 3, "C": 2, "D": 999, "E": 10},
                                    "loss": 0.0,
                                    "weights": {"w_AB": 4, "w_AC": 2, "w_CB": 1, "w_BD": 5, "w_BE": 4, "w_CE": 8},
                                    "formula": "dist[B] = min(4, 2 + 1) = 3"
                                },
                                {
                                    "step_idx": 3,
                                    "phase": "RELAX_B",
                                    "description": "Visit B. Relax (B,D): 3+5=8. Relax (B,E): 3+4=7 < 10 (shorter path to target E found!).",
                                    "active_layer": "hidden",
                                    "activations": {"A": 0, "B": 3, "C": 2, "D": 8, "E": 7},
                                    "loss": 0.0,
                                    "weights": {"w_AB": 4, "w_AC": 2, "w_CB": 1, "w_BD": 5, "w_BE": 4, "w_CE": 8},
                                    "formula": "dist[E] = min(10, 3 + 4) = 7"
                                },
                                {
                                    "step_idx": 4,
                                    "phase": "COMPLETED",
                                    "description": "Target E reached. Shortest path is A -> C -> B -> E with total path cost 7.",
                                    "active_layer": "output",
                                    "activations": {"A": 0, "B": 3, "C": 2, "D": 8, "E": 7},
                                    "loss": 0.0,
                                    "weights": {"w_AB": 4, "w_AC": 2, "w_CB": 1, "w_BD": 5, "w_BE": 4, "w_CE": 8},
                                    "formula": "Shortest Path: A \u2192 C \u2192 B \u2192 E (Cost = 7)"
                                }
                            ]
                        }
                    }
                ]
            }
            return plan, {
                "prompt_tokens": 180,
                "completion_tokens": 360,
                "total_tokens": 540,
                "usage_type": "SIMULATED",
                "is_estimated": True,
            }

        # 2. Comparison / Matrix / Versus / Benchmark / Tradeoffs
        elif any(w in intent_lower for w in ["compare", "comparative", "tradeoff", "vs", "versus", "benchmark"]):
            # Extract compared entities if present
            e1, e2 = "Option A", "Option B"
            if " between " in intent_lower and " and " in intent_lower:
                parts = intent_lower.split(" between ", 1)[1].split(" and ", 1)
                e1 = parts[0].strip().split()[0].title()
                e2 = parts[1].strip().split()[0].title()
            elif " vs " in intent_lower:
                parts = intent_lower.split(" vs ", 1)
                e1 = parts[0].strip().split()[-1].title()
                e2 = parts[1].strip().split()[0].title()
            elif " versus " in intent_lower:
                parts = intent_lower.split(" versus ", 1)
                e1 = parts[0].strip().split()[-1].title()
                e2 = parts[1].strip().split()[0].title()
            elif "compare " in intent_lower and " and " in intent_lower:
                parts = intent_lower.replace("compare ", "", 1).split(" and ", 1)
                e1 = parts[0].strip().split()[-1].title()
                e2 = parts[1].strip().split()[0].title()
            elif "vite" in intent_lower and "webpack" in intent_lower:
                e1, e2 = "Vite", "Webpack"

            k1 = re.sub(r"[^a-zA-Z0-9_]", "_", e1.lower())
            k2 = re.sub(r"[^a-zA-Z0-9_]", "_", e2.lower())

            if e1.lower() == "rust" and e2.lower() == "go":
                rows = [
                    {
                        "dimension": "Memory Safety & Runtime Model",
                        k1: "Compile-time affine type system & borrow checker; zero GC runtime overhead",
                        k2: "Concurrent mark-and-sweep garbage collector with ~1ms STW pause guarantees",
                        "advantage": "Rust (Zero Overhead)"
                    },
                    {
                        "dimension": "Concurrency Architecture",
                        k1: "Async/await cooperative state machines via Tokio runtime; fearless multithreading",
                        k2: "M:N green-thread goroutines with channels and work-stealing scheduler",
                        "advantage": "Go (Ergonomic Concurrency)"
                    },
                    {
                        "dimension": "Compilation Target & Binary Footprint",
                        k1: "Native LLVM machine code; minimal embedded/container runtime (<3MB stripped)",
                        k2: "Self-contained static executable with bundled GC runtime (~10-15MB)",
                        "advantage": "Rust"
                    },
                    {
                        "dimension": "Developer Ergonomics & Learning Curve",
                        k1: "Steep learning curve due to explicit lifetimes and borrow checker semantics",
                        k2: "Rapid team onboarding with minimalist specification (25 language keywords)",
                        "advantage": "Go"
                    },
                    {
                        "dimension": "Tail Latency Predictability (P99)",
                        k1: "Deterministic microsecond-level execution without GC collection pauses",
                        k2: "P99 sub-5ms under modern runtime, but occasional GC collection pauses",
                        "advantage": "Rust (Real-Time)"
                    }
                ]
            elif e1.lower() == "vite" and e2.lower() == "webpack":
                rows = [
                    {
                        "dimension": "Dev Server Cold Start",
                        k1: "Instant (~150ms) using native browser ESM and unbundled modules",
                        k2: "Slow (2-15s) requiring full bundle compilation before serving",
                        "advantage": "Vite"
                    },
                    {
                        "dimension": "Hot Module Replacement (HMR)",
                        k1: "Constant O(1) latency independent of codebase size",
                        k2: "Linear O(N) degradation as module graph expands",
                        "advantage": "Vite"
                    },
                    {
                        "dimension": "Build Pipeline Engine",
                        k1: "Rollup for production output, ESBuild for pre-bundling",
                        k2: "Custom Webpack compilation pipeline with mature plugin ecosystem",
                        "advantage": "Webpack (Ecosystem)"
                    },
                    {
                        "dimension": "Legacy Browser Support",
                        k1: "Requires @vitejs/plugin-legacy for non-ESM targets",
                        k2: "Native legacy transpilation via Babel / core-js",
                        "advantage": "Webpack"
                    },
                    {
                        "dimension": "Configuration Complexity",
                        k1: "Zero-config sensible defaults for TypeScript, JSX, CSS modules",
                        k2: "Verbose configuration (loaders, plugins, optimization rules)",
                        "advantage": "Vite"
                    }
                ]
            else:
                rows = [
                    {
                        "dimension": "Core Architecture & Runtime Model",
                        k1: f"Specialized architectural model optimized for {e1} workloads",
                        k2: f"Alternative operational model designed for {e2} paradigms",
                        "advantage": "Domain-Specific"
                    },
                    {
                        "dimension": "Execution Latency & Throughput",
                        k1: f"High-efficiency pipeline tuned for bounded latency in {e1}",
                        k2: f"Distributed or decoupled execution engine for {e2}",
                        "advantage": f"{e1} (Low Latency)"
                    },
                    {
                        "dimension": "Ecosystem Maturity & Tooling",
                        k1: f"Established tooling and library ecosystem supporting {e1}",
                        k2: f"Specialized operational utilities tailored for {e2}",
                        "advantage": "Context-Dependent"
                    },
                    {
                        "dimension": "Resource Consumption & Footprint",
                        k1: f"Optimized memory and compute allocation under {e1}",
                        k2: f"Elastic scaling profile suited for {e2} infrastructure",
                        "advantage": f"{e1}"
                    }
                ]

            plan = {
                "mode": "FULL_WORKSPACE",
                "title": f"Comparative Intelligence: {e1} vs {e2}",
                "subtitle": f"Synthesized multi-dimensional evaluation of {intent[:60]}",
                "components": [
                    {
                        "id": "model_metrics_strip",
                        "type": "metric_strip",
                        "props": {
                            "metrics": [
                                {"label": "Comparison Mode", "value": "EMPIRICAL_BENCHMARK", "badge_color": "emerald"},
                                {"label": "Compared Targets", "value": f"{e1} vs {e2}", "badge_color": "blue"},
                                {"label": "Evaluation Dimensions", "value": f"{len(rows)} Criteria", "badge_color": "purple"}
                            ]
                        }
                    },
                    {
                        "id": "comparison_matrix_main",
                        "type": "comparison_matrix",
                        "props": {
                            "title": f"Architectural & Tradeoff Matrix: {e1} vs {e2}",
                            "columns": [
                                {"key": "dimension", "header": "Evaluation Dimension", "type": "text"},
                                {"key": k1, "header": e1, "type": "text"},
                                {"key": k2, "header": e2, "type": "text"},
                                {"key": "advantage", "header": "Architectural Advantage", "type": "badge"}
                            ],
                            "rows": rows,
                            "placeholder_count": 0
                        }
                    }
                ]
            }
            return plan, {
                "prompt_tokens": 160,
                "completion_tokens": 280,
                "total_tokens": 440,
                "usage_type": "SIMULATED",
                "is_estimated": True,
            }

        # 3. Timeline / Milestones / Workflow / Trajectory
        elif any(w in intent_lower for w in ["timeline", "roadmap", "milestone", "schedule", "lifecycle", "trajectory", "orbital"]):
            if any(w in intent_lower for w in ["orbital", "spacecraft", "trajectory", "delta-v", "mission"]):
                metrics = [
                    {"label": "Mission Phase", "value": "INTERPLANETARY_CRUISE", "badge_color": "emerald"},
                    {"label": "Target Delta-V", "value": "1,240 m/s", "badge_color": "blue"},
                    {"label": "Telemetry Status", "value": "DIRECT_LINK_NOMINAL", "badge_color": "cyan"},
                    {"label": "Trajectory Dispersion", "value": "<0.02%", "badge_color": "purple"}
                ]
                items = [
                    {"id": "s1", "title": "Stage 1: Launch & Trans-Atmospheric Ascent", "status": "completed", "description": "Atmospheric departure and staging verified on telemetry."},
                    {"id": "s2", "title": "Stage 2: Trans-Planetary Injection Burn", "status": "completed", "description": "Upper stage restart and escape velocity achieved (11.2 km/s)."},
                    {"id": "s3", "title": "Stage 3: Deep Space Trajectory Correction (TCM-1/2)", "status": "active", "description": "Attitude thruster fine adjustments to align B-plane arrival coordinates."},
                    {"id": "s4", "title": "Stage 4: Orbital Insertion Main Engine Burn (JOI/MOI)", "status": "pending", "description": "Retro-propulsion burn to capture into target planetary elliptical orbit."},
                    {"id": "s5", "title": "Stage 5: Orbit Circularization & Science Telemetry", "status": "pending", "description": "Aero-braking passes and high-gain science instrument downlink activation."}
                ]
                title = f"Spacecraft Trajectory & Telemetry: {intent[:50]}"
                subtitle = "Sequential orbital insertion stages, propulsion events, and verified telemetry checkpoints"
            else:
                metrics = [
                    {"label": "Current Stage", "value": "IN_PROGRESS", "badge_color": "blue"},
                    {"label": "Completed Phases", "value": "2 of 4", "badge_color": "emerald"},
                    {"label": "Target Milestone", "value": "Production Release", "badge_color": "purple"}
                ]
                items = [
                    {"id": "m1", "title": "Architecture & Schema Freezing", "status": "completed", "description": "Contracts, models, and type definitions established."},
                    {"id": "m2", "title": "Engine Implementation", "status": "completed", "description": "Substrate and planner pipelines wired."},
                    {"id": "m3", "title": "Live Verification & Probes", "status": "active", "description": "Running live browser and calculation probes."},
                    {"id": "m4", "title": "Demonstration Delivery", "status": "pending", "description": "Final package and submission delivery."}
                ]
                title = f"Process Timeline: {intent[:60]}"
                subtitle = "Sequential workflow stages and verifiable phase transitions"

            plan = {
                "mode": "FULL_WORKSPACE",
                "title": title,
                "subtitle": subtitle,
                "components": [
                    {
                        "id": "model_metrics_strip",
                        "type": "metric_strip",
                        "props": {"metrics": metrics}
                    },
                    {
                        "id": "model_timeline",
                        "type": "timeline_view",
                        "props": {
                            "title": "Mission & Stage Transition Tracker",
                            "items": items
                        }
                    }
                ]
            }
            return plan, {
                "prompt_tokens": 130,
                "completion_tokens": 220,
                "total_tokens": 350,
                "usage_type": "SIMULATED",
                "is_estimated": True,
            }

        # 4. Form / Booking / Flight / Portal Handoff
        elif any(w in intent_lower for w in ["form", "flight", "booking", "portal", "airline", "ticket"]):
            plan = {
                "mode": "FULL_WORKSPACE",
                "title": f"Service Discovery & Handoff: {intent[:60]}",
                "subtitle": "Truthful route discovery with supervised execution and safe portal handoff",
                "components": [
                    {
                        "id": "model_metrics_strip",
                        "type": "metric_strip",
                        "props": {
                            "metrics": [
                                {"label": "Service Type", "value": "Flight Route Discovery", "badge_color": "blue"},
                                {"label": "Authorization Level", "value": "HUMAN_SUPERVISED", "badge_color": "amber"},
                                {"label": "Transaction Status", "value": "LOCAL_DRAFT", "badge_color": "purple"}
                            ]
                        }
                    },
                    {
                        "id": "model_form_draft",
                        "type": "form_draft",
                        "props": {
                            "title": "Flight Route & Inquiry Specification",
                            "status": "LOCAL_DRAFT",
                            "official_portal_url": "https://www.airindia.com",
                            "fields": [
                                {"label": "Departure Airport", "name": "origin", "type": "text", "value": "DEL (Indira Gandhi Intl, Delhi)"},
                                {"label": "Arrival Airport", "name": "destination", "type": "text", "value": "BOM (Chhatrapati Shivaji Intl, Mumbai)"},
                                {"label": "Travel Class", "name": "cabin_class", "type": "select", "value": "Economy"},
                                {"label": "Direct Flight Preferred", "name": "direct_only", "type": "checkbox", "value": "true"}
                            ]
                        }
                    },
                    {
                        "id": "model_action_panel",
                        "type": "action_panel",
                        "props": {
                            "action_type": "EXTERNAL_PORTAL_HANDOFF",
                            "effect": "NAVIGATE",
                            "target_url": "https://www.airindia.com",
                            "explanation": "IOL discovered verified route specifications. To complete payment and seat reservation securely, open the official carrier portal.",
                            "parameters": {"origin": "DEL", "destination": "BOM", "cabin": "Economy"}
                        }
                    }
                ]
            }
            return plan, {
                "prompt_tokens": 150,
                "completion_tokens": 250,
                "total_tokens": 400,
                "usage_type": "SIMULATED",
                "is_estimated": True,
            }

        # 5. Document / Report
        elif any(w in intent_lower for w in ["document", "report", "paper", "summary", "article"]):
            plan = {
                "mode": "FULL_WORKSPACE",
                "title": f"Document Synthesis: {intent[:60]}",
                "subtitle": "Synthesized structured document preview with verified references",
                "components": [
                    {
                        "id": "model_metrics_strip",
                        "type": "metric_strip",
                        "props": {
                            "metrics": [
                                {"label": "Document Type", "value": "RESEARCH_BRIEF", "badge_color": "blue"},
                                {"label": "Verified Sections", "value": "3 Sections", "badge_color": "emerald"},
                                {"label": "Status", "value": "SYNTHESIZED", "badge_color": "purple"}
                            ]
                        }
                    },
                    {
                        "id": "model_document_preview",
                        "type": "document_preview",
                        "props": {
                            "title": f"Research Brief: {intent[:50]}",
                            "document_type": "RESEARCH_BRIEF",
                            "sections": [
                                {"heading": "1. Executive Overview", "text": "This synthesis aggregates empirical findings and verified facts directly from primary literature and authoritative databases."},
                                {"heading": "2. Comparative Analysis", "text": "Key differentiators demonstrate clear tradeoffs between developer ergonomics, bundle size, and build latency."},
                                {"heading": "3. Recommendations", "text": "Adopt modern ESM-based tooling for interactive applications while preserving compatibility polyfills for legacy deployments."}
                            ],
                            "metadata": {"Author": "IOL Autonomous Synthesizer", "Standard": "Task 011 Specification"}
                        }
                    }
                ]
            }
            return plan, {
                "prompt_tokens": 140,
                "completion_tokens": 240,
                "total_tokens": 380,
                "usage_type": "SIMULATED",
                "is_estimated": True,
            }

        # Default: Data Grid
        else:
            plan = {
                "mode": "FULL_WORKSPACE",
                "title": f"Generative Workspace: {intent[:50]}",
                "subtitle": f"Model-directed workspace tailored for {expected_shape} outcomes",
                "components": [
                    {
                        "id": "model_metrics_strip",
                        "type": "metric_strip",
                        "props": {
                            "metrics": [
                                {"label": "Synthesis Status", "value": "TEST_SYNTHESIZED", "badge_color": "emerald"},
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
                                {"name": "Intent Context", "value": intent[:40], "confidence": 0.95, "status": "ALIGNED"}
                            ],
                            "placeholder_count": 0
                        }
                    }
                ]
            }
            return plan, {
                "prompt_tokens": 120,
                "completion_tokens": 180,
                "total_tokens": 300,
                "usage_type": "SIMULATED",
                "is_estimated": True,
            }


model_provider_gateway = ModelProviderGateway()
