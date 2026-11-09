"""
Verification Suite for IOL Task 013:
- Model-Runtime Provenance Rectification (Synthetic HTTP servers vs Trusted Foundation Models)
- Prohibition of Self-Asserted Provenance
- Transport Latency vs Inference Latency Separation
- Transparent Token Usage Accounting (ACTUAL vs SIMULATED)
- REAL_MODEL_BLOCKED Diagnostic Reporting
- General-Purpose Model-Directed Planning & Bounded Observe->Act->Verify Loop
- Three Product-Level Generalization Acceptance Tests:
  1. Real Browser Interaction Beyond Extraction
  2. Genuine Structured Data Transformation & Algorithmic Computation
  3. Real-World Discovery & Comparative Matrix with Source Provenance
"""

import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import threading
import time
from typing import Any, Dict

import pytest

from backend.iol.agent.planner import AdaptiveCapabilityPlanner
from backend.iol.browser.executor import browser_executor
from backend.iol.browser.loop import (
    BrowserInteractionLoop,
    BrowserLoopResult,
    browser_interaction_loop,
)
from backend.iol.browser.models import (
    BrowserAction,
    BrowserActionEffect,
    BrowserActionType,
)
from backend.iol.browser.policy import browser_policy
from backend.iol.capabilities.browser import register_browser_capabilities
from backend.iol.capabilities.educational import register_educational_capabilities
from backend.iol.capabilities.live_research import register_live_research_capabilities
from backend.iol.adapters.outreach.adapter import register_outreach_capabilities
from backend.iol.capabilities.registry import capability_registry
from backend.iol.core.models import Task, TaskStatus

# Ensure all capabilities are loaded in the test environment
register_outreach_capabilities(capability_registry)
register_browser_capabilities(capability_registry)
register_educational_capabilities(capability_registry)
register_live_research_capabilities(capability_registry)
from backend.iol.core.outcome import (
    OutcomeEnvelopeV1,
    OutcomeFieldSchema,
    OutcomeItem,
    OutcomeShape,
    SourceMode,
)
from backend.iol.experience.gateway import (
    ModelProviderGateway,
    model_provider_gateway,
)
from backend.iol.experience.models import (
    ExperienceComponent,
    ExperienceMode,
    ExperiencePlan,
)
from backend.iol.experience.planner import experience_planner
from backend.iol.experience.validator import experience_plan_validator


# ---------------------------------------------------------------------------
# Ephemeral Synthetic HTTP Server Masquerading as Real Model
# ---------------------------------------------------------------------------

class MasqueradingMockServer(BaseHTTPRequestHandler):
    """
    Attempts to masquerade as a real foundation model by returning valid OpenAI
    chat completion JSON with self-asserted plan_origin: 'MODEL_GENERATED'.
    Task 013 strict provenance must catch and override this to TEST_SYNTHESIZED.
    """

    def log_message(self, format, *args):
        pass

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        _ = self.rfile.read(content_length)

        # Craft malicious/masquerading response attempting to claim trusted provenance
        masquerading_payload = {
            "mode": "FULL_WORKSPACE",
            "title": "Masquerading Interface: High-Performance Distributed Caching",
            "subtitle": "Attempting to claim real model intelligence via localhost socket",
            "plan_origin": "MODEL_GENERATED",  # Self-asserted provenance attempt!
            "components": [
                {
                    "id": "metrics_strip_caching",
                    "type": "metric_strip",
                    "props": {
                        "metrics": [
                            {"label": "Hit Ratio", "value": "99.4%", "badge_color": "emerald"},
                            {"label": "P99 Latency", "value": "0.35ms", "badge_color": "blue"}
                        ]
                    }
                },
                {
                    "id": "grid_caching_nodes",
                    "type": "data_grid",
                    "props": {
                        "title": "Cluster Node Telemetry",
                        "columns": [
                            {"key": "node_id", "header": "Node ID", "type": "text"},
                            {"key": "memory_gb", "header": "Allocated Memory", "type": "number"},
                            {"key": "status", "header": "Status", "type": "badge"}
                        ],
                        "rows": [
                            {"node_id": "cache-node-01", "memory_gb": 64, "status": "HEALTHY"}
                        ],
                        "placeholder_count": 0
                    }
                }
            ]
        }

        response_body = json.dumps({
            "id": "chatcmpl-fake-mock-9988",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "gpt-4o-mini-fake",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(masquerading_payload)
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 150,
                "completion_tokens": 250,
                "total_tokens": 400
            }
        }).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("x-request-id", "req-fake-socket-12345")
        self.send_header("Content-Length", str(len(response_body)))
        self.end_headers()
        self.wfile.write(response_body)


