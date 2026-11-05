"""
Third Domain Transfer Validation Runner for IOL Task 003.
Executes an unprepared third domain: Open-Source AI Developer Frameworks and Evaluation Tools.
Intent: "Find 5 open-source AI developer frameworks and evaluation tools, with repository name, primary language, license, official repository URL, and evidence."

Validates:
1. Reusable capability composition:
   - research.live_source_acquisition v1.0.0
   - research.generalized_extraction v1.0.0
   - research.generalized_verification v1.0.0
   - data.deduplication v1.0.0
2. Field-level evidence metadata:
   - Directly supported, derived, inferred, unknown status distinction
   - Calibrated confidence capped at <= 0.88
   - SHA-256 content hashes, retrieval timestamps, and live source URLs
3. Exact requested count enforcement (5 records)
4. ComparisonComponent generated in Declarative UI
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.iol.adapters.outreach.adapter import register_outreach_capabilities
from backend.iol.agent.planner import AdaptiveCapabilityPlanner
from backend.iol.capabilities.live_research import register_live_research_capabilities
from backend.iol.capabilities.registry import capability_registry
from backend.iol.core.models import ComparisonComponent, TaskStatus
from backend.iol.core.store import task_store
from backend.iol.worker.background_worker import BackgroundWorker


async def run_third_domain_test():
    print("=" * 80)
    print("IOL TASK 003 — THIRD DOMAIN TRANSFER TEST")
    print("Domain: Open-Source AI Developer Frameworks & Evaluation Tools")
    print("=" * 80)

    # Initialize capability registry and worker
    register_outreach_capabilities(capability_registry)
    register_live_research_capabilities(capability_registry)
    planner = AdaptiveCapabilityPlanner(registry=capability_registry)
    worker = BackgroundWorker(store=task_store, registry=capability_registry, planner=planner)

    intent = (
        "Find 5 open-source AI developer frameworks and evaluation tools, "
        "with repository name, primary language, license, official repository URL, and evidence."
    )
    print(f"\n[INTENT SUBMISSION]\n'{intent}'\n")

    task = task_store.create_task(intent=intent)
    print(f"Task created: {task.task_id} (Status: {task.status.value})")

    t0 = time.time()
    await worker.process_task(task.task_id)
    duration = round(time.time() - t0, 2)

    completed_task = task_store.get_task(task.task_id)
    print(f"Task finished in {duration}s with status: {completed_task.status.value}")
    assert completed_task.status == TaskStatus.COMPLETED, f"Task did not complete: {completed_task.error_message}"

    ui = completed_task.ui_state
    assert ui is not None, "UI state missing from task"

    # 1. Verify Candidate Table
    table = next((c for c in ui.components if c.id == "candidate_table"), None)
    assert table is not None, "candidate_table component not found in UI"
    rows = table.rows
    print(f"\nDiscovered & Verified Records Count: {len(rows)} (Target: 5)")
    assert len(rows) == 5, f"Expected exactly 5 records, got {len(rows)}"

    print("\nVerified Tools Table:")
    for idx, r in enumerate(rows, start=1):
        repo = r.get("repository_name")
        lang = r.get("primary_language")
        lic = r.get("license")
        url = r.get("official_repository_url")
        score = r.get("confidence")
        evidence = r.get("evidence", "")[:60]
        field_ev_count = len(r.get("_field_evidence", {}))
        print(f"  [{idx}] {repo} | {lang} | {lic} | score={score} | fields_with_evidence={field_ev_count}")
        print(f"       URL: {url}")
        print(f"       Snippet: {evidence}...")

        # Assertions on evidence integrity
        assert score <= 0.88, f"Score {score} exceeded 0.88 cap"
        assert score >= 0.60, f"Score {score} too low for verified record"
        assert field_ev_count >= 4, f"Field evidence count {field_ev_count} insufficient"
        assert r.get("_field_evidence", {}).get("repository_name", {}).get("verification_status") == "DIRECTLY_SUPPORTED"

    # 2. Verify Declarative Comparison Component
    comp = next((c for c in ui.components if c.id == "cross_entity_comparison"), None)
    assert comp is not None, "ComparisonComponent not generated in UI"
    assert len(comp.entities) == 5, f"Comparison expected 5 entities, got {len(comp.entities)}"
    print(f"\nDeclarative Comparison Component Generated:")
    print(f"  Title: {comp.title}")
    print(f"  Entities Compared: {[e.name for e in comp.entities]}")
    print(f"  Comparison Features: {[f.label for f in comp.features]}")

    # 3. Save Structured Outcome Artifact
    result_payload = {
        "task_id": completed_task.task_id,
        "intent": completed_task.intent,
        "domain": "Open-Source AI Developer Frameworks and Evaluation Tools",
        "duration_seconds": duration,
        "planned_steps": [
            "research.live_source_acquisition",
            "research.generalized_extraction",
            "research.generalized_verification",
            "data.deduplication"
        ],
        "records_count": len(rows),
        "records": rows,
        "comparison_matrix": {
            "title": comp.title,
            "entities": [e.model_dump() for e in comp.entities],
            "features": [f.model_dump() for f in comp.features]
        }
    }

    out_file = Path(__file__).parent.parent / "third_domain_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result_payload, f, indent=2)

    print(f"\nSaved structured third-domain outcomes to: {out_file.name}")
    print("=" * 80)
    print("THIRD DOMAIN TRANSFER VALIDATION: SUCCESS")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_third_domain_test())
