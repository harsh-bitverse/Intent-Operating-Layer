"""
Integration Tests for IOL: Professor Research and Startup Research.
Demonstrates that the exact same reusable capability IDs execute end-to-end
across diverse research domains without modifying underlying capability contracts.
"""

import pytest
from backend.iol.capabilities.base import ExecutionContext
from backend.iol.capabilities.registry import CapabilityRegistry
from backend.iol.adapters.outreach.adapter import register_outreach_capabilities
from backend.iol.agent.orchestrator import IntentOrchestrator


@pytest.fixture
def test_environment():
    registry = CapabilityRegistry()
    register_outreach_capabilities(registry)
    orchestrator = IntentOrchestrator()
    return registry, orchestrator


@pytest.mark.asyncio
async def test_professor_research_pipeline(test_environment):
    """
    Scenario 1: Academic Professor Research.
    Grounded in IIT Delhi student credentials, targeting elite faculty.
    """
    registry, orchestrator = test_environment
    intent = "Research faculty in AI and SciML for Summer 2027 internship and schedule 8am windows"

    # 1. Orchestrator plans steps using registered capabilities
    plan = await orchestrator.plan(intent, registry.list_capabilities())
    assert len(plan.steps) == 7
    step_cap_ids = [s.capability_id for s in plan.steps]
    assert "research.entity_discovery" in step_cap_ids
    assert "research.verification" in step_cap_ids
    assert "content.constrained_personalization" in step_cap_ids
    assert "scheduling.destination_window" in step_cap_ids
    assert "security.human_approval_gateway" in step_cap_ids

    # 2. Execute Step 1: Entity Discovery
    ctx = ExecutionContext(task_id="task_prof_e2e", step_id="step_discovery")
    res1 = await registry.invoke("research.entity_discovery", plan.steps[0].parameters, ctx)
    assert res1.success is True
    discovered_entities = res1.data["entities"]
    assert len(discovered_entities) > 0
    assert any("mit" in e["organization"].lower() or "stanford" in e["organization"].lower() for e in discovered_entities)

    # 3. Execute Step 2: Extraction
    ctx.step_id = "step_extraction"
    res2 = await registry.invoke("research.structured_extraction", {
        "entity_type": "faculty",
        "entities": discovered_entities,
        "desired_fields": ["name", "organization", "email", "domain_or_department", "evidence_url"]
    }, ctx)
    assert res2.success is True
    extracted_records = res2.data["records"]
    assert len(extracted_records) == len(discovered_entities)

    # 4. Execute Step 3: Verification
    ctx.step_id = "step_verification"
    res3 = await registry.invoke("research.verification", {
        "entity_type": "faculty",
        "records": extracted_records
    }, ctx)
    assert res3.success is True
    verified_entities = res3.data["verified_entities"]
    assert res3.data["pass_count"] >= 1

    # 5. Execute Step 4: Deduplication
    ctx.step_id = "step_dedup"
    res4 = await registry.invoke("data.deduplication", {
        "entity_type": "faculty",
        "entities": verified_entities,
        "identity_fields": ["organization", "name"]
    }, ctx)
    assert res4.success is True
    unique_entities = res4.data["unique_entities"]
    assert len(unique_entities) > 0

    # 6. Execute Step 5: Grounded Personalization
    ctx.step_id = "step_personalization"
    target = unique_entities[0]
    res5 = await registry.invoke("content.constrained_personalization", {
        "entity_type": "faculty",
        "target_entity": target,
        "sender_profile": {
            "name": "Harshith N",
            "title": "Undergraduate, Department of Chemical Engineering",
            "institution": "Indian Institute of Technology Delhi (IIT Delhi)",
            "email": "ch1251635@iitd.ac.in",
            "verified_projects": [
                {"title": "Neural Process Twin", "summary": "Physics-aware SciML surrogate simulator in PyTorch"}
            ]
        },
        "constraints": {
            "min_words": 100,
            "max_words": 200,
            "forbidden_terms": ["github.com", "linkedin.com"]
        }
    }, ctx)
    assert res5.success is True
    draft = res5.data
    assert draft["passed_quality_gates"] is True
    assert 100 <= draft["word_count"] <= 200
    assert "Neural Process Twin" in draft["body_text"]
    assert "github.com" not in draft["body_text"]

    # 7. Execute Step 6: Morning Window Scheduling
    ctx.step_id = "step_scheduling"
    res6 = await registry.invoke("scheduling.destination_window", {
        "entity_type": "faculty",
        "target_entities": unique_entities,
        "target_local_hour": 8,
        "operator_timezone": "Asia/Kolkata"
    }, ctx)
    assert res6.success is True
    windows = res6.data["windows"]
    assert len(windows) > 0
    assert "IST" in windows[0]["operator_dispatch_time"]

    # 8. Execute Step 7: Security Approval Gateway (Safety Enforced)
    ctx.step_id = "step_approval"
    res7 = await registry.invoke("security.human_approval_gateway", {
        "action_type": "DISPATCH_OUTREACH",
        "payload": draft,
        "dry_run": True
    }, ctx)
    assert res7.success is True
    assert res7.data["allowed"] is True
    assert res7.data["dry_run"] is True