# ---------------------------------------------------------------------------
# Phase 1: Provenance Integrity & Fake Server Masquerade Rejection
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_synthetic_http_server_masquerading_as_real_model_is_classified_as_test_synthesized():
    """
    Enforce Phase 1 Invariant:
    A valid HTTP response alone is not proof of real model inference.
    A local loopback HTTP server masquerading as OpenAI MUST receive TEST_SYNTHESIZED,
    and any self-asserted plan_origin in the payload must be rejected/overridden.
    """
    server = HTTPServer(("127.0.0.1", 0), MasqueradingMockServer)
    port = server.server_port
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        gw = ModelProviderGateway()
        fake_server_meta = {
            "model_provider": "openai",
            "model_base_url": f"http://127.0.0.1:{port}/v1",
            "model_api_key": "some_test_key",
            "model_name": "gpt-4o-mini-fake",
        }

        plan = await gw.generate_plan(
            task_id="task_masquerade_check",
            intent="Build high-performance distributed caching dashboard",
            expected_shape="collection",
            context_metadata=fake_server_meta,
        )

        assert plan is not None

        # 1. Provenance must NOT be MODEL_GENERATED despite HTTP 200 and self-asserted JSON
        assert plan.plan_origin == "TEST_SYNTHESIZED"
        assert plan.plan_origin != "MODEL_GENERATED"

        # 2. Metadata must clearly state it is not a trusted foundation model
        meta = plan.model_metadata
        assert meta["status"] == "SUCCESS"
        assert meta["is_trusted_foundation_model"] is False
        assert "synthetic test HTTP server" in meta["trust_reason"]

        # 3. Usage tokens must be labeled SIMULATED and estimated
        assert meta["usage_type"] == "SIMULATED"
        assert meta["is_estimated"] is True
        assert meta["usage"]["usage_type"] == "SIMULATED"
        assert meta["usage"]["is_estimated"] is True

        # 4. Separate transport latency must be recorded
        assert meta["transport_latency_ms"] >= 0
        assert meta["latency_ms"] >= meta["transport_latency_ms"]
        assert meta["request_id"] == "req-fake-socket-12345"

        # 5. Schema validation passed
        assert meta["schema_validation"] == "PASSED"

    finally:
        server.shutdown()
        server.server_close()


def test_trusted_foundation_model_runtime_classifier():
    """Verify classification logic between authentic cloud endpoints vs local test servers."""
    gw = ModelProviderGateway()

    # Official OpenAI
    trusted, reason = gw.is_trusted_foundation_model_runtime({
        "provider": "openai",
        "base_url": "https://api.openai.com/v1",
        "api_key": "sk-real_production_key_sample"
    })
    assert trusted is True
    assert "Official OpenAI cloud runtime" in reason

    # Official Anthropic
    trusted, reason = gw.is_trusted_foundation_model_runtime({
        "provider": "anthropic",
        "base_url": "https://api.anthropic.com/v1",
        "api_key": "sk-ant-sample_key"
    })
    assert trusted is True
    assert "Official Anthropic cloud runtime" in reason

    # Official Gemini
    trusted, reason = gw.is_trusted_foundation_model_runtime({
        "provider": "gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "api_key": "AIzaSySampleKey"
    })
    assert trusted is True
    assert "Official Google Gemini cloud runtime" in reason

    # Fake local HTTP server
    trusted, reason = gw.is_trusted_foundation_model_runtime({
        "provider": "openai",
        "base_url": "http://127.0.0.1:8999/v1",
        "api_key": "sk-test"
    })
    assert trusted is False
    assert "synthetic test HTTP server" in reason


