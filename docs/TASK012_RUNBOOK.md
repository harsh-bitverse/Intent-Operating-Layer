# IOL Task 012 — Operational Runbook & Verification Manual

## 1. System Overview & Task 012 Objectives
This runbook provides complete operational reproduction procedures for **IOL Task 012: Real Model Inference & End-to-End Generative Experience Verification**.

### Core Invariants Enforced in Task 012:
1. **Strict Provenance Integrity:**
   - `MODEL_GENERATED`: Assigned **ONLY** when live HTTP network inference occurs through a foundation model provider (`openai`, `anthropic`, `gemini`, `ollama`) and produces a catalog-validated plan.
   - `TEST_SYNTHESIZED`: Assigned when synthesized via the built-in offline test engine (`mock`, `test_mock`).
   - `RECIPE_ADAPTED` / `DETERMINISTIC_FALLBACK`: Assigned when no model credentials are provided or inference fails, reporting `status: "MODEL_GENERATION_BLOCKED"` or `"MODEL_GENERATION_FAILED"`.
2. **Accurate Usage Tracking:**
   - Actual measured provider token counts are tagged with `usage_type: "ACTUAL"` and `is_estimated: false`.
   - Simulated test token counts are tagged with `usage_type: "SIMULATED"` and `is_estimated: true`. Zero fabricated tokens are ever passed off as actual provider metrics.
3. **Localhost Proxy Bypass:**
   - Any local Ollama or OpenAI-compatible endpoint on `127.0.0.1` or `localhost` automatically bypasses corporate HTTP proxies using `ProxyHandler({})`.
4. **Novel Workspace Expressiveness:**
   - Dynamically synthesizes unfamiliar structures (e.g., comparative architectural matrices with custom columns, spacecraft trajectory mission trackers) without hardcoded task names or dedicated pages.
5. **Knowledge Reuse & Latency Optimization:**
   - Reuses structural signatures and layout geometries from `ExperienceKnowledgeStore` with sub-millisecond warm adaptation (<2ms) vs cold generation.

---

## 2. Environment Setup & Provider Activation

### A. Prerequisites
- Python 3.12+ with virtual environment activated.
- Node.js 20+ with npm dependencies installed in `frontend/`.
- Playwright Chromium installed (`npx playwright install chromium`).

### B. Live Foundation Model Activation (Optional)
To activate live model generation, set the respective API key in your shell:

#### OpenAI
```powershell
$env:OPENAI_API_KEY = "sk-..."
$env:IOL_EXP_MODEL = "gpt-4o-mini"
```

#### Anthropic
```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
$env:IOL_EXP_MODEL = "claude-3-5-haiku-20241022"
```

#### Google Gemini
```powershell
$env:GEMINI_API_KEY = "AIzaSy..."
$env:IOL_EXP_MODEL = "gemini-1.5-flash"
```

#### Local Ollama (OpenAI-compatible)
```powershell
$env:OLLAMA_HOST = "http://127.0.0.1:11434"
$env:IOL_EXP_MODEL = "llama3.2"
```

> **Security Note:** Never commit API keys to version control. Keys can also be passed per-task via `metadata: { "model_api_key": "..." }`.

---

## 3. Starting the Services

### 1. Launch FastAPI Backend
```powershell
# From repository root:
python -m uvicorn backend.iol.api.app:app --host 127.0.0.1 --port 8000
```
Verify health:
```powershell
curl.exe --noproxy "*" -s http://127.0.0.1:8000/api/health
# Response: {"status":"healthy","service":"Intent Operating Layer","version":"0.5.0-mvp","capabilities_loaded":17}
```

### 2. Launch Next.js Frontend
```powershell
cd frontend
npm run dev -- -p 3000
```
Verify frontend:
```powershell
curl.exe --noproxy "*" -s -I http://127.0.0.1:3000
# Response: HTTP/1.1 200 OK
```

---

## 4. Test Suite Execution & Verification

### A. Full Backend Automated Test Suite (93 tests)
```powershell
python -m pytest backend/tests -v
```
All 93 tests cover:
- Real model inference HTTP network loop
- Strict provenance integrity (`MODEL_GENERATED` vs `TEST_SYNTHESIZED` vs `RECIPE_ADAPTED`)
- Unconfigured blocker reporting (`MODEL_GENERATION_BLOCKED`)
- Novel comparative and trajectory generation
- Knowledge reuse cold vs warm latency benchmarking (>5x speedup)
- Browser loop DOM state verification and consequential action gating

### B. Legacy Outreach Suite (41 tests)
```powershell
cd "c:\Workspace\Projects\Outreach Intelligence Engine"
python -m pytest tests -q
```
All 41 legacy tests pass cleanly.

### C. Playwright End-to-End Browser Tests (14 tests)
```powershell
cd frontend
npx playwright test
```
Verifies full user journeys, research grids, neural canvases, full-screen workspace modes, browser loops, form drafts, action approvals, and Task 012 novel comparative/trajectory workspaces.

---

## 5. Capturing Live Demonstration Visual Evidence
To capture the three Task 012 visual screenshots automatically into `docs/screenshots/`:
```powershell
python scripts/run_task012_probes.py
```
Generated artifacts:
1. `docs/screenshots/v12_probe1_rust_vs_go_comparative_matrix.png`
2. `docs/screenshots/v12_probe2_spacecraft_trajectory_telemetry.png`
3. `docs/screenshots/v12_probe3_real_http_model_generated.png`
