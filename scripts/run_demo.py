#!/usr/bin/env python3
"""
Engineers' Conclave Demonstration Runner for Intent Operating Layer (IOL).
Executes Demo A (Academic Faculty), Demo B (Indian AI Startups), or Demo C (AI Developer Tools).
Supports both --mode live (live network research) and --mode replay (offline recorded fixtures).
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.iol.adapters.outreach.adapter import register_outreach_capabilities
from backend.iol.agent.planner import AdaptiveCapabilityPlanner
from backend.iol.capabilities.live_research import register_live_research_capabilities
from backend.iol.capabilities.registry import CapabilityRegistry
from backend.iol.core.models import TaskStatus
from backend.iol.core.store import DurableTaskStore
from backend.iol.worker.background_worker import BackgroundWorker


DEMO_SPECS = {
    "A": {
        "title": "Demo A: Autonomous Academic Faculty Research",
        "domain": "Academia (Autonomous Systems & Embodied AI)",
        "intent": (
            "Find 10 professors researching autonomous systems and embodied AI, "
            "with institution, research interests, official profile URL, and evidence."
        ),
        "expected_columns": ["name", "institution", "research_interests", "official_profile_url", "confidence"],
        "description": "Demonstrates live scholarly source acquisition, structured extraction, evidence verification, semantic relevance gating, and cryptographic deduplication."
    },
    "B": {
        "title": "Demo B: Indian AI Infrastructure Commercial Discovery",
        "domain": "Industry Startups (Indian AI Infrastructure)",
        "intent": (
            "Find 10 startups working on AI infrastructure in India, "
            "with company name, product focus, official website, location, and supporting evidence."
        ),
        "expected_columns": ["company_name", "product_focus", "official_website", "location", "confidence"],
        "description": "Demonstrates cross-domain reuse of identical capabilities for commercial entities with geographic and temporal constraints."
    },
    "C": {
        "title": "Demo C: Open-Source AI Developer Frameworks & Warm Skill Reuse",
        "domain": "Developer Tools (LLM Frameworks & Evaluation Engines)",
        "intent": (
            "Find 5 open-source AI evaluation and developer frameworks with "
            "repository name, primary language, license, official repository URL, and evidence."
        ),
        "expected_columns": ["repository_name", "primary_language", "license", "official_repository_url", "confidence"],
        "description": "Demonstrates third-domain generalization, SPDX open-source license verification, comparative analysis matrix generation, and warm-start plan compilation (< 15ms)."
    }
}


async def run_single_demo(demo_key: str, mode: str, store_dir: Path) -> Dict[str, Any]:
    spec = DEMO_SPECS[demo_key]
    print("\n" + "=" * 80)
    print(f"  {spec['title'].upper()}")
    print("=" * 80)
    print(f"Domain:      {spec['domain']}")
    print(f"Mode:        {mode.upper()}")
    print(f"Description: {spec['description']}")
    print(f"Intent:      \"{spec['intent']}\"")
    print("-" * 80)

    # Set replay mode environment flag if requested
    if mode == "replay":
        os.environ["IOL_DEMO_REPLAY"] = "1"
    else:
        os.environ.pop("IOL_DEMO_REPLAY", None)

    db_path = store_dir / f"demo_{demo_key.lower()}_{mode}.db"
    store = DurableTaskStore(db_path=db_path)
    registry = CapabilityRegistry()
    register_outreach_capabilities(registry)
    register_live_research_capabilities(registry)
    planner = AdaptiveCapabilityPlanner(registry=registry)
    worker = BackgroundWorker(store=store, registry=registry, planner=planner)

    start_wall = time.time()
    task = store.create_task(
        intent=spec["intent"],
        user_id="demo_operator",
        metadata={"tenant_id": "conclave_demo"}
    )
    print(f"[*] Task created with ID: {task.task_id}")
    print("[*] Dispatching task to autonomous BackgroundWorker...")

    # Execute task
    await worker.process_task(task.task_id)
    duration_s = round(time.time() - start_wall, 2)

    completed = store.get_task(task.task_id)
    events = store.get_events(task.task_id)

    print(f"\n[+] Task finished with status: {completed.status.value.upper()} in {duration_s}s")
    print(f"[+] Total durable events logged: {len(events)}")

    # Extract UI and results
    ui = completed.ui_state
    rows = []
    comp_matrix = None

    if ui:
        for comp in ui.components:
            if comp.id == "candidate_table":
                rows = getattr(comp, "rows", [])
            elif comp.id == "comparative_matrix":
                comp_matrix = comp

    print(f"\n[RESULTS TABLE SUMMARY] — {len(rows)} Verified Records Delivered:")
    print("-" * 80)

    col_headers = spec["expected_columns"]
    header_str = " | ".join(h.replace("_", " ").title()[:20].ljust(20) for h in col_headers)
    print(header_str)
    print("-" * 80)

    for idx, row in enumerate(rows, start=1):
        fields = [str(row.get(h, "N/A"))[:18].ljust(20) for h in col_headers]
        print(" | ".join(fields))

    if comp_matrix:
        print("\n[+] Comparative Analysis Matrix Generated (Declarative Comparison Component)")
        print(f"    Entities Compared: {len(getattr(comp_matrix, 'entities', []))}")
        print(f"    Feature Dimensions: {len(getattr(comp_matrix, 'feature_categories', []))}")

    # Verify evidence metadata
    sample_evidence = None
    for r in rows:
        if "_field_evidence" in r and r["_field_evidence"]:
            sample_evidence = r["_field_evidence"]
            break

    if sample_evidence:
        print("\n[PROVENANCE & EVIDENCE SAMPLE]")
        first_field = next(iter(sample_evidence.keys()))
        ev = sample_evidence[first_field]
        print(f"    Field:          {ev.get('field_name')}")
        print(f"    Evidence URL:   {ev.get('evidence_url')}")
        print(f"    Source Type:    {ev.get('source_type')}")
        print(f"    Status:         {ev.get('verification_status')}")
        print(f"    Confidence:     {ev.get('confidence')} (Capped conservative score)")

    return {
        "demo": demo_key,
        "mode": mode,
        "task_id": task.task_id,
        "status": completed.status.value,
        "duration_seconds": duration_s,
        "records_count": len(rows),
        "events_count": len(events),
        "records": rows
    }


async def main():
    parser = argparse.ArgumentParser(description="IOL Engineers' Conclave Demonstration Runner")
    parser.add_argument(
        "--demo",
        choices=["A", "B", "C", "ALL"],
        default="A",
        help="Select demonstration: A (Academic Faculty), B (Indian Startups), C (AI Developer Tools), or ALL"
    )
    parser.add_argument(
        "--mode",
        choices=["live", "replay"],
        default="replay",
        help="Execution mode: 'live' queries public web/APIs; 'replay' uses offline verified fixtures (recommended for reliable presentations)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Optional path to save JSON results"
    )
    args = parser.parse_args()

    store_dir = ROOT_DIR / ".demo_data"
    store_dir.mkdir(exist_ok=True)

    demos_to_run = ["A", "B", "C"] if args.demo == "ALL" else [args.demo]
    all_results = {}

    for d in demos_to_run:
        res = await run_single_demo(d, args.mode, store_dir)
        all_results[d] = res

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2)
        print(f"\n[+] Demonstration results successfully saved to: {out_path}")

    print("\n" + "=" * 80)
    print("  ALL REQUESTED DEMONSTRATIONS COMPLETED SUCCESSFULLY")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
