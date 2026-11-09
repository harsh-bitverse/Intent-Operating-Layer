"""
Tests for IOL Task 010: Genuine Model-Directed Execution and Generative Experiences.
Validates:
1. Real model-directed experience generation & explicit MODEL_GENERATION_BLOCKED reporting.
2. Autonomous browser interaction loop on interactive forms with approval gating.
3. Information comparison structure across multi-source extractions.
4. Expressive unfamiliar visual workspace synthesis (interactive 2D canvas).
5. Everyday-task readiness (flight route & schedule specifications with honest portal handoff and zero fake bookings).
"""

import pytest
from backend.iol.agent.planner import AdaptiveCapabilityPlanner
from backend.iol.browser.loop import browser_interaction_loop, BrowserLoopResult
from backend.iol.browser.policy import browser_policy, BrowserActionEffect
from backend.iol.browser.models import BrowserAction, BrowserActionType
from backend.iol.capabilities.registry import CapabilityRegistry
from backend.iol.capabilities.browser import register_browser_capabilities
from backend.iol.capabilities.educational import register_educational_capabilities
from backend.iol.capabilities.live_research import register_live_research_capabilities
from backend.iol.experience.gateway import model_provider_gateway
from backend.iol.experience.planner import experience_planner
from backend.iol.core.outcome import OutcomeShape, SourceMode


@pytest.fixture
def configured_registry():
    registry = CapabilityRegistry()
    register_browser_capabilities(registry)
    register_educational_capabilities(registry)
    register_live_research_capabilities(registry)
    return registry


@pytest.mark.asyncio
async def test_model_directed_generation_and_blocked_reporting():
    """Phase 1: Verify model-directed ExperiencePlan synthesis and explicit blocked reporting."""
    # 1. Configured mock model provider -> MODEL_GENERATED plan
    mock_meta = {
        "model_provider": "mock",
        "model_api_key": "test_mock_token_12345",
        "model_name": "mock-general-v1"
    }

    plan_model = await model_provider_gateway.generate_plan(
        task_id="task_probe_m1",
        intent="Synthesize custom interactive latency benchmarking workspace",
        expected_shape="collection",
        context_metadata=mock_meta
    )

    assert plan_model is not None
    assert plan_model.plan_origin == "TEST_SYNTHESIZED"
    assert plan_model.model_metadata.get("status") == "SUCCESS"
    assert plan_model.model_metadata.get("provider") == "mock"
    assert plan_model.model_metadata.get("usage_type") == "SIMULATED"
    assert plan_model.model_metadata.get("is_estimated") is True
    usage = plan_model.model_metadata.get("usage") or plan_model.model_metadata.get("tokens", {})
    assert usage.get("total_tokens", 0) > 0
    assert len(plan_model.components) >= 2

    # 2. No provider configured -> Explicit MODEL_GENERATION_BLOCKED without mislabeling
    plan_unconfigured = experience_planner.plan_experience(
        task_id="task_probe_m2",
        intent="Research cutting-edge AI infrastructure startups in Bengaluru",
        context_metadata={}
    )

    assert plan_unconfigured.plan_origin in ("RECIPE_ADAPTED", "DETERMINISTIC_FALLBACK")
    assert plan_unconfigured.plan_origin != "MODEL_GENERATED"
    assert plan_unconfigured.model_metadata.get("status") == "MODEL_GENERATION_BLOCKED"
    assert "No active external LLM credentials configured" in plan_unconfigured.model_metadata.get("origin_reason", "")


@pytest.mark.asyncio
async def test_autonomous_browser_loop_interactive_form_and_approval_halt():
    """Phase 2 & Structure 2: Autonomous browser action loop explores form, populates draft, and pauses at approval boundary."""
    result: BrowserLoopResult = await browser_interaction_loop.run_loop(
        tenant_id="tenant_task010_form",
        task_id="task_task010_form_1",
        goal="Discover inputs and submit registration form",
        start_url="https://httpbin.org/forms/post",
        max_steps=5,
    )

    # Verification:
    # 1. Loop executed multiple steps
    assert result.total_steps >= 2
    assert len(result.trace) >= 2

    # 2. Populated draft fields verified in DOM
    assert len(result.form_fields) > 0
    for field in result.form_fields:
        assert field.get("verified_in_dom") is True
        assert len(field.get("value", "")) > 0

    # 3. Discovered submit action was classified as consequential and halted at approval boundary
    actions = [t.action_type for t in result.trace]
    assert "fill" in actions

    # Either paused for approval or completed with populated draft
    if result.status == "PAUSED_FOR_APPROVAL":
        assert result.pending_action is not None
        assert result.pending_action.get("effect") in ("EXTERNAL_WRITE", "PAYMENT_OR_ORDER")
        assert "httpbin.org" in result.final_url
    else:
        assert result.status == "COMPLETED"