@pytest.mark.asyncio
async def test_startup_research_pipeline(test_environment):
    """
    Scenario 2: Tech Startup & Founder Research.
    Uses the EXACT SAME capability IDs to discover, verify, personalize, and schedule startup outreach.
    """
    registry, orchestrator = test_environment
    intent = "Find innovative AI and robotics startups for industry research collaboration"

    # 1. Orchestrator plans steps using the exact same registered capabilities
    plan = await orchestrator.plan(intent, registry.list_capabilities())
    assert len(plan.steps) == 7
    step_cap_ids = [s.capability_id for s in plan.steps]
    assert "research.entity_discovery" in step_cap_ids
    assert "research.verification" in step_cap_ids
    assert "content.constrained_personalization" in step_cap_ids
    assert "scheduling.destination_window" in step_cap_ids

    # 2. Execute Step 1: Entity Discovery (Targeting Startups)
    ctx = ExecutionContext(task_id="task_startup_e2e", step_id="step_discovery")
    res1 = await registry.invoke("research.entity_discovery", {
        "entity_type": "startup",
        "query_terms": ["ai", "robotics"],
        "max_results": 4
    }, ctx)
    assert res1.success is True
    discovered_startups = res1.data["entities"]
    assert len(discovered_startups) >= 2
    assert any("figure" in s["organization"].lower() or "scale" in s["organization"].lower() for s in discovered_startups)

    # 3. Execute Step 2: Extraction
    ctx.step_id = "step_extraction"
    res2 = await registry.invoke("research.structured_extraction", {
        "entity_type": "startup",
        "entities": discovered_startups,
        "desired_fields": ["name", "organization", "email", "domain_or_department", "source_url"]
    }, ctx)
    assert res2.success is True
    assert len(res2.data["records"]) == len(discovered_startups)

    # 4. Execute Step 3: Verification
    ctx.step_id = "step_verification"
    res3 = await registry.invoke("research.verification", {
        "entity_type": "startup",
        "records": res2.data["records"]
    }, ctx)
    assert res3.success is True
    verified_startups = res3.data["verified_entities"]
    assert res3.data["pass_count"] >= 1

    # 5. Execute Step 4: Deduplication
    ctx.step_id = "step_dedup"
    res4 = await registry.invoke("data.deduplication", {
        "entity_type": "startup",
        "entities": verified_startups,
        "identity_fields": ["organization", "name"]
    }, ctx)
    assert res4.success is True
    unique_startups = res4.data["unique_entities"]

    # 6. Execute Step 5: Grounded Personalization
    ctx.step_id = "step_personalization"
    target_startup = unique_startups[0]
    res5 = await registry.invoke("content.constrained_personalization", {
        "entity_type": "startup",
        "target_entity": target_startup,
        "sender_profile": {
            "name": "Harshith N",
            "title": "Systems Researcher & Engineer",
            "institution": "IIT Delhi",
            "email": "ch1251635@iitd.ac.in",
            "verified_projects": [
                {"title": "Humanoid Robotics Multi-DOF Controller", "summary": "Servo-actuated kinematic control mechanism"}
            ]
        },
        "constraints": {
            "min_words": 100,
            "max_words": 200,
            "forbidden_terms": ["github.com", "linkedin.com"]
        }
    }, ctx)
    assert res5.success is True
    draft = res5.data
    assert draft["passed_quality_gates"] is True
    assert 100 <= draft["word_count"] <= 200

    # 7. Execute Step 6: Morning Window Scheduling
    ctx.step_id = "step_scheduling"
    res6 = await registry.invoke("scheduling.destination_window", {
        "entity_type": "startup",
        "target_entities": unique_startups,
        "target_local_hour": 8,
        "operator_timezone": "Asia/Kolkata"
    }, ctx)
    assert res6.success is True
    assert len(res6.data["windows"]) > 0

    # 8. Verification: Autonomous Live Transmission MUST be Blocked
    ctx.step_id = "step_approval"
    res_unsafe = await registry.invoke("security.human_approval_gateway", {
        "action_type": "DISPATCH_OUTREACH",
        "payload": draft,
        "dry_run": False  # Live attempt
    }, ctx)
    assert res_unsafe.success is False
    assert res_unsafe.data["allowed"] is False
    assert "BLOCKED" in res_unsafe.data["execution_status"]
