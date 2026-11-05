"""
Tests for Outreach Engine Reusable Capabilities Adapter.
Verifies discovery, extraction, verification, deduplication, personalization,
and destination scheduling using genuine schemas.
"""

import pytest
from backend.iol.capabilities.base import ExecutionContext
from backend.iol.capabilities.registry import CapabilityRegistry
from backend.iol.adapters.outreach.adapter import register_outreach_capabilities


@pytest.fixture
def registry():
    reg = CapabilityRegistry()
    register_outreach_capabilities(reg)
    return reg


@pytest.mark.asyncio
async def test_entity_discovery_capability(registry):
    ctx = ExecutionContext(task_id="t1", step_id="s1")
    params = {
        "entity_type": "faculty",
        "query_terms": ["sciml", "neural process"],
        "max_results": 3
    }
    res = await registry.invoke("research.entity_discovery", params, ctx)
    assert res.success is True
    assert res.data["total_discovered"] >= 1
    assert any("bodner" in e["name"].lower() or "mit" in e["organization"].lower() for e in res.data["entities"])


@pytest.mark.asyncio
async def test_structured_extraction_capability(registry):
    ctx = ExecutionContext(task_id="t1", step_id="s2")
    entities = [
        {"name": "Prof. Adam Bodner", "organization": "Massachusetts Institute of Technology", "country": "United States"}
    ]
    params = {
        "entity_type": "faculty",
        "entities": entities,
        "desired_fields": ["name", "organization", "email"]
    }
    res = await registry.invoke("research.structured_extraction", params, ctx)
    assert res.success is True
    assert len(res.data["records"]) == 1
    rec = res.data["records"][0]
    assert rec["fields"]["name"] == "Prof. Adam Bodner"
    assert "mit.edu" in rec["fields"]["email"]


@pytest.mark.asyncio
async def test_verification_capability(registry):
    ctx = ExecutionContext(task_id="t1", step_id="s3")
    records = [
        {
            "entity_id": "e1",
            "fields": {
                "name": "Prof. Adam Bodner",
                "organization": "MIT",
                "email": "bodner@mit.edu",
                "evidence_url": "https://csail.mit.edu/person/bodner"
            }
        },
        {
            "entity_id": "e2",
            "fields": {
                "name": "Invalid Candidate",
                "organization": "Unknown",
                "email": "bad-email-no-at",
                "evidence_url": ""
            }
        }
    ]
    params = {"entity_type": "faculty", "records": records}
    res = await registry.invoke("research.verification", params, ctx)
    assert res.success is True
    assert res.data["pass_count"] == 1
    assert res.data["flagged_count"] == 1
    assert res.data["verified_entities"][0]["is_valid"] is True
    assert res.data["verified_entities"][0]["confidence_tier"] == "HIGH"
    assert res.data["verified_entities"][1]["is_valid"] is False


@pytest.mark.asyncio
async def test_deduplication_capability(registry):
    ctx = ExecutionContext(task_id="t1", step_id="s4")
    entities = [
        {"name": "Prof. Percy Liang", "organization": "Stanford University"},
        {"name": "Prof. Percy Liang", "organization": "Stanford University"},  # Duplicate
        {"name": "Prof. Adam Bodner", "organization": "MIT"}
    ]
    params = {
        "entity_type": "faculty",
        "entities": entities,
        "identity_fields": ["organization", "name"]
    }
    res = await registry.invoke("data.deduplication", params, ctx)
    assert res.success is True
    assert res.data["duplicates_detected"] == 1
    assert len(res.data["unique_entities"]) == 2


@pytest.mark.asyncio
async def test_constrained_personalization_capability(registry):
    ctx = ExecutionContext(task_id="t1", step_id="s5")
    params = {
        "entity_type": "faculty",
        "target_entity": {
            "name": "Prof. Adam Bodner",
            "organization": "Massachusetts Institute of Technology",
            "domain_or_department": "Computer Science and AI Lab"
        },
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
    }
    res = await registry.invoke("content.constrained_personalization", params, ctx)
    assert res.success is True
    data = res.data
    assert data["passed_quality_gates"] is True
    assert 100 <= data["word_count"] <= 200
    assert "linkedin.com" not in data["body_text"].lower()
    assert "Neural Process Twin" in data["body_text"]
    assert "Sincerely,\nHarshith N" in data["body_text"]


@pytest.mark.asyncio
async def test_destination_window_scheduling_capability(registry):
    ctx = ExecutionContext(task_id="t1", step_id="s6")
    params = {
        "entity_type": "faculty",
        "target_entities": [
            {"name": "Prof. Adam Bodner", "organization": "Massachusetts Institute of Technology"},
            {"name": "Prof. Percy Liang", "organization": "Stanford University"}
        ],
        "target_local_hour": 8,
        "target_local_minute": 0,
        "operator_timezone": "Asia/Kolkata",
        "avoid_weekends": True
    }
    res = await registry.invoke("scheduling.destination_window", params, ctx)
    assert res.success is True
    assert res.data["total_scheduled"] == 2
    w1 = res.data["windows"][0]
    w2 = res.data["windows"][1]
    assert w1["timezone_iana"] == "America/New_York"
    assert w2["timezone_iana"] == "America/Los_Angeles"
    assert "IST" in w1["operator_dispatch_time"]
    assert "IST" in w2["operator_dispatch_time"]


@pytest.mark.asyncio
async def test_human_approval_gateway_capability(registry):
    ctx = ExecutionContext(task_id="t1", step_id="s7")

    # Safe dry-run is allowed
    dry_params = {
        "action_type": "DISPATCH_OUTREACH",
        "payload": {"recipient": "test@mit.edu", "body": "Hello"},
        "dry_run": True
    }
    res = await registry.invoke("security.human_approval_gateway", dry_params, ctx)
    assert res.success is True
    assert res.data["allowed"] is True
    assert res.data["dry_run"] is True

    # Live sending without authenticated session is BLOCKED
    live_blocked = {
        "action_type": "DISPATCH_OUTREACH",
        "payload": {"recipient": "test@mit.edu", "body": "Hello"},
        "dry_run": False
    }
    res_blocked = await registry.invoke("security.human_approval_gateway", live_blocked, ctx)
    assert res_blocked.success is False
    assert res_blocked.data["allowed"] is False
    assert "BLOCKED" in res_blocked.data["execution_status"]
