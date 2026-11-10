"""
Tests for IOL v0.6 Experience Engine Subsystem.
Verifies recipe matching, plan generation, progressive data binding,
and mathematical neural network simulation capability.
"""

import os
import pytest
import asyncio
from backend.iol.experience.models import ExperienceMode, ExperiencePlan
from backend.iol.experience.recipes import experience_recipe_store
from backend.iol.experience.planner import experience_planner
from backend.iol.capabilities.educational import (
    NeuralNetworkSimulationCapability,
    NeuralSimulationInput,
    sigmoid,
)
from backend.iol.capabilities.base import ExecutionContext
from backend.iol.core.store import task_store
from backend.iol.core.models import ExecutionBudget, TaskStatus
from backend.iol.worker.background_worker import BackgroundWorker


def test_recipe_store_seed():
    """Verify built-in recipes are registered."""
    recipes = experience_recipe_store.list_recipes()
    recipe_ids = {r.recipe_id for r in recipes}
    assert "exp_recipe_research_database" in recipe_ids
    assert "exp_recipe_educational_simulation" in recipe_ids
    assert "exp_recipe_comparison_analysis" in recipe_ids


def test_recipe_matching_logic():
    """Verify intent-based recipe matching."""
    # Educational
    r1 = experience_recipe_store.find_matching_recipe("Teach me how a neural network learns step by step")
    assert r1.recipe_id == "exp_recipe_educational_simulation"

    # Comparison
    r2 = experience_recipe_store.find_matching_recipe("Compare PyTorch versus TensorFlow benchmarks")
    assert r2.recipe_id == "exp_recipe_comparison_analysis"

    # Research
    r3 = experience_recipe_store.find_matching_recipe("Find AI infrastructure startups in India")
    assert r3.recipe_id == "exp_recipe_research_database"


def test_experience_planner_plan_creation():
    """Verify ExperiencePlanner creates tailored ExperiencePlans."""
    plan = experience_planner.plan_experience(
        task_id="task_test_plan_1",
        intent="Find AI infrastructure startups in India"
    )
    assert plan.task_id == "task_test_plan_1"
    assert plan.mode == ExperienceMode.FULL_WORKSPACE
    assert "Startups" in plan.title or "AI" in plan.title
    assert len(plan.components) >= 2

    # Check data_grid has startup columns
    grid = plan.get_component("research_grid_main")
    assert grid is not None
    col_keys = [c["key"] for c in grid.props["columns"]]
    assert "company_name" in col_keys
    assert "confidence" in col_keys


def test_progressive_data_binding():
    """Verify records and metrics binding into an ExperiencePlan."""
    plan = experience_planner.plan_experience(
        task_id="task_test_bind_1",
        intent="Find AI infrastructure startups in India"
    )
    sample_records = [
        {"company_name": "Sarvam AI", "location": "Bengaluru", "confidence": 0.95},
        {"company_name": "Krutrim", "location": "Bengaluru", "confidence": 0.92},
    ]

    updated_plan = experience_planner.bind_records_to_plan(
        plan=plan,
        records=sample_records,
        execution_mode="LIVE (GITHUB REPOSITORIES API)",
        status="COMPLETED"
    )

    grid = updated_plan.get_component("research_grid_main")
    assert len(grid.props["rows"]) == 2
    assert grid.props["rows"][0]["company_name"] == "Sarvam AI"
    assert grid.props["placeholder_count"] == 3

    strip = updated_plan.get_component("metric_strip_main")
    metrics = {m["label"]: m["value"] for m in strip.props["metrics"]}
    assert metrics.get("Status") == "COMPLETED"
    assert "LIVE" in str(metrics.get("Execution Mode"))


