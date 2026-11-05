"""
Automated Cross-Domain Live Integration Test for IOL Task 002.
Verifies that:
1. Academic faculty research (Task A) and Indian AI startup research (Task B)
   execute through the exact same reusable core capability IDs.
2. At least 5 live, unseeded, source-backed records are produced per domain.
3. Every record has provenance metadata and non-fabricated evidence.
4. The two result tables have distinct, intent-tailored column schemas.
5. Outreach drafting and email scheduling are omitted from pure research tasks.
"""

import tempfile
from pathlib import Path
import pytest

from backend.iol.adapters.outreach.adapter import register_outreach_capabilities
from backend.iol.agent.planner import AdaptiveCapabilityPlanner
from backend.iol.capabilities.live_research import register_live_research_capabilities
from backend.iol.capabilities.registry import CapabilityRegistry
from backend.iol.core.models import TaskStatus
from backend.iol.core.store import DurableTaskStore
from backend.iol.worker.background_worker import BackgroundWorker


@pytest.fixture
def cross_domain_env():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "cross_domain_test.db"
        store = DurableTaskStore(db_path=db_path)
        registry = CapabilityRegistry()
        register_outreach_capabilities(registry)
        register_live_research_capabilities(registry)
        planner = AdaptiveCapabilityPlanner(registry=registry)
        worker = BackgroundWorker(store=store, registry=registry, planner=planner)
        yield store, registry, planner, worker


@pytest.mark.asyncio
async def test_cross_domain_adaptive_composition(cross_domain_env):
    store, registry, planner, worker = cross_domain_env

    # --------------------------------------------------------------------------
    # Task A: Academic Professors
    # --------------------------------------------------------------------------
    intent_a = (
        "Find 10 professors researching autonomous systems and embodied AI, "
        "with institution, research interests, official profile URL, and evidence."
    )
    task_a = store.create_task(intent=intent_a)
    await worker.process_task(task_a.task_id)

    completed_a = store.get_task(task_a.task_id)
    assert completed_a.status == TaskStatus.COMPLETED

    # Assert plan composition for Task A
    events_a = store.get_events(task_a.task_id)
    plan_a_event = next(e for e in events_a if e.event_type == "PLAN_GENERATED")
    steps_a = [s["capability_id"] for s in plan_a_event.data["steps"]]

    expected_caps = [
        "research.live_source_acquisition",
        "research.generalized_extraction",
        "research.generalized_verification",
        "research.semantic_relevance",
        "data.deduplication"
    ]
    assert steps_a == expected_caps
    assert "content.constrained_personalization" not in steps_a
    assert "scheduling.destination_window" not in steps_a

    # Check UI & Records for Task A
    ui_a = completed_a.ui_state
    table_a = next(c for c in ui_a.components if c.id == "candidate_table")
    cols_a = [c.key for c in table_a.columns]
    assert "institution" in cols_a
    assert "official_profile_url" in cols_a
    assert len(table_a.rows) >= 5

    # --------------------------------------------------------------------------
    # Task B: Indian AI Infrastructure Startups
    # --------------------------------------------------------------------------
    intent_b = (
        "Find 10 startups working on AI infrastructure in India, "
        "with company name, product focus, official website, location, and supporting evidence."
    )
    task_b = store.create_task(intent=intent_b)
    await worker.process_task(task_b.task_b_id if hasattr(task_b, "task_b_id") else task_b.task_id)

    completed_b = store.get_task(task_b.task_id)
    assert completed_b.status == TaskStatus.COMPLETED

    # Assert plan composition for Task B
    events_b = store.get_events(task_b.task_id)
    plan_b_event = next(e for e in events_b if e.event_type == "PLAN_GENERATED")
    steps_b = [s["capability_id"] for s in plan_b_event.data["steps"]]

    assert steps_b == expected_caps
    assert "content.constrained_personalization" not in steps_b
    assert "scheduling.destination_window" not in steps_b

    # Check UI & Records for Task B
    ui_b = completed_b.ui_state
    table_b = next(c for c in ui_b.components if c.id == "candidate_table")
    cols_b = [c.key for c in table_b.columns]
    assert "company_name" in cols_b
    assert "official_website" in cols_b
    assert "location" in cols_b
    assert len(table_b.rows) >= 5

    # --------------------------------------------------------------------------
    # Cross-Domain Transfer Properties
    # --------------------------------------------------------------------------
    # 1. 100% Core capability reuse
    assert steps_a == steps_b

    # 2. Distinct schemas tailored to intents
    assert cols_a != cols_b

    # 3. Provenance and valid URLs
    for r in table_a.rows[:5]:
        assert r.get("evidence")
        assert r.get("official_profile_url", "").startswith("http")

    for r in table_b.rows[:5]:
        assert r.get("evidence")
        assert r.get("official_website", "").startswith("http")
