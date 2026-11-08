# IOL Task 011 — Demonstration Runbook
## Genuine Generative UI, Adaptive Workspaces & Open-Ended Execution

**System:** Intent Operating Layer (IOL v0.11)  
**Baseline:** Post-Task 010 (Commit `1d8c00f`)  
**Date:** November 8, 2026  
**Status:** FULLY IMPLEMENTED, VERIFIED & PASSING

---

## 1. Quickstart & Service Execution

### A. Environment Prerequisites
- Python 3.12+ with dependencies installed (`pip install -e .`)
- Node.js 18+ and npm installed
- Chromium installed for Playwright (`npx playwright install chromium`)

### B. Launching Background Servers

1. **Start FastAPI Backend Server (Port 8000):**
```powershell
python -m uvicorn backend.iol.api.app:app --host 127.0.0.1 --port 8000
```
*Health verification:*
```powershell
curl.exe --noproxy "*" http://127.0.0.1:8000/api/health
# {"status":"healthy","service":"Intent Operating Layer","version":"0.5.0-mvp","capabilities_loaded":17}
```

2. **Start Next.js Frontend Server (Port 3000):**
```powershell
cd frontend
npm run dev -- -p 3000
```
*Web dashboard accessible at: `http://localhost:3000`*

---

## 2. Automated Test Verification (138 Tests)

Execute the full suite of automated unit, integration, security, and Playwright E2E tests:

```powershell
# 1. Run Task 011 generative UI verification suite
python -m pytest backend/tests/test_task011_generative_ui.py -v

# 2. Run full backend test suite (86 tests)
python -m pytest backend/tests -v

# 3. Run legacy outreach test suite (41 tests)
python -m pytest "c:\Workspace\Projects\Outreach Intelligence Engine\tests" -q

# 4. Run Playwright end-to-end browser tests (11 tests)
cd frontend
npx playwright test
```

**Total Automated Baseline:** 138 tests passing across backend, outreach adapter, and frontend.

---

## 3. Live Demonstration Probes (`scripts/run_task011_probes.py`)

Run the automated live probe runner to execute all four Task 011 demonstrations against the live system and generate full-fidelity screenshots:

```powershell
python scripts/run_task011_probes.py
```

### Demonstration Landmark Highlights

#### Demo 11A — Multi-Source Information Comparison Matrix
- **Intent:** `"Compare Vite and Webpack frontend build tool architectures and performance tradeoffs"`
- **Architecture:** Model-directed synthesis generating `comparison_matrix` with 5 empirical tradeoff dimensions:
  1. *Dev Server Cold Start:* Instant (~150ms) using native browser ESM vs slow (2-15s) full bundle compilation.
  2. *Hot Module Replacement (HMR):* Constant O(1) latency independent of codebase size vs linear O(N) degradation.
  3. *Build Pipeline Engine:* Rollup + ESBuild vs custom Webpack compilation pipeline with mature plugin ecosystem.
  4. *Legacy Browser Support:* `@vitejs/plugin-legacy` vs native Babel/core-js polyfills.
  5. *Configuration Complexity:* Zero-config sensible defaults vs verbose loaders and plugins.
- **Experience Origin:** `MODEL_GENERATED` with token usage and latency telemetry.
- **Screenshot Asset:** `docs/screenshots/v11_probe1_build_tools_comparison.png`

#### Demo 11B — Autonomous Browser Interaction Loop with Input, Select & Approval Boundary
- **Intent:** `"Fill official passport inquiry form with applicant details and submit application for review"`
- **Architecture:** `browser.interaction_loop` observes interactive DOM, handles `<input>`, `<textarea>`, `<select>` dropdown options, and checkbox toggling.
- **DOM State Verification:** Verifies attribute changes in DOM (`verified_in_dom=True`, `state_changed=True`).
- **Approval Safety Boundary:** Halts before consequential external submission, safely preserving draft in `form_draft`.
- **Experience Origin:** `MODEL_GENERATED` (`metric_strip` + `form_draft` + `action_panel`).
- **Screenshot Asset:** `docs/screenshots/v11_probe2_interactive_form_selection.png`

#### Demo 11C — Interactive Computation: Dijkstra Shortest Path Simulation (NOT Neural Net)
- **Intent:** `"Run Dijkstra algorithm shortest path simulation on directed weighted graph"`
- **Architecture:** Executes genuine mathematical Dijkstra graph capability (`educational.dijkstra_simulation`):
  - Topology: 5 vertices (A, B, C, D, E) and 6 directed weighted edges.
  - Step-by-step priority queue relaxation across 5 phases:
    - *Step 0 (INIT):* dist(A)=0, dist(others)=∞.
    - *Step 1 (RELAX A):* Relax (A,B)=4, (A,C)=2. Min unvisited = C.
    - *Step 2 (RELAX C):* Relax (C,B)=2+1=3 < 4 (shorter!). Relax (C,E)=10. Min unvisited = B.
    - *Step 3 (RELAX B):* Relax (B,D)=8. Relax (B,E)=3+4=7 < 10 (shorter!). Target E settled.
    - *Step 4 (COMPLETED):* Reconstructed optimal path `A -> C -> B -> E` with minimum cost `7.0`.
- **Canvas Rendering:** Dynamic 2D vector graph layout with node positions, dynamic weights, and interactive step controller.
- **Outcome Shape:** `OutcomeShape.SIMULATION` with step provenance.
- **Screenshot Asset:** `docs/screenshots/v11_probe3_dijkstra_graph_simulation.png`

#### Demo 11D — Everyday Service Discovery with Honest Portal Handoff
- **Intent:** `"Discover Air India scheduled flight destinations from Delhi to Mumbai with official portal handoff"`
- **Architecture:** Extracts truthful carrier destination specifications from public authority database (`https://en.wikipedia.org/wiki/Air_India_destinations`).
- **Truthful Outcome Guardrail:**
  - Reports verified route specifications without fabricating seat prices, availability, or fake bookings.
  - Binds an `action_panel` with `action_type: "EXTERNAL_PORTAL_HANDOFF"` to authenticated carrier portal `https://www.airindia.com`.
- **Screenshot Asset:** `docs/screenshots/v11_probe4_everyday_flight_handoff.png`

---

## 4. Architectural Invariants Verified
1. **Zero False Claims of `MODEL_GENERATED`:** When no external model credentials exist, plans cleanly output `RECIPE_ADAPTED` or `DETERMINISTIC_FALLBACK` with `model_metadata.status="MODEL_GENERATION_BLOCKED"`.
2. **Cross-Domain Knowledge Adaptation:** `ExperienceKnowledgeStore` abstracts structural signatures `(shape, interaction_need, domain_family)` and adapts them across disparate domains with privacy scrubbing.
3. **Resilient Browser Execution:** Selectors retry with fallback strategies, verify DOM state transitions, and enforce strict approval gating before mutations.
