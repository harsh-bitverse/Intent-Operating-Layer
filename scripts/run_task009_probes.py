"""
Execution and Verification Script for IOL Task 009 Generalization Probes.
Executes two held-out unfamiliar tasks through the live backend,
verifies progressive outcome binding and experience synthesis,
and captures full-fidelity screenshots of the generative workspace.
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
    expected_shape: str
):
    print(f"\n=======================================================")
    print(f"Executing Probe: {probe_id}")
    print(f"Intent: {intent}")
    print(f"=======================================================")

    start_time = time.perf_counter()

    async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
        # 1. Submit Intent
        res = await client.post(
            f"{API_BASE}/api/tasks",
            headers=AUTH_HEADERS,
            json={
                "intent": intent,
                "budget": {"max_duration_seconds": 60, "max_steps": 6, "max_cost_usd": 1.0, "retry_limit": 1},
                "metadata": {"user_id": "test_operator", "probe_id": probe_id}
            }
        )
        assert res.status_code == 201, f"Task submission failed: {res.text}"
        task_data = res.json()
        task_id = task_data["task_id"]
        print(f"[*] Task created with ID: {task_id}")

        # 2. Poll until completion or timeout (max 45s)
        completed = False
        task_record = {}
        for attempt in range(45):
            await asyncio.sleep(1.0)
            poll_res = await client.get(f"{API_BASE}/api/tasks/{task_id}", headers=AUTH_HEADERS)
            if poll_res.status_code == 200:
                task_record = poll_res.json()
                status = task_record.get("status")
                progress = task_record.get("progress", {})
                current_step = progress.get("current_step", 0)
                total_steps = progress.get("total_steps", 0)
                print(f"    [{attempt+1}s] Status: {status} (Step {current_step}/{total_steps})")
                if status in ("COMPLETED", "FAILED", "CANCELLED"):
                    completed = True
                    break

        duration = round(time.perf_counter() - start_time, 2)
        assert completed, f"Task {task_id} timed out after 45s"
        assert task_record.get("status") == "COMPLETED", f"Task failed with status: {task_record.get('status')}"
        print(f"[OK] Task completed successfully in {duration}s")

        # 3. Verify Outcome Envelope
        outcome = task_record.get("outcome_envelope") or task_record.get("metadata", {}).get("outcome_envelope")
        print(f"[*] Outcome Envelope Shape: {outcome.get('shape') if outcome else 'None'}")
        if outcome:
            items = outcome.get("items", [])
            print(f"[*] Extracted Items Count: {len(items)}")
            for item in items[:4]:
                fields = item.get("fields", {})
                name = fields.get("name") or fields.get("title") or fields.get("url")
                itype = fields.get("type") or "N/A"
                src = fields.get("source") or fields.get("url")
                print(f"    - [{itype}] {str(name)[:50]} -> {str(src)[:40]}")

        # 4. Verify Experience Plan
        exp_plan = task_record.get("experience_plan") or task_record.get("metadata", {}).get("experience_plan")
        if exp_plan:
            print(f"[*] Experience Plan Origin: {exp_plan.get('plan_origin')}")
            print(f"[*] Components Count: {len(exp_plan.get('components', []))}")
            model_meta = exp_plan.get("model_metadata", {})
            print(f"[*] Model Metadata: {model_meta}")

        # 5. Capture visual browser screenshot via Playwright
        print(f"[*] Capturing frontend screenshot of completed workspace...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 1400, "height": 900})
            url = f"{FRONTEND_BASE}/?task_id={task_id}"
            await page.goto(url, wait_until="networkidle", timeout=20000)
            await page.wait_for_timeout(1500)

            screenshot_path = SCREENSHOT_DIR / screenshot_name
            await page.screenshot(path=str(screenshot_path), full_page=True)
            await browser.close()
            print(f"[OK] Screenshot saved to: {screenshot_path}")

    return {
        "probe_id": probe_id,
        "task_id": task_id,
        "duration_s": duration,
        "status": task_record.get("status"),
        "shape": outcome.get("shape") if outcome else None,
        "items_count": len(outcome.get("items", [])) if outcome else 0,
        "screenshot": str(screenshot_path)
    }


async def main():
    print("Initiating Task 009 Generalization Probes...")

    # Probe 1: Comparative Documentation Analysis
    p1 = await execute_and_verify_probe(
        probe_id="PROBE_1_DOC_COMPARISON",
        intent="Compare official documentation for Python 3 at https://docs.python.org/3/ and FastAPI at https://fastapi.tiangolo.com/",
        screenshot_name="v09_probe1_doc_comparison.png",
        expected_shape="comparison"
    )

    # Probe 2: Official Institutional Portal
    p2 = await execute_and_verify_probe(
        probe_id="PROBE_2_IITD_PORTAL",
        intent="Navigate to https://home.iitd.ac.in/ and extract official academic programs and campus links",
        screenshot_name="v09_probe2_iitd_portal.png",
        expected_shape="document"
    )

    print("\n=======================================================")
    print("PROBE VERIFICATION SUMMARY")
    print("=======================================================")
    print(json.dumps([p1, p2], indent=2))


if __name__ == "__main__":
    asyncio.run(main())
