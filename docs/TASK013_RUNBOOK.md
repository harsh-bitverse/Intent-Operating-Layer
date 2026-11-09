# IOL Task 013 — Operational Runbook & Verification Manual

## 1. System Overview & Task 013 Objectives

This operational runbook provides complete instructions to verify, execute, and evaluate **IOL Task 013: Activate Real Intelligence and Deliver the First Complete Intent-to-Outcome Experience**.

### Core Technical Invariants Enforced in Task 013:

1. **Strict Model Runtime Provenance Enforcement:**
   - `MODEL_GENERATED`: Assigned **ONLY** when inference is verified to originate from a trusted, authentic foundation-model provider endpoint (`api.openai.com`, `api.anthropic.com`, `generativelanguage.googleapis.com`, or an active local Ollama daemon verified via `/api/version`).
   - `TEST_SYNTHESIZED`: Enforced for all synthetic generation, fixtures, and local HTTP test mock servers on loopback interfaces (`127.0.0.1`, `localhost`). A 200 OK HTTP response alone is **never** accepted as proof of real model inference.
   - **Zero Self-Assertion:** Payloads attempting to self-assert `"plan_origin": "MODEL_GENERATED"` from untrusted endpoints are strictly intercepted, rejected, and rewritten to `TEST_SYNTHESIZED`.
2. **Transport vs Inference Latency Separation:**
   - Every inference response separates network transit latency (`transport_latency_ms`) from provider model compute latency (`inference_latency_ms`).
3. **Truthful Telemetry & Blocker Reporting:**
   - When external provider credentials are not present in the runtime environment, IOL immediately and truthfully reports `status: "REAL_MODEL_BLOCKED"`, documents the exact user setup steps, and falls back to deterministic/recipe execution without fabricating model inference or usage metrics.
4. **Model-Directed Capability Planning with Inviolable Authorization Gates:**
   - The adaptive capability planner composes capabilities dynamically via model reasoning.
   - Irreversible/consequential capabilities (e.g. form submission, external transactions) must pass through deterministic authorization policies (`action_approval_manager`); the model cannot grant itself execution authority.
5. **Product-Level Generalization Across 3 Unfamiliar Tasks:**
   - **Task 1 (Browser Interaction Beyond Extraction):** Multi-step form discovery, input typing, verified DOM mutation, and consequential submit gate pause.
   - **Task 2 (Algorithmic Computation & Data Transformation):** Dijkstra shortest path priority queue relaxation on directed graphs, calculating exact path (`A -> C -> B -> E`, cost `7.0`) and streaming into an interactive canvas.
   - **Task 3 (Real-World Comparative Analysis):** Architectural comparison matrix with verified source evidence.

---

## 2. Environment Setup & Provider Activation Guide

### A. Environment Audit
Verify whether any model provider credentials exist in your current shell:

```powershell
Get-ChildItem env: | Where-Object { $_.Name -match "OPENAI|ANTHROPIC|GEMINI|GOOGLE|OLLAMA" }
```

### B. Activating Real Foundation Model Intelligence (User Setup Steps)

To run IOL with live model intelligence, configure at least one authorized provider before starting the backend server:

#### Option 1: Google Gemini (Recommended — Native Structured JSON)
```powershell
$env:GEMINI_API_KEY = "AIzaSy..."
$env:IOL_EXP_MODEL = "gemini-1.5-flash"  # or gemini-2.0-flash
```

#### Option 2: OpenAI
```powershell
$env:OPENAI_API_KEY = "sk-..."
$env:IOL_EXP_MODEL = "gpt-4o-mini"       # or gpt-4o
```

#### Option 3: Anthropic
```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
$env:IOL_EXP_MODEL = "claude-3-5-haiku-20241022"
```

#### Option 4: Local Ollama Daemon
Ensure Ollama is installed and running (`ollama serve`), then pull the model:
```powershell
ollama pull llama3.2
$env:OLLAMA_HOST = "http://127.0.0.1:11434"
$env:IOL_EXP_MODEL = "llama3.2"
```

> **Security & Privacy Invariant:** API keys are never persisted to disk, logged in plaintext, or committed to Git.

---

## 3. Starting the Services

### 1. Launch FastAPI Backend
From the workspace root (`C:\Workspace\Products\Intent Operating Layer`):
```powershell
python -m uvicorn backend.iol.api.app:app --host 127.0.0.1 --port 8000
```

Verify backend health (using proxy bypass):
```powershell
python -c "import urllib.request, os; os.environ['NO_PROXY']='*'; print(urllib.request.urlopen('http://127.0.0.1:8000/api/health').read().decode())"
# Expected response: {"status":"healthy","service":"Intent Operating Layer","version":"0.5.0-mvp","capabilities_loaded":17}
```

### 2. Launch Next.js Frontend
From the `frontend/` directory:
```powershell
cd frontend
npm run dev -- -p 3000
```

Verify frontend liveness:
```powershell
python -c "import urllib.request, os; os.environ['NO_PROXY']='*'; print(urllib.request.urlopen('http://127.0.0.1:3000').getcode())"
# Expected response: 200
```

---

## 4. Test Suite Execution & Verification

### A. Full Backend Automated Test Suite (100 tests)
Run all 21 test modules across the backend:
```powershell
python -m pytest backend/tests -v
```
All 100 tests pass, covering:
- Strict foundation model runtime verification (`is_trusted_foundation_model_runtime`)
- Rejection of masquerading loopback servers attempting to claim `MODEL_GENERATED`
- Truthful `REAL_MODEL_BLOCKED` diagnostic reporting when credentials are missing
- Separate transport and inference latency measurements
- Bounded model-directed capability planning with safety policy gates
- Three product-level generalization tasks (browser interaction, Dijkstra simulation, comparative matrix)

### B. Legacy Outreach Engine Regression Suite (41 tests)
```powershell
python -m pytest tests -q
# Ran from C:\Workspace\Projects\Outreach Intelligence Engine
# 41 passed in ~2.0s
```

### C. Playwright End-to-End Suite for Task 013 (3 tests)
From the `frontend/` directory:
```powershell
cd frontend
npx playwright test e2e_task013_suite.spec.ts
```
Expected output:
- `ok 1 Probe 1: Strict Provenance - Mock/Synthetic Provider is explicitly tagged TEST_SYNTHESIZED`
- `ok 2 Probe 2: Unconfigured Credentials truthfully reports REAL_MODEL_BLOCKED setup status`
- `ok 3 Probe 3: Algorithmic Simulation - Dijkstra graph relaxation outcome verification`

---

## 5. Live Demonstration & Visual Screenshot Capture

Execute the automated visual probe script to reproduce the authentic documentation screenshots:
```powershell
python scripts/run_task013_probes.py
```

Generated full-page visual captures in `docs/screenshots/`:
1. `docs/screenshots/v13_probe1_strict_provenance_masquerade_rejected.png`:
   - Proves that an untrusted local HTTP server attempting to self-assert `MODEL_GENERATED` is strictly overridden to `TEST_SYNTHESIZED` with `SIMULATED` usage mode and `UNTRUSTED_LOOPBACK` trust score.
2. `docs/screenshots/v13_probe2_real_model_blocked_diagnostics.png`:
   - Proves that an unconfigured environment truthfully reports `REAL_MODEL_BLOCKED` with setup instructions and adapts safely without false claims.
3. `docs/screenshots/v13_probe3_generalization_browser_approval.png`:
   - Demonstrates the interactive Dijkstra directed graph relaxation canvas with step-by-step priority queue state updates and optimal path calculation (`A -> C -> B -> E`, cost 7.0).
