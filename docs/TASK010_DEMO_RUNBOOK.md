# IOL Task 010 — Demonstration Runbook
## Genuine Model-Directed Execution & Generative Experiences

**System:** Intent Operating Layer (IOL v0.10)  
**Baseline:** Post-Task 009 (Commit `a0d7105`)  
**Date:** November 8, 2026  
**Status:** FULLY VERIFIED & READY FOR EC DEMONSTRATION  

---

## 1. Quickstart & Service Execution

### A. Environment Prerequisites
- Python 3.12+ with dependencies installed (`pip install -e .` or `requirements.txt`)
- Node.js 18+ and npm installed
- Chromium installed for Playwright (`playwright install chromium`)

### B. Launching Background Servers

1. **Start FastAPI Backend Server (Port 8000):**
```powershell
python -m uvicorn backend.iol.api.app:app --host 127.0.0.1 --port 8000
```
*Health verification:*
```powershell
curl -s http://127.0.0.1:8000/api/health
# {"status":"healthy","service":"Intent Operating Layer","version":"0.5.0-mvp","capabilities_loaded":16}
```

2. **Start Next.js Frontend Server (Port 3000):**
```powershell
cd frontend
npm run dev -- -p 3000
```
*Web dashboard accessible at: `http://localhost:3000`*

---

## 2. Automated Test Verification (133 Tests)

Execute the full suite of automated unit, integration, security, and Playwright E2E tests:

```powershell
# 1. Run full backend test suite (81 tests)
python -m pytest backend/tests -v

# 2. Run legacy outreach test suite (41 tests)
python -m pytest "c:\Workspace\Projects\Outreach Intelligence Engine\tests" -q

# 3. Run Playwright end-to-end browser tests (11 tests)
cd frontend
npx playwright test
```

**Total Automated Baseline:** 133/133 tests passing with 0 failures.

---

## 3. Live Demonstration Probes (`scripts/run_task010_probes.py`)

Run the automated live probe runner to execute all four Task 010 demonstrations against the live system and generate full-fidelity screenshots:

```powershell
python scripts/run_task010_probes.py
```

### Demonstration Landmark Highlights

#### Demo 10A — Multi-Source Information Comparison Matrix
- **Intent:** `"Compare FastAPI vs Flask web frameworks: architecture, concurrency, typing, and licensing"`
- **Architecture:** Autonomous planner creates dual navigation steps to official documentation sites (`https://fastapi.tiangolo.com/` and `https://flask.palletsprojects.com/`).
- **Outcome Shape:** `OutcomeShape.COMPARISON` with 13 structured records.
- **Experience Component:** Adaptive `comparison_matrix` with side-by-side criteria evaluation.
- **Screenshot Asset:** `docs/screenshots/v10_probe1_comparison_matrix.png`

#### Demo 10B — Interactive Form Exploration with Approval Boundary Halt
- **Intent:** `"Interactive browser loop to explore form inputs, draft registration, and submit form on https://httpbin.org/forms/post"`
- **Architecture:** `browser.interaction_loop` cycles through `observe -> select -> validate -> execute -> verify -> stop`.
- **Form Discovery:** Discovers `<input name="custname">`, `<input name="custtel">`, `<input name="custemail">`, `<input name="size">`, and populates realistic draft values.
- **Safety Boundary:** When encountering the `<button>Submit order</button>`, `BrowserPolicy` classifies it as `EXTERNAL_WRITE`/`PAYMENT_OR_ORDER`, halting execution cleanly at `PAUSED_FOR_APPROVAL`.
- **Outcome:** Populated draft values are verified in the DOM and preserved without submitting unapproved external data.
- **Screenshot Asset:** `docs/screenshots/v10_probe2_form_draft_approval.png`

#### Demo 10C — Unfamiliar Expressive Visual Workspace (Neural Simulation)
- **Intent:** `"Teach me how a neural network learns with interactive visual simulation and step by step backpropagation"`
- **Architecture:** Dispatches `educational.neural_simulation` capability.
- **Outcome Shape:** `OutcomeShape.SIMULATION` with loss reduction from `0.0828` to `0.0811`.
- **Experience Component:** `interactive_canvas_2d` rendering 2-input, 2-hidden, 1-output node-edge architecture with step-by-step playback controls across 5 phases (Forward Pass, Hidden Activations, Loss Calculation, Backpropagation, Gradient Descent).
- **Screenshot Asset:** `docs/screenshots/v10_probe3_visual_simulation.png`

#### Demo 10D — Everyday Task: Flight Route Discovery with Honest Handoff
- **Intent:** `"Check flight route details and schedule specifications for Air India AI101 from DEL to JFK with official booking portal"`
- **Architecture:** Navigates public encyclopedia destination for route and schedule specifications.
- **Guardrail Against Hallucinated Bookings:**
  - *Summary Note:* "Extracted route & schedule specifications from official encyclopedic sources. Live fares and seat bookings require official airline portal authentication; no speculative prices or fake bookings fabricated."
  - *Handoff Component:* Binds an `action_panel` component with `action_type: "external.portal_handoff"` directing operator to authenticated airline session.
- **Screenshot Asset:** `docs/screenshots/v10_probe4_flight_route_handoff.png`

---

## 4. Phase 1 Model-Directed Generation vs. Blocked Reporting

To demonstrate genuine `MODEL_GENERATED` experience generation with token tracking:

```python
from backend.iol.experience.gateway import model_provider_gateway

# 1. With configured provider (or test mock)
plan = await model_provider_gateway.generate_plan(
    task_id="demo_model_task",
    intent="Build live latency analytics workspace",
    context_metadata={"model_provider": "mock", "model_api_key": "active_key"}
)
print(plan.plan_origin)  # "MODEL_GENERATED"
print(plan.model_metadata["usage"])  # {'prompt_tokens': 120, 'completion_tokens': 180, 'total_tokens': 300}

# 2. When credentials missing (zero mislabeling)
plan_blocked = experience_planner.plan_experience(
    task_id="demo_blocked_task",
    intent="Build live latency analytics workspace",
    context_metadata={}
)
print(plan_blocked.plan_origin)  # "RECIPE_ADAPTED"
print(plan_blocked.model_metadata["status"])  # "MODEL_GENERATION_BLOCKED"
```

---

## 5. Visual Asset Index

| Screenshot | Description | Key Landmarks |
|---|---|---|
| `docs/screenshots/v10_probe1_comparison_matrix.png` | Structure 1: Information Comparison | `COMPARISON` badge, dual-documentation extraction, structured columns |
| `docs/screenshots/v10_probe2_form_draft_approval.png` | Structure 2: Form Draft & Approval | Discovered inputs, verified draft values, DOM confirmation |
| `docs/screenshots/v10_probe3_visual_simulation.png` | Structure 3: Visual 2D Canvas | Interactive nodes, weights, backward step controller, loss delta |
| `docs/screenshots/v10_probe4_flight_route_handoff.png` | Phase 4: Flight Route & Honest Handoff | Public route specifications, no fake fares, official handoff panel |
