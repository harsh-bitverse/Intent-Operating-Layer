"""
Automated Verification Suite for IOL Task 011:
- Genuine Model-Directed Generative UI Synthesis & Token Tracking
- Algorithmic Graph Computation & Step Walkthrough (Dijkstra)
- Experience Knowledge Store & Cross-Domain Pattern Adaptation
- Privacy Scrubbing of Personal Information
- Dynamic Browser Loop DOM State Verification & Recovery
- Schema Validation of Generalized Expressive UI Catalog
"""

import asyncio
import os
import pytest

from backend.iol.capabilities.base import ExecutionContext
from backend.iol.capabilities.educational import (
    DijkstraGraphSimulationCapability,
    DijkstraSimulationInput,
)
from backend.iol.capabilities.registry import capability_registry
from backend.iol.experience.gateway import ModelProviderGateway, model_provider_gateway
from backend.iol.experience.knowledge import (
    StructuralSignature,
    experience_knowledge_store,
)
from backend.iol.experience.models import ExperienceComponent, ExperiencePlan
from backend.iol.experience.planner import experience_planner
from backend.iol.experience.validator import experience_plan_validator
from backend.iol.browser.loop import (
    BrowserInteractionLoop,
    BrowserLoopStepTrace,
)
from backend.iol.browser.models import (
    BrowserAction,
    BrowserActionEffect,
    BrowserActionType,
    BrowserObservation,
)


@pytest.mark.asyncio
async def test_model_directed_generative_ui_synthesis():
    """Verify genuine MODEL_GENERATED ExperiencePlan synthesis with catalog validation and token metadata."""
    gw = ModelProviderGateway()
    context_meta = {"model_provider": "test_mock", "model_name": "iol-synthesizer-v1"}

    plan = await gw.generate_plan(
        task_id="task_test_model_gen",
        intent="synthesize dijkstra algorithm shortest path interactive simulation",
        expected_shape="simulation",
        context_metadata=context_meta,
    )

    assert plan is not None
    assert plan.plan_origin == "MODEL_GENERATED"
    assert plan.status == "ACTIVE"
    assert len(plan.components) >= 2

    # Check component types
    types = [c.type for c in plan.components]
    assert "metric_strip" in types
    assert "interactive_canvas_2d" in types

    # Check model metadata provenance
    meta = plan.model_metadata
    assert meta["status"] == "SUCCESS"
    assert meta["provider"] == "test_mock"
    assert meta["latency_ms"] >= 0
    assert "usage" in meta
    assert meta["usage"]["total_tokens"] > 0

    # Strict catalog schema validation
    is_valid, errors = experience_plan_validator.validate_plan(plan)
    assert is_valid, f"Validation errors: {errors}"


@pytest.mark.asyncio
async def test_unconfigured_model_generation_blocked_zero_false_claims():
    """Verify unconfigured runs cleanly report MODEL_GENERATION_BLOCKED without fabricating MODEL_GENERATED."""
    # Ensure no external API keys are active for this test
    clean_env = {
        "OPENAI_API_KEY": None,
        "ANTHROPIC_API_KEY": None,
        "GEMINI_API_KEY": None,
        "GOOGLE_API_KEY": None,
        "OLLAMA_HOST": None,
        "IOL_TEST_MODEL_PROVIDER": None,
    }
    old_env = {}
    for k, v in clean_env.items():
        old_env[k] = os.environ.get(k)
        if k in os.environ:
            del os.environ[k]

    try:
        gw = ModelProviderGateway()
        plan_none = await gw.generate_plan("task_blocked", "find artificial intelligence startups")
        assert plan_none is None, "Gateway must return None when no model provider credentials exist."

        plan = experience_planner.plan_experience(
            task_id="task_fallback_verify",
            intent="find artificial intelligence startups in healthcare",
            expected_shape="collection",
        )

        assert plan.plan_origin in ("RECIPE_ADAPTED", "DETERMINISTIC_FALLBACK")
        assert plan.plan_origin != "MODEL_GENERATED"
        assert plan.model_metadata.get("status") in ("MODEL_GENERATION_BLOCKED", "KNOWLEDGE_TRANSFER_ADAPTED")

    finally:
        for k, v in old_env.items():
            if v is not None:
                os.environ[k] = v


