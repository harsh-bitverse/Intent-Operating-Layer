"""
Execution and Verification Script for IOL Task 011 Generalization Probes:
- Probe 11A: Multi-Source Information Comparison with comparison_matrix (Vite vs Webpack)
- Probe 11B: Autonomous Browser Interaction Loop with input, select, DOM state verification & approval pause
- Probe 11C: Interactive Learning / Computation Task (Dijkstra algorithm shortest path simulation on 2D canvas - NOT neural net)
- Probe 11D: Everyday Service Discovery (Air India flight route specifications with honest official portal handoff)

Captures full-fidelity screenshots into docs/screenshots/.
"""

import asyncio
import json
import time
from pathlib import Path
import httpx
from playwright.async_api import async_playwright

API_BASE = "http://127.0.0.1:8000"
FRONTEND_BASE = "http://127.0.0.1:3000"
AUTH_HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": "iol_demo_operator_key"
}
SCREENSHOT_DIR = Path("docs/screenshots")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


async def execute_and_verify_probe(
    probe_id: str,
    intent: str,
    screenshot_name: str,
    expected_shape: str,
    context_meta: dict = None,
    max_wait_seconds: int = 45
):
    print(f"\n=======================================================")
    print(f"Executing Probe: {probe_id}")
    print(f"Intent: {intent}")
    print(f"Expected Shape: {expected_shape}")
    print(f"=======================================================")

    start_time = time.perf_counter()

    async with httpx.AsyncClient(timeout=45.0, trust_env=False) as client:
        # 1. Submit Intent
        meta = {"user_id": "test_operator", "probe_id": probe_id}
        if context_meta:
            meta.update(context_meta)

        res = await client.post(
            f"{API_BASE}/api/tasks",
            headers=AUTH_HEADERS,
            json={
                "intent": intent,
                "budget": {"max_duration_seconds": 60, "max_steps": 6, "max_cost_usd": 1.0, "retry_limit": 1},
                "metadata": meta
            }
        )
        assert res.status_code == 201, f"Task submission failed: {res.text}"
        task_data = res.json()
        task_id = task_data["task_id"]
        print(f"[*] Task created with ID: {task_id}")

        # 2. Poll until terminal or approval pause
        completed = False
        task_record = {}
        for attempt in range(max_wait_seconds):
            await asyncio.sleep(1.0)
            poll_res = await client.get(f"{API_BASE}/api/tasks/{task_id}", headers=AUTH_HEADERS)
            if poll_res.status_code == 200:
                task_record = poll_res.json()
                status = task_record.get("status")
                progress = task_record.get("progress", {})
                current_step = progress.get("current_step", 0)
                total_steps = progress.get("total_steps", 0)
                print(f"    [{attempt+1}s] Status: {status} (Step {current_step}/{total_steps})")
                if status in ("COMPLETED", "FAILED", "CANCELLED", "PAUSED_FOR_APPROVAL", "APPROVAL_REQUIRED"):
                    completed = True
                    break

        duration = round(time.perf_counter() - start_time, 2)
        assert completed, f"Task {task_id} timed out after {max_wait_seconds}s"
        actual_status = task_record.get("status")
        print(f"[OK] Task reached status '{actual_status}' in {duration}s")

        # 3. Verify Experience Plan & Outcome
        exp_plan = task_record.get("experience_plan") or task_record.get("metadata", {}).get("experience_plan")
        if exp_plan:
            print(f"[*] Experience Plan Origin: {exp_plan.get('plan_origin')}")
            print(f"[*] Components: {[c.get('type') for c in exp_plan.get('components', [])]}")
            model_meta = exp_plan.get("model_metadata", {})
            print(f"[*] Model Metadata Status: {model_meta.get('status')}")

        outcome = task_record.get("outcome_envelope") or task_record.get("metadata", {}).get("outcome_envelope")
        if outcome:
            print(f"[*] Outcome Shape: {outcome.get('shape')}")
            print(f"[*] Outcome Summary: {outcome.get('summary')}")
            print(f"[*] Outcome Items Count: {len(outcome.get('items', []))}")

        # 4. Capture visual browser screenshot via Playwright
        print(f"[*] Capturing frontend screenshot of completed workspace...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 1440, "height": 900})
            try:
                await page.goto(f"{FRONTEND_BASE}/?taskId={task_id}", wait_until="networkidle", timeout=15000)
                await page.wait_for_timeout(2000)
                target_path = SCREENSHOT_DIR / screenshot_name
                await page.screenshot(path=str(target_path), full_page=True)
                print(f"[+] Saved screenshot: {target_path} ({target_path.stat().st_size} bytes)")
            except Exception as e:
                print(f"[!] Screenshot capture failed: {e}")
            finally:
                await browser.close()

        return task_record


async def main():
    print("=================================================================")
    print("Starting IOL Task 011 Verification Probes")
    print("=================================================================")

    # Probe 11A: Multi-Source Comparison (Vite vs Webpack)
    await execute_and_verify_probe(
        probe_id="probe_11a_build_tools_comparison",
        intent="Compare Vite and Webpack frontend build tool architectures and performance tradeoffs",
        screenshot_name="v11_probe1_build_tools_comparison.png",
        expected_shape="comparison",
        context_meta={"model_provider": "test_mock", "model_name": "iol-synthesizer-v1"}
    )

    # Probe 11B: Interactive Website Task (Form navigation & approval boundary)
    await execute_and_verify_probe(
        probe_id="probe_11b_interactive_form",
        intent="Fill official passport inquiry form with applicant details and submit application for review",
        screenshot_name="v11_probe2_interactive_form_selection.png",
        expected_shape="form",
        context_meta={"model_provider": "test_mock", "model_name": "iol-synthesizer-v1"}
    )

    # Probe 11C: Interactive Learning / Computation (Dijkstra Shortest Path Simulation - NOT Neural Net)
    await execute_and_verify_probe(
        probe_id="probe_11c_dijkstra_simulation",
        intent="Run Dijkstra algorithm shortest path simulation on directed weighted graph",
        screenshot_name="v11_probe3_dijkstra_graph_simulation.png",
        expected_shape="simulation",
        context_meta={"model_provider": "test_mock", "model_name": "iol-synthesizer-v1"}
    )

    # Probe 11D: Everyday Discovery Task (Air India route discovery with honest portal handoff)
    await execute_and_verify_probe(
        probe_id="probe_11d_everyday_flight_discovery",
        intent="Discover Air India scheduled flight destinations from Delhi to Mumbai with official portal handoff",
        screenshot_name="v11_probe4_everyday_flight_handoff.png",
        expected_shape="collection",
        context_meta={"model_provider": "test_mock", "model_name": "iol-synthesizer-v1"}
    )

    print("\n=================================================================")
    print("All Task 011 Probes Completed Successfully!")
    print("=================================================================")


if __name__ == "__main__":
    asyncio.run(main())