@pytest.mark.asyncio
async def test_neural_network_simulation_capability():
    """Verify mathematical correctness of neural simulation capability."""
    cap = NeuralNetworkSimulationCapability()
    ctx = ExecutionContext(task_id="task_test_sim", step_id="step_sim")
    params = NeuralSimulationInput(
        input_values=[0.5, 0.8],
        target_value=1.0,
        learning_rate=0.1
    )

    res = await cap.execute(params, ctx)
    assert res.success is True
    data = res.data

    assert "initial_loss" in data
    assert "final_loss" in data
    # Gradient descent must decrease loss
    assert data["final_loss"] < data["initial_loss"]

    # Verify 5 structured steps
    steps = data["steps_detail"]
    assert len(steps) == 5
    assert steps[0]["phase"] == "1. Input Layer Feeding"
    assert steps[4]["phase"] == "5. Parameter Update & Loss Reduction"

    # Verify nodes & edges
    assert len(data["nodes"]) == 5  # 2 inputs, 2 hidden, 1 output
    assert len(data["edges"]) == 6  # 4 input->hidden, 2 hidden->output


@pytest.mark.asyncio
async def test_end_to_end_educational_worker_execution():
    """Verify background worker processes an educational intent and binds ExperiencePlan."""
    task = task_store.create_task(
        intent="Teach me how a neural network learns using an interactive 2D visualization",
        budget=ExecutionBudget(max_steps=5, max_duration_seconds=15.0),
        user_id="test_edu_user"
    )

    from backend.iol.capabilities.registry import capability_registry
    from backend.iol.capabilities.educational import register_educational_capabilities
    register_educational_capabilities(capability_registry)

    worker = BackgroundWorker(store=task_store, registry=capability_registry)
    await worker.process_task(task.task_id)

    completed_task = task_store.get_task(task.task_id)
    assert completed_task.status == TaskStatus.COMPLETED

    exp_plan = completed_task.experience_plan
    assert exp_plan is not None
    assert exp_plan["title"] == "Interactive Neural Network Visualizer"
    assert exp_plan["mode"] == "FULL_WORKSPACE"

    # Check that neural canvas received mathematical simulation data
    canvas_comp = next((c for c in exp_plan["components"] if c["type"] == "interactive_canvas_2d"), None)
    assert canvas_comp is not None
    assert "nodes" in canvas_comp["props"]
    assert "edges" in canvas_comp["props"]
    assert len(canvas_comp["props"]["nodes"]) == 5
    assert "steps_detail" in canvas_comp["props"]
    assert canvas_comp["props"]["final_loss"] < canvas_comp["props"]["initial_loss"]


def test_experience_plan_validator_rules():
    """Verify validator accepts valid catalog plans and blocks malicious/unknown components."""
    from backend.iol.experience.validator import ExperiencePlanValidator
    from backend.iol.experience.models import ExperienceComponent

    valid_plan = ExperiencePlan(
        plan_id="plan_valid_1",
        task_id="task_val_1",
        title="Valid Research Workspace",
        components=[
            ExperienceComponent(id="layout_root", type="workspace_layout", props={}),
            ExperienceComponent(id="strip_1", type="metric_strip", props={"metrics": [{"label": "Count", "value": 5}]}),
            ExperienceComponent(id="grid_1", type="data_grid", props={"columns": [{"key": "name", "header": "Name"}]}),
        ]
    )
    is_valid, errors = ExperiencePlanValidator.validate_plan(valid_plan)
    assert is_valid
    assert len(errors) == 0

    # Malicious script injection attempt
    injected_plan = ExperiencePlan(
        plan_id="plan_inj_1",
        task_id="task_inj_1",
        title="Injected Plan",
        components=[
            ExperienceComponent(
                id="bad_comp",
                type="data_grid",
                props={"columns": [], "title": "<script>alert('pwn')</script>"}
            )
        ]
    )
    is_valid_inj, errors_inj = ExperiencePlanValidator.validate_plan(injected_plan)
    assert not is_valid_inj
    assert any("script injection" in e.lower() for e in errors_inj)

    # Unknown component type
    unknown_plan = ExperiencePlan(
        plan_id="plan_unk_1",
        task_id="task_unk_1",
        title="Unknown Plan",
        components=[
            ExperienceComponent(id="unk_comp", type="custom_unregistered_widget", props={})
        ]
    )
    is_valid_unk, errors_unk = ExperiencePlanValidator.validate_plan(unknown_plan)
    assert not is_valid_unk
    assert any("unknown component type" in e.lower() for e in errors_unk)