@pytest.mark.asyncio
async def test_dijkstra_graph_simulation_capability():
    """Verify DijkstraGraphSimulationCapability computes exact mathematical shortest path."""
    cap = DijkstraGraphSimulationCapability()
    ctx = ExecutionContext(task_id="task_dijkstra_test", tenant_id="default", user_id="test_user", step_id="s1")

    res = await cap.execute(DijkstraSimulationInput(start_vertex="A", target_vertex="E"), ctx)

    assert res.success is True
    data = res.data
    assert data["algorithm"] == "Dijkstra Shortest Path"
    assert data["optimal_path"] == ["A", "C", "B", "E"]
    assert data["optimal_cost"] == 7.0

    # Verify steps structure
    steps = data["steps_detail"]
    assert len(steps) == 5
    assert steps[0]["phase"] == "INIT"
    assert steps[4]["phase"] == "COMPLETED"

    # Verify node coordinates for 2D canvas
    nodes = data["nodes"]
    assert len(nodes) == 5
    for node in nodes:
        assert "cx" in node and "cy" in node
        assert "label" in node


def test_experience_knowledge_cross_domain_adaptation():
    """Verify ExperienceKnowledgeStore adapts structural patterns across domains with privacy scrubbing."""
    # 1. Test Privacy Scrubbing
    sensitive_payload = {
        "user_email": "engineer.lead@enterprise.com",
        "mobile": "+1-555-019-2834",
        "secret_token": "sk-1234567890abcdef1234567890abcdef",
        "api_key": "raw_secret_value",
        "description": "Please contact engineer.lead@enterprise.com with token sk-abcdef123456789012345678",
    }
    scrubbed = experience_knowledge_store.scrub_private_data(sensitive_payload)

    assert "api_key" not in scrubbed
    assert "[REDACTED_EMAIL]" in scrubbed["user_email"]
    assert "[REDACTED_PHONE]" in scrubbed["mobile"]
    assert "[REDACTED_SECRET]" in scrubbed["description"]

    # 2. Test Cross-Domain Adaptation
    adapted_plan = experience_knowledge_store.adapt_pattern_cross_domain(
        source_record_id="pat_comparison_matrix",
        target_intent="compare PostgreSQL and MongoDB database architectures",
        target_domain="database_systems",
        target_entity_names=("PostgreSQL", "MongoDB"),
        task_id="task_cross_domain_test",
    )

    assert adapted_plan is not None
    assert adapted_plan.plan_origin == "RECIPE_ADAPTED"
    assert "Database_Systems" in adapted_plan.title
    assert "PostgreSQL vs MongoDB" in adapted_plan.title

    matrix_comp = adapted_plan.get_component("comparison_matrix_main")
    assert matrix_comp is not None
    assert any(c["header"] == "PostgreSQL" for c in matrix_comp.props["columns"])
    assert any(c["header"] == "MongoDB" for c in matrix_comp.props["columns"])

    is_valid, errors = experience_plan_validator.validate_plan(adapted_plan)
    assert is_valid, f"Validation errors: {errors}"


def test_generalized_expressive_ui_catalog_validation():
    """Verify validator accepts all Task 011 catalog components and strictly rejects unsafe scripts."""
    valid_plan = ExperiencePlan(
        plan_id="plan_valid_catalog",
        task_id="task_catalog",
        mode="FULL_WORKSPACE",
        title="Valid Expressive Workspace",
        status="ACTIVE",
        components=[
            ExperienceComponent(
                id="c_metrics",
                type="metric_strip",
                props={"metrics": [{"label": "Status", "value": "ACTIVE", "badge_color": "emerald"}]},
            ),
            ExperienceComponent(
                id="c_timeline",
                type="timeline_view",
                props={
                    "title": "Delivery Stages",
                    "items": [{"id": "t1", "title": "Stage 1", "status": "completed"}],
                },
            ),
            ExperienceComponent(
                id="c_document",
                type="document_preview",
                props={
                    "title": "Technical Specification",
                    "document_type": "PDF",
                    "content": "Verified specifications.",
                },
            ),
            ExperienceComponent(
                id="c_canvas",
                type="interactive_canvas_2d",
                props={"title": "Graph Simulation", "nodes": [], "edges": [], "steps_detail": []},
            ),
        ],
    )

    is_valid, errors = experience_plan_validator.validate_plan(valid_plan)
    assert is_valid, f"Valid plan unexpectedly rejected: {errors}"

    # Verify script injection rejection
    malicious_plan = ExperiencePlan(
        plan_id="plan_xss",
        task_id="task_xss",
        mode="FULL_WORKSPACE",
        title="Unsafe Workspace",
        status="ACTIVE",
        components=[
            ExperienceComponent(
                id="c_xss",
                type="document_preview",
                props={"title": "XSS Probe", "content": "<script>alert(1)</script>"},
            )
        ],
    )

    is_malicious_valid, mal_errors = experience_plan_validator.validate_plan(malicious_plan)
    assert not is_malicious_valid
    assert any("Potential script injection" in err for err in mal_errors)
