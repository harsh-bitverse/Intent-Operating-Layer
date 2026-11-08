# IOL v0.9 — General-Purpose End-to-End Execution & Generative Workspace Demo Runbook

**System:** Intent Operating Layer (IOL) v0.9  
**Target Milestone:** IIT Delhi Engineers' Conclave Submission & Live Demonstrations  
**Repository:** `https://github.com/harsh-bitverse/Intent-Operating-Layer.git`  
**Working Workspace:** `C:\Workspace\Products\Intent Operating Layer`  

---

## 1. Executive Summary & Core Principle

IOL is a visual-first, general-purpose intent-to-outcome operating platform. It turns high-level human objectives into verified, source-backed outcomes across APIs, browser automation, and data pipelines without human micro-management.

- **Primary Product Principle:** Get the user's actual work done reliably and deliver verified, structured outcomes.
- **Secondary Product Principle:** Learn reusable, typed capabilities from execution so that future similar or related work becomes progressively faster and cheaper across users without data leakage.
- **Truth Invariant:** Fallback layouts are never falsely labeled as `MODEL_GENERATED`. All web extracts retain verbatim DOM excerpts, cryptographic hashes, and exact retrieval timestamps. Consequential external actions remain strictly gated behind operator approval tickets.

---

## 2. 90-to-120 Second Demo Pitch & Live Walkthrough

### Act 1: The Problem & The Intent (0:00 – 0:30)
1. **Show the clean interface** at `http://localhost:3000`. Point out the session selector (demonstrating multi-tenant isolation and operator privilege boundaries).
2. **State an unfamiliar intent:**
   ```
   "Compare official documentation for Python 3 at https://docs.python.org/3/ and FastAPI at https://fastapi.tiangolo.com/"
   ```
3. **Click "Execute Intent →"**:
   - The Adaptive Execution Planner dynamically decomposes the goal into sequential `browser.navigate` and `browser.extract` capability steps.
   - Concurrently, the Experience Engine synthesizes a comparison workspace plan.

### Act 2: Multi-Step Live Browser Execution & Progressive Outcomes (0:30 – 1:00)
1. Point to the **Real-Time Step Timeline** and **Card Metrics**:
   - Status transitions to `RUNNING`.
   - The sandboxed Playwright session navigates to Python 3 documentation, extracts live headings and section anchors, and captures element telemetry.
   - The session navigates to FastAPI documentation, extracting framework metadata and community links.
2. Point to the **Adaptive Comparison Matrix**:
   - Rows stream in progressively without full-page reloads via Server-Sent Events (SSE).
   - Each row displays verified attribute names, target domains, and live status badges.

### Act 3: Verification, Provenance & Export (1:00 – 1:30)
1. Click any row or switch to the **Outcome Envelope** tab:
   - Point out the field-level cryptographic provenance: exact source URL, HTTP status (200), ISO-8601 retrieval timestamp, and raw DOM excerpt.
2. Click **"📦 Replay Bundle"** or **"Export CSV"**:
   - IOL exports a tamper-evident audit bundle verifying that no numbers, URLs, or facts were hallucinated.

### Act 4: Consequential Action Safety & Approval Gate (1:30 – 2:00)
1. Open the Action Approval Demo (`Test external write action approval lifecycle`):
   - Show how consequential actions (e.g. `EXTERNAL_WRITE` or `PAYMENT_OR_ORDER`) automatically pause task execution and generate an **ActionPanel**.
   - Show the consequence badge (`EXTERNAL WRITE (Approval Required)`) and scoped parameters.
   - Click **"✓ Approve & Execute"**: The system verifies the cryptographic ticket fingerprint, executes the action, and resumes task completion.

---

## 3. Preflight & Local Execution Commands

### Prerequisites
- Python 3.12+ with virtualenv or system packages
- Node.js 18+ and npm
- Playwright Chromium installed (`python -m playwright install chromium`)