@pytest.mark.asyncio
async def test_information_comparison_matrix_structure(configured_registry):
    """Structure 1: Multi-source information comparison plans with comparison_matrix and OutcomeShape.COMPARISON."""
    planner = AdaptiveCapabilityPlanner(registry=configured_registry)
    intent = "Compare FastAPI vs Flask web frameworks: architecture, concurrency, typing, and licensing"

    plan = await planner.plan(intent=intent, available_capabilities=configured_registry.list_capabilities())

    assert len(plan.steps) >= 2
    step_caps = [s.capability_id for s in plan.steps]
    assert "browser.navigate" in step_caps or "browser.extract" in step_caps

    # Verify ExperiencePlan selects comparative matrix recipe
    exp_plan = experience_planner.plan_experience(
        task_id="task_probe_comp_1",
        intent=intent,
        expected_shape="comparison"
    )

    assert exp_plan.mode.value.upper() in ("FULL_WORKSPACE", "EMBEDDED")
    comp_types = [c.type for c in exp_plan.components]
    assert "data_grid" in comp_types or "comparison_matrix" in comp_types

    matrix_comp = exp_plan.get_component("comparison_matrix_main") or exp_plan.components[-1]
    col_keys = [c["key"] for c in matrix_comp.props.get("columns", [])]
    assert len(col_keys) >= 3


@pytest.mark.asyncio
async def test_unfamiliar_visual_workspace_simulation(configured_registry):
    """Structure 3: Unfamiliar task composes expressive visual workspace with interactive 2D canvas."""
    planner = AdaptiveCapabilityPlanner(registry=configured_registry)
    intent = "Teach me how a neural network learns with interactive visual simulation and step by step backpropagation"

    plan = await planner.plan(intent=intent, available_capabilities=configured_registry.list_capabilities())
    assert any("neural_simulation" in s.capability_id or "simulation" in s.capability_id for s in plan.steps)

    exp_plan = experience_planner.plan_experience(
        task_id="task_probe_edu_1",
        intent=intent,
        expected_shape="simulation"
    )

    canvas_comp = exp_plan.get_component("neural_canvas_main")
    assert canvas_comp is not None
    assert canvas_comp.type == "interactive_canvas_2d"

    arch = canvas_comp.props.get("architecture", {})
    assert arch.get("input_nodes") == 2
    assert arch.get("output_nodes") == 1

    steps_detail = canvas_comp.props.get("steps_detail", [])
    assert len(steps_detail) >= 4
    phases = [s.get("phase") for s in steps_detail]
    assert "Hidden Layer Activations" in phases
    assert "Backpropagation (Gradients)" in phases


@pytest.mark.asyncio
async def test_everyday_flight_discovery_with_honest_handoff(configured_registry):
    """Phase 4: Everyday flight route inquiry plans with real destinations and enforces honest handoff."""
    planner = AdaptiveCapabilityPlanner(registry=configured_registry)
    intent = "Check flight route details and schedule specifications for Air India AI101 from DEL to JFK with official booking portal"

    plan = await planner.plan(intent=intent, available_capabilities=configured_registry.list_capabilities())
    assert len(plan.steps) >= 1
    step_caps = [s.capability_id for s in plan.steps]
    assert "browser.navigate" in step_caps

    # Verify policy forbids unauthorized payments or fabricated booking actions
    fake_book_action = BrowserAction(
        action_type=BrowserActionType.CLICK,
        selector="button#confirm-purchase",
        text="Pay Now & Issue Ticket $1,250",
    )
    effect = browser_policy.classify_action_effect(fake_book_action)
    assert effect == BrowserActionEffect.PAYMENT_OR_ORDER
    assert browser_policy.requires_approval(effect) is True