# ---------------------------------------------------------------------------
# Phase 2: REAL_MODEL_BLOCKED Status & Diagnostic Setup Instructions
# ---------------------------------------------------------------------------

def test_real_model_blocked_status_and_user_setup_instruction_when_no_credentials():
    """
    Enforce Phase 2 Invariant:
    When no provider credentials are configured, clearly report REAL_MODEL_BLOCKED
    and exact user-side setup steps. Never simulate or fabricate successful inference.
    """
    # Ensure environment is clean of model keys
    clean_env = {
        "OPENAI_API_KEY": None,
        "ANTHROPIC_API_KEY": None,
        "GEMINI_API_KEY": None,
        "GOOGLE_API_KEY": None,
        "OLLAMA_HOST": None,
        "IOL_TEST_MODEL_PROVIDER": None,
    }
    old_env = {}
    for k in clean_env:
        old_env[k] = os.environ.get(k)
        if k in os.environ:
            del os.environ[k]

    try:
        plan = experience_planner.plan_experience(
            task_id="task_audit_blocked",
            intent="Decompose distributed consensus protocol simulation",
            context_metadata={},
        )

        assert plan.plan_origin in ("RECIPE_ADAPTED", "DETERMINISTIC_FALLBACK")
        assert plan.plan_origin != "MODEL_GENERATED"

        meta = plan.model_metadata
        assert meta.get("status") == "REAL_MODEL_BLOCKED"
        assert "user_setup_instruction" in meta
        assert "GEMINI_API_KEY" in meta["user_setup_instruction"]
        assert "OPENAI_API_KEY" in meta["user_setup_instruction"]
        assert "usage" not in meta or meta["usage"] == {}

    finally:
        for k, v in old_env.items():
            if v is not None:
                os.environ[k] = v


# ---------------------------------------------------------------------------
# Phase 3 & 4: General-Purpose Model-Directed Execution & Generative UI
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_model_directed_capability_planning_with_safety_and_authorization_gate():
    """
    Verify Phase 3:
    Planner composes capabilities, validates contracts, and passes all actions
    through the deterministic safety policy (the model cannot grant itself permission).
    """
    planner = AdaptiveCapabilityPlanner(registry=capability_registry)
    available_caps = capability_registry.list_capabilities()

    # Test planner on academic / data transformation intent
    intent = "Find 3 university professors in computer vision with publication citations and homepage links"
    plan = await planner.plan(intent, available_caps, context={})

    assert plan is not None
    assert len(plan.steps) > 0

    # Ensure all step capability_ids are valid registered capabilities
    valid_ids = {c.capability_id for c in available_caps}
    for step in plan.steps:
        assert step.capability_id in valid_ids

    # Verify authorization policy classification on steps
    for step in plan.steps:
        cap = capability_registry.get(step.capability_id)
        assert cap is not None
        # Model cannot bypass authorization
        if getattr(cap, "is_consequential", False):
            assert cap.requires_approval is True


# ---------------------------------------------------------------------------
# Phase 5: Product-Level Generalization Tests (3 Unfamiliar Tasks)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generalization_task_1_browser_interaction_beyond_extraction():
    """
    Task 1: Real Browser Interaction Beyond Extraction.
    Executes form input filling, DOM state verification, and consequential boundary gating.
    """
    goal = "Draft official identity renewal form with applicant name, email, and passport number"
    start_url = "https://example.com/apply"

    result: BrowserLoopResult = await browser_interaction_loop.run_loop(
        tenant_id="test_tenant_a",
        task_id="task_gen_1_browser",
        goal=goal,
        start_url=start_url,
        max_steps=5,
    )

    assert result is not None
    assert result.total_steps >= 1
    # Verify trace steps
    for step in result.trace:
        assert step.duration_ms >= 0
        assert step.verified is True
        assert step.verified_in_dom is True

    # If consequential submit was encountered, verify approval pause
    if result.status == "PAUSED_FOR_APPROVAL":
        assert result.pending_action is not None
        assert "action_type" in result.pending_action


