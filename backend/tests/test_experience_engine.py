"""
Tests for IOL v0.6 Experience Engine Subsystem.
Verifies recipe matching, plan generation, progressive data binding,
and mathematical neural network simulation capability.
"""

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