def test_browser_and_form_recipes_matching():
    """Verify browser navigation and form draft recipes match correctly."""
    r_browser = experience_recipe_store.find_matching_recipe("Browse https://news.ycombinator.com and extract top stories")
    assert r_browser.recipe_id == "exp_recipe_browser_extraction"

    r_form = experience_recipe_store.find_matching_recipe("Draft an official passport renewal application form")
    assert r_form.recipe_id == "exp_recipe_form_draft"


def test_bind_outcome_to_plan_monotonic():
    """Verify progressive outcome envelope binding monotonically updates version."""
    from backend.iol.core.outcome import OutcomeEnvelopeV1, OutcomeFieldSchema, OutcomeItem, OutcomeShape, SourceMode

    plan = experience_planner.plan_experience("task_bind_test", "Find 3 database engines")
    assert plan.version == 1

    outcome = OutcomeEnvelopeV1(
        shape=OutcomeShape.COLLECTION,
        title="Database Engines",
        field_schema=[
            OutcomeFieldSchema(key="engine", header="Database Engine", type="text"),
            OutcomeFieldSchema(key="stars", header="Stars", type="number")
        ],
        items=[
            OutcomeItem(id="db_1", fields={"engine": "PostgreSQL", "stars": 15000}),
            OutcomeItem(id="db_2", fields={"engine": "DuckDB", "stars": 24000}),
        ],
        source_mode=SourceMode.LIVE_API,
        revision=2
    )

    updated_plan = experience_planner.bind_outcome_to_plan(plan, outcome)
    assert updated_plan.version == 2
    grid = updated_plan.get_component("research_grid_main")
    assert grid is not None
    assert len(grid.props["rows"]) == 2
    assert grid.props["rows"][0]["engine"] == "PostgreSQL"


def test_model_directed_experience_generation_and_blocked_reporting():
    """Verify Phase 1: MODEL_GENERATED plan synthesis, provenance tokens, and MODEL_GENERATION_BLOCKED fallback."""
    # 1. Blocked fallback when no provider credentials exist
    clean_keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "OLLAMA_HOST", "IOL_TEST_MODEL_PROVIDER"]
    old_env = {k: os.environ.pop(k, None) for k in clean_keys}
    try:
        plan_blocked = experience_planner.plan_experience("task_blocked_test", "Compare Redis vs Memcached")
        assert plan_blocked.plan_origin in ("RECIPE_ADAPTED", "DETERMINISTIC_FALLBACK")
        assert plan_blocked.model_metadata["status"] in ("MODEL_GENERATION_BLOCKED", "REAL_MODEL_BLOCKED")
        assert "No active external LLM credentials configured" in plan_blocked.model_metadata["origin_reason"]
    finally:
        for k, v in old_env.items():
            if v is not None:
                os.environ[k] = v

    # 2. Verified TEST_SYNTHESIZED synthesis when test provider is configured
    plan_model = experience_planner.plan_experience(
        task_id="task_model_test",
        intent="Synthesize custom autonomous intelligence dashboard",
        expected_shape="comparison",
        context_metadata={"model_api_key": "test_key", "model_provider": "mock", "model_name": "mock-gpt-4o"}
    )
    assert plan_model.plan_origin == "TEST_SYNTHESIZED"
    assert plan_model.model_metadata["status"] == "SUCCESS"
    assert plan_model.model_metadata["provider"] == "mock"
    assert plan_model.model_metadata["usage_type"] == "SIMULATED"
    assert plan_model.model_metadata["is_estimated"] is True
    assert "usage" in plan_model.model_metadata
    assert plan_model.model_metadata["usage"]["total_tokens"] > 0
    assert len(plan_model.components) >= 2

    # 3. Component catalog validation
    comp_types = [c.type for c in plan_model.components]
    assert "metric_strip" in comp_types
    assert "data_grid" in comp_types
