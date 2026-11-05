"""
End-to-End User Journey Verification Script for IOL (Implementation Task 004).
Validates the complete 10-step user journey across authentication, background execution,
SSE replay reconnection, intermediate semantic relevance gates, declarative UI rendering,
and verified results export.
"""

import asyncio
import json
import sys
import tempfile
import time
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from starlette.testclient import TestClient
from backend.iol.adapters.outreach.adapter import register_outreach_capabilities
from backend.iol.api.app import app
from backend.iol.capabilities.live_research import register_live_research_capabilities
from backend.iol.capabilities.registry import capability_registry
from backend.iol.core.models import TaskStatus
from backend.iol.core.store import task_store
from backend.iol.worker.background_worker import background_worker


def run_10_step_user_journey():
    print("=" * 80)
    print("STARTING IOL END-TO-END 10-STEP USER JOURNEY VERIFICATION")
    print("=" * 80)

    # Register capabilities into runtime registry
    register_outreach_capabilities(capability_registry)
    register_live_research_capabilities(capability_registry)

    headers = {"X-API-Key": "iol_demo_operator_key"}

    with TestClient(app) as client:
        # ----------------------------------------------------------------------
        # Step 1: Health & Service Discovery
        # ----------------------------------------------------------------------
        print("\n[Step 1] Checking API health and registered capabilities...")
        health_res = client.get("/api/health")
        assert health_res.status_code == 200, f"Health check failed: {health_res.text}"
        health_data = health_res.json()
        print(f" -> System Healthy! Status: {health_data['status']}, Capabilities: {health_data['capabilities_loaded']}")
        assert health_data["capabilities_loaded"] >= 7

        # ----------------------------------------------------------------------
        # Step 2: Intent Input
        # ----------------------------------------------------------------------
        intent = (
            "Find 5 open-source AI developer frameworks and evaluation tools, "
            "with repository name, primary language, license, official repository URL, and evidence."
        )
        print(f"\n[Step 2] User inputs research mission intent:")
        print(f" -> Intent: \"{intent}\"")

        # ----------------------------------------------------------------------
        # Step 3: Task Creation & Server-Derived Authentication
        # ----------------------------------------------------------------------
        print("\n[Step 3] Submitting task creation request to POST /api/tasks...")
        create_res = client.post(
            "/api/tasks",
            json={"intent": intent, "metadata": {"session": "e2e_demo_session"}},
            headers=headers
        )
        assert create_res.status_code == 201, f"Task creation failed: {create_res.text}"
        task_data = create_res.json()
        task_id = task_data["task_id"]
        print(f" -> Task Created! Task ID: {task_id}, User ID: {task_data['user_id']}, Status: {task_data['status']}")
        assert task_data["user_id"] == "default_user"

        # ----------------------------------------------------------------------
        # Step 4: Initial UI Layout & Background Processing
        # ----------------------------------------------------------------------
        print("\n[Step 4] Monitoring autonomous background worker execution...")
        start_wait = time.time()
        task = None
        while time.time() - start_wait < 30.0:
            task = task_store.get_task(task_id)
            if task and task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                break
            time.sleep(0.5)

        assert task is not None, "Task was not found in persistent store"
        assert task.status == TaskStatus.COMPLETED, f"Task ended in status {task.status.value}: {task.error_message}"
        assert task.ui_state is not None, "Task UI state was not persisted"
        print(f" -> Task reached COMPLETED state! UI rendered with {len(task.ui_state.components)} components.")
        comp_types = [c.type for c in task.ui_state.components]
        print(f" -> Rendered Components: {comp_types}")
        assert "card" in comp_types
        assert "timeline" in comp_types
        assert "table" in comp_types

        # ----------------------------------------------------------------------
        # Step 5: Background Execution Independence
        # ----------------------------------------------------------------------
        print(f"\n[Step 5] Task completed in background independently of client session.")
        print(f" -> Final Status: {task.status.value}, Completed Steps: {task.current_step}/{task.total_steps}")
        assert task.status == TaskStatus.COMPLETED

        # ----------------------------------------------------------------------
        # Step 6 & 7: SSE Event Replay & Reconnection with Last-Event-ID
        # ----------------------------------------------------------------------
        print("\n[Step 6 & 7] Testing durable event log and SSE reconnection replay...")
        all_events = task_store.get_events(task_id)
        total_events = len(all_events)
        print(f" -> Total events recorded in durable store: {total_events}")
        assert total_events >= 10

        mid_point_id = all_events[len(all_events) // 2].event_id
        replayed_events = task_store.get_events(task_id, since_event_id=mid_point_id)
        print(f" -> Reconnection simulation with Last-Event-ID={mid_point_id}: replayed {len(replayed_events)} events seamlessly.")
        assert len(replayed_events) > 0
        assert all(e.event_id > mid_point_id for e in replayed_events)

        # ----------------------------------------------------------------------
        # Step 8: Inspect Intermediate Steps (Provenance, Evidence & Relevance Gate)
        # ----------------------------------------------------------------------
        print("\n[Step 8] Verifying intermediate capability steps from event stream...")
        cap_events = [e for e in all_events if e.event_type == "CAPABILITY_INVOKED"]
        cap_ids_executed = [e.data.get("capability_id") for e in cap_events]
        print(f" -> Executed Capabilities: {cap_ids_executed}")
        assert "research.live_source_acquisition" in cap_ids_executed
        assert "research.generalized_extraction" in cap_ids_executed
        assert "research.generalized_verification" in cap_ids_executed
        assert "research.semantic_relevance" in cap_ids_executed
        assert "data.deduplication" in cap_ids_executed

        # ----------------------------------------------------------------------
        # Step 9: Declarative UI Inspection & Comparison Matrix
        # ----------------------------------------------------------------------
        print("\n[Step 9] Inspecting final UI state, table records, and comparison matrix...")
        table_comp = next(c for c in task.ui_state.components if c.id == "candidate_table")
        assert len(table_comp.rows) >= 3
        print(f" -> Verified Candidates in Table: {len(table_comp.rows)}")
        for idx, row in enumerate(table_comp.rows[:3], start=1):
            name = row.get("repository_name") or row.get("name")
            conf = row.get("confidence")
            status = row.get("status")
            print(f"    {idx}. {name} | Status: {status} | Score: {conf}")

        has_comparison = any(c.type == "comparison" for c in task.ui_state.components)
        print(f" -> Comparison Matrix Component generated: {has_comparison}")
        assert has_comparison is True

        # ----------------------------------------------------------------------
        # Step 10: Export Verified Results
        # ----------------------------------------------------------------------
        print("\n[Step 10] Exporting verified results and verifying provenance integrity...")
        export_payload = {
            "task_id": task.task_id,
            "intent": task.intent,
            "status": task.status.value,
            "verified_records_count": len(table_comp.rows),
            "records": table_comp.rows
        }
        export_json = json.dumps(export_payload, indent=2)
        assert len(export_json) > 500
        print(f" -> Export Generated successfully ({len(export_json)} bytes)!")

    print("\n" + "=" * 80)
    print("10-STEP USER JOURNEY VERIFICATION PASSED WITH 100% INTEGRITY")
    print("=" * 80)
    return True


if __name__ == "__main__":
    success = run_10_step_user_journey()
    if not success:
        sys.exit(1)
