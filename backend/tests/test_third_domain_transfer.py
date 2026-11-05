"""
Tests for Workstream C & D: Third Domain Transfer and Multi-Entity Comparison Component.
Verifies autonomous execution of open-source AI developer tools & evaluation frameworks
through shared, domain-neutral capabilities.
"""

import pytest
from backend.iol.adapters.outreach.adapter import register_outreach_capabilities
from backend.iol.agent.planner import AdaptiveCapabilityPlanner
from backend.iol.capabilities.live_research import register_live_research_capabilities
from backend.iol.capabilities.registry import CapabilityRegistry
from backend.iol.core.models import ComparisonComponent, TableComponent, TaskStatus
from backend.iol.core.store import DurableTaskStore
from backend.iol.worker.background_worker import BackgroundWorker


@pytest.fixture
def env():
    store = DurableTaskStore()
    reg = CapabilityRegistry()
    register_outreach_capabilities(reg)
    register_live_research_capabilities(reg)
    planner = AdaptiveCapabilityPlanner(registry=reg)
    worker = BackgroundWorker(store=store, registry=reg, planner=planner)
    return store, reg, planner, worker


@pytest.mark.asyncio
async def test_third_domain_planning_and_contract_validation(env):
    """Verify that a developer tools intent dynamically maps to a 4-step plan without hardcoded pipelines."""
    _, reg, planner, _ = env
    intent = "Find 5 open-source AI developer frameworks and evaluation tools, with repository name, primary language, license, official repository URL, and evidence."

    plan = await planner.plan(intent, reg.list_capabilities())
    assert len(plan.steps) == 5
    step_cap_ids = [s.capability_id for s in plan.steps]
    assert step_cap_ids == [
        "research.live_source_acquisition",
        "research.generalized_extraction",
        "research.generalized_verification",
        "research.semantic_relevance",
        "data.deduplication",
    ]

    # Verify parameters bind requested fields properly
    ext_step = plan.steps[1]
    assert "repository_name" in ext_step.parameters["requested_fields"]
    assert "license" in ext_step.parameters["requested_fields"]


@pytest.mark.asyncio
async def test_third_domain_end_to_end_execution_and_comparison(env):
    """Verify end-to-end execution of third domain with count enforcement and ComparisonComponent generation."""
    store, reg, planner, worker = env
    intent = "Find 5 open-source AI developer frameworks and evaluation tools, with repository name, primary language, license, official repository URL, and evidence."

    task = store.create_task(intent=intent)
    await worker.process_task(task.task_id)

    completed = store.get_task(task.task_id)
    assert completed.status == TaskStatus.COMPLETED
    assert completed.ui_state is not None

    # Check candidate table
    table = next(c for c in completed.ui_state.components if isinstance(c, TableComponent) and c.id == "candidate_table")
    assert len(table.rows) == 5, f"Expected 5 records, got {len(table.rows)}"

    for row in table.rows:
        assert "repository_name" in row
        assert "primary_language" in row
        assert "official_repository_url" in row
        assert row.get("confidence", 0) <= 0.88
        assert row.get("confidence", 0) >= 0.60
        assert "_field_evidence" in row
        assert "_classification" in row

    # Check comparison component
    comp = next((c for c in completed.ui_state.components if isinstance(c, ComparisonComponent) or getattr(c, 'type', None) == 'comparison'), None)
    assert comp is not None, "ComparisonComponent must be generated for verified entities"
    assert len(comp.entities) == 5
    assert len(comp.features) >= 3