### Terminal 1: Launch Backend API
```powershell
cd "C:\Workspace\Products\Intent Operating Layer"
python -m uvicorn backend.iol.api.app:app --host 127.0.0.1 --port 8000
```
Verify health:
```powershell
curl.exe -s --noproxy "*" http://127.0.0.1:8000/api/health
# Expected: {"status":"healthy","service":"Intent Operating Layer","version":"0.5.0-mvp","capabilities_loaded":15}
```

### Terminal 2: Launch Frontend Workspace
```powershell
cd "C:\Workspace\Products\Intent Operating Layer\frontend"
npm run dev -- -p 3000
```
Verify frontend:
```powershell
curl.exe -s --noproxy "*" -I http://127.0.0.1:3000
# Expected: HTTP/1.1 200 OK
```

### Run All Automated Verification Suites
```powershell
# 1. Run all 74 backend tests (includes browser substrate, SSRF, injection defenses, and live research)
python -m pytest backend/tests -v

# 2. Run all 41 legacy outreach integration tests
python -m pytest "C:\Workspace\Projects\Outreach Intelligence Engine\tests" -q

# 3. Run all 11 Playwright E2E suites
cd frontend
npx playwright test
```

### Run Live Generalization Probes
```powershell
python scripts/run_task009_probes.py
```

---

## 4. Capabilities & Limitations Matrix

| Feature / Domain | Current Working Implementation | Security Invariant / Restriction | Limitation / Next Step |
| :--- | :--- | :--- | :--- |
| **Browser Substrate** | Headless Playwright Chromium with multi-step session manager, DOM heading/link extraction, viewport screenshots. | Strict SSRF filter blocks `169.254.169.254`, IPv6 loopbacks, and RFC1918 private IPs unless explicitly whitelisted institutional domain. | Dynamic SPA javascript heavy rendering capped at 20s timeout per step. |
| **Prompt Injection Defense** | Neutralizes LLM delimiter tokens (`<|im_start|>`, `[INST]`) and adversarial phrases (`ignore previous instructions`) in DOM text. | Untrusted page content is defanged before passing to models or telemetry. | Zero-day steganographic or prompt-in-image attacks require visual OCR guardrails. |
| **Experience Engine** | Declarative catalog (`workspace_layout`, `metric_strip`, `data_grid`, `comparison_matrix`, `interactive_canvas_2d`, `form_draft`, `action_panel`). | Schema validator enforces component allowlisting, tree depth bounds (<4), and script injection defenses. | When cloud LLM keys (`OPENAI_API_KEY`) are absent, truthfully reports `RECIPE_ADAPTED` with documented reason. |
| **Action Approvals** | Cryptographic ticket fingerprints, consequence tier classification (`READ`, `LOCAL_DRAFT`, `EXTERNAL_WRITE`, `PAYMENT_OR_ORDER`). | Consequential writes are strictly halted until explicit operator approval ticket submission. Anti-replay enforced. | Rejection requires operator manual intervention; automated mitigation planning in v1.0. |
| **Outcome Envelopes** | Normalized typed envelope (`DOCUMENT`, `COMPARISON`, `COLLECTION`, `SIMULATION`) with monotonic revision streaming over SSE. | Field-level cryptographic hash, source URL, and exact ISO retrieval timestamps attached to every record. | Multi-page PDF document OCR parsing planned for future document capabilities. |

---

## 5. Verified Screenshots Directory

All visual artifacts are saved in `docs/screenshots/`:
- `v09_probe1_doc_comparison.png`: Live multi-step documentation comparison (Python 3 vs FastAPI).
- `v09_probe2_iitd_portal.png`: Live institutional portal navigation (IIT Delhi Home).
- `v08_demo1_browser_extraction.png`: Real browser navigation to public site with telemetry and screenshot.
- `v08_demo4_form_draft.png`: Public service form draft with `LOCAL_DRAFT` safety badge.
- `v08_action_approval_verified.png`: Scoped action approval panel with consequence tier and ticket execution.
- `v06_demo_a_research_workspace.png`: Adaptive research workspace with full-screen data grid and evidence drawer.
- `v06_demo_b_neural_simulation.png`: Educational 2D node-edge canvas with interactive step controller.
- `tenant_isolation_403.png`: Cross-tenant authorization boundary blocking unauthorized access.
