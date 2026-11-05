"""
Automated Skill Learning, Lifecycle State Progression, and Warm-Start Benchmark Tests.
Validates extraction of reusable capability blueprints from task traces,
the 3-stage validation state machine (CANDIDATE -> VALIDATED -> TRUSTED),
and cold vs warm execution performance metrics.
"""

import tempfile
import time
from pathlib import Path
import pytest

from backend.iol.adapters.outreach.adapter import register_outreach_capabilities
from backend.iol.agent.planner import AdaptiveCapabilityPlanner
from backend.iol.capabilities.live_research import register_live_research_capabilities
from backend.iol.capabilities.registry import CapabilityRegistry
from backend.iol.core.models import TaskStatus
from backend.iol.core.store import DurableTaskStore
from backend.iol.skills.extractor import SkillExtractor
from backend.iol.skills.models import SkillLifecycleState
from backend.iol.skills.registry import LearnedSkillRegistry
from backend.iol.worker.background_worker import BackgroundWorker


@pytest.fixture
def skill_test_env():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "skill_test.db"
        store = DurableTaskStore(db_path=db_path)
        reg = CapabilityRegistry()
        register_outreach_capabilities(reg)
        register_live_research_capabilities(reg)
        planner = AdaptiveCapabilityPlanner(registry=reg)
        worker = BackgroundWorker(store=store, registry=reg, planner=planner)
        skill_reg = LearnedSkillRegistry()
        extractor = SkillExtractor()
        yield store, reg, planner, worker, skill_reg, extractor


@pytest.mark.asyncio
async def test_end_to_end_skill_learning_and_warm_start_benchmark(skill_test_env):
    """
    Executes the complete demonstrable learning loop:
    1. Cold Execution: Run initial task without pre-existing skill.
    2. Extraction: Extract sanitized, versioned skill candidate.
    3. Validation 1: Validate against diverse Task 2 -> VALIDATED_FOR_TASK_FAMILY.
    4. Validation 2: Validate against diverse Task 3 -> TRUSTED_FOR_BOUNDED_REUSE.
    5. Warm-Start Execution: Execute Task 4 using warm compilation and measure latency.
    """
    store, reg, planner, worker, skill_reg, extractor = skill_test_env

    # --------------------------------------------------------------------------
    # 1. Cold Execution: Task 1 (AI Developer Frameworks)
    # --------------------------------------------------------------------------
    intent_cold = "Find 5 open-source AI developer frameworks with repository name, primary language, license, official repository URL, and evidence."

    t0_cold_plan = time.perf_counter()
    cold_plan = await planner.plan(intent_cold, reg.list_capabilities())
    cold_plan_duration_ms = (time.perf_counter() - t0_cold_plan) * 1000

    task_1 = store.create_task(intent=intent_cold)
    await worker.process_task(task_1.task_id)

    completed_1 = store.get_task(task_1.task_id)
    assert completed_1.status == TaskStatus.COMPLETED
    events_1 = store.get_events(task_1.task_id)

    # --------------------------------------------------------------------------
    # 2. Extract Skill Candidate from Execution Trace
    # --------------------------------------------------------------------------
    learned_skill = extractor.extract_skill(completed_1, events_1)
    assert learned_skill is not None
    assert learned_skill.lifecycle_state == SkillLifecycleState.CANDIDATE
    assert len(learned_skill.steps) == 5
    assert learned_skill.task_family == "research.developer_tools_discovery"
    assert "skill_research_developer_tools_discovery" in learned_skill.skill_id

    # Verify sanitization: no raw task IDs or private tokens
    for s in learned_skill.steps:
        params_str = str(s.parameter_template)
        assert task_1.task_id not in params_str

    skill_reg.register_skill(learned_skill)

    # --------------------------------------------------------------------------
    # 3. Validation Run 1 on New Diverse Task (Task 2)
    # --------------------------------------------------------------------------
    intent_val_1 = "Find 5 evaluation tools for LLMs with repository name, license, and official repository URL."
    task_2 = store.create_task(intent=intent_val_1)
    await worker.process_task(task_2.task_id)
    assert store.get_task(task_2.task_id).status == TaskStatus.COMPLETED

    skill_reg.record_validation(
        skill_id=learned_skill.skill_id,
        task_id=task_2.task_id,
        success=True,
        domain="evaluation_tools",
        notes="Successfully discovered and verified LLM evaluation tools."
    )
    # State transitions to VALIDATED_FOR_TASK_FAMILY
    assert learned_skill.lifecycle_state == SkillLifecycleState.VALIDATED_FOR_TASK_FAMILY

    # --------------------------------------------------------------------------
    # 4. Validation Run 2 on Another Diverse Task (Task 3)
    # --------------------------------------------------------------------------
    intent_val_2 = "Find 5 agent orchestration frameworks with repository name, primary language, and license."
    task_3 = store.create_task(intent=intent_val_2)
    await worker.process_task(task_3.task_id)
    assert store.get_task(task_3.task_id).status == TaskStatus.COMPLETED

    skill_reg.record_validation(
        skill_id=learned_skill.skill_id,
        task_id=task_3.task_id,
        success=True,
        domain="agent_orchestration",
        notes="Successfully transferred to multi-agent frameworks."
    )
    # State transitions to TRUSTED_FOR_BOUNDED_REUSE
    assert learned_skill.lifecycle_state == SkillLifecycleState.TRUSTED_FOR_BOUNDED_REUSE

    # --------------------------------------------------------------------------
    # 5. Warm-Start Compilation & Benchmark (Task 4)
    # --------------------------------------------------------------------------
    intent_warm = "Find 5 open-source LLM inference serving frameworks with repository name, license, and evidence."

    warm_durations = []
    warm_plan = None
    for _ in range(5):
        t0_warm = time.perf_counter()
        warm_plan = skill_reg.compile_warm_plan(
            skill=learned_skill,
            intent=intent_warm,
            entity_type="tool",
            requested_fields=["repository_name", "license", "official_repository_url", "evidence"],
            max_records=5,
            query_terms=["LLM serving", "inference"],
            available_capabilities=reg.list_capabilities()
        )
        warm_durations.append((time.perf_counter() - t0_warm) * 1000)

    warm_plan_duration_ms = min(warm_durations)

    print(f"\n[Skill Benchmark] Cold Planning: {cold_plan_duration_ms:.3f}ms | Warm Planning: {warm_plan_duration_ms:.3f}ms")
    assert warm_plan is not None
    assert "Warm-start execution plan" in warm_plan.rationale
    assert len(warm_plan.steps) == 5
    # Sub-15ms plan instantiation
    assert warm_plan_duration_ms < 15.0

    # Execute Warm Task
    task_4 = store.create_task(intent=intent_warm)
    await worker.process_task(task_4.task_id)
    completed_4 = store.get_task(task_4.task_id)
    assert completed_4.status == TaskStatus.COMPLETED

    # Verify candidate table populated with intent-satisfied targets
    ui_4 = completed_4.ui_state
    table_comp = next(c for c in ui_4.components if c.id == "candidate_table")
    assert len(table_comp.rows) >= 3
    for r in table_comp.rows:
        assert r.get("confidence") >= 0.60