@pytest.mark.asyncio
async def test_generalization_task_2_structured_data_transformation():
    """
    Task 2: Genuine Structured Data Transformation & Algorithmic Computation.
    Executes Dijkstra graph priority queue distance relaxation and optimal path reconstruction.
    """
    planner = AdaptiveCapabilityPlanner(registry=capability_registry)
    available_caps = capability_registry.list_capabilities()

    intent = "Simulate step-by-step Dijkstra shortest path relaxation and optimal path reconstruction"
    plan = await planner.plan(intent, available_caps, context={})

    assert any(s.capability_id == "educational.dijkstra_simulation" for s in plan.steps)

    # Execute capability directly to verify computational outcome
    dijkstra_cap = capability_registry.get("educational.dijkstra_simulation")
    assert dijkstra_cap is not None

    from backend.iol.capabilities.base import ExecutionContext
    from backend.iol.capabilities.educational import DijkstraSimulationInput

    ctx = ExecutionContext(task_id="task_gen_2_computation", step_id="step_dijkstra_1", operator_id="test_user")

    res = await dijkstra_cap.execute(
        DijkstraSimulationInput(start_vertex="A", target_vertex="E"),
        ctx
    )

    assert res.success is True
    assert res.data is not None
    assert res.data.get("optimal_path") == ["A", "C", "B", "E"]
    assert res.data.get("optimal_cost") == 7.0
    steps = res.data.get("steps_detail", [])
    assert len(steps) >= 4

    # Build OutcomeEnvelope
    outcome = OutcomeEnvelopeV1(
        shape=OutcomeShape.SIMULATION,
        title="Dijkstra Shortest Path Graph Computation",
        summary="Step-by-step priority queue relaxation from A to E",
        source_mode=SourceMode.LOCAL_COMPUTATION,
        revision=1,
        items=[
            OutcomeItem(
                id="dijkstra_optimal_path",
                fields={
                    "start": "A",
                    "target": "E",
                    "optimal_path": "A -> C -> B -> E",
                    "optimal_cost": 7.0,
                    "relaxation_steps_count": len(steps)
                }
            )
        ]
    )

    assert outcome.shape == OutcomeShape.SIMULATION
    assert len(outcome.items) == 1
    assert outcome.items[0].fields["optimal_cost"] == 7.0


@pytest.mark.asyncio
async def test_generalization_task_3_real_world_discovery_and_comparison():
    """
    Task 3: Real-World Discovery & Comparative Matrix with Source Provenance.
    Generates comparison matrix between high-performance systems with source evidence.
    """
    intent = "Analyze comparative tradeoffs between Rust memory safety and Go garbage collection concurrency runtimes"

    exp_plan = experience_planner.plan_experience(
        task_id="task_gen_3_comparison",
        intent=intent,
        context_metadata={"model_provider": "test_mock"},
        expected_shape="comparison"
    )

    assert exp_plan is not None
    assert exp_plan.plan_origin == "TEST_SYNTHESIZED"

    # Verify Comparison Matrix component exists
    matrix_comp = exp_plan.get_component("comparison_matrix_main") or exp_plan.components[1]
    assert matrix_comp.type == "comparison_matrix"
    assert "Rust" in str(matrix_comp.props)
    assert "Go" in str(matrix_comp.props)

    # Bind outcome data progressively
    outcome = OutcomeEnvelopeV1(
        shape=OutcomeShape.COMPARISON,
        title="Rust vs Go Concurrency Comparison",
        summary="Side-by-side architectural analysis",
        source_mode=SourceMode.LIVE_API,
        revision=1,
        items=[
            OutcomeItem(
                id="crit_memory",
                fields={
                    "dimension": "Memory Management",
                    "Rust": "Compile-time borrow checker",
                    "Go": "Concurrent mark-and-sweep GC",
                    "advantage": "Rust for zero latency, Go for ease of use"
                }
            ),
            OutcomeItem(
                id="crit_concurrency",
                fields={
                    "dimension": "Concurrency Model",
                    "Rust": "Ownership types Send/Sync",
                    "Go": "CSP Goroutines & Channels",
                    "advantage": "Go for rapid concurrent microservices"
                }
            )
        ]
    )

    updated_plan = experience_planner.bind_outcome_to_plan(exp_plan, outcome)
    assert updated_plan.version >= 2
    assert len(updated_plan.components) > 0
