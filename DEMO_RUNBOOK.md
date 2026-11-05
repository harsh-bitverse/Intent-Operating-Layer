# IOL — Engineers' Conclave Demonstration Runbook (Task 005)

**Platform:** Intent Operating Layer (IOL)  
**Governing Product Principles:**  
- **Primary:** Execute the user's requested work and deliver usable, verified outcomes.  
- **Secondary:** Learn generalizable capabilities from execution so related future tasks become faster and more reliable across users without leaking private information.  
**Demonstration Scope:** Live & Replay Demonstrations across Academic Faculty Research, Indian AI Startups, AI Developer Tools, Dynamic Capability Composition, Multi-Tenant Isolation, and Warm-Start Skill Reuse.

---

## 1. Fast Start: One-Command Startup

For instant demonstration setup on any workstation:

### Windows (PowerShell)
```powershell
./scripts/run_local.ps1
```
*Options:*
- `./scripts/run_local.ps1 -Mode replay` (ensures 100% resilient offline demos)
- `./scripts/run_local.ps1 -Port 8000 -FrontendPort 3000`

### Linux / macOS (Bash)
```bash
chmod +x scripts/run_local.sh
./scripts/run_local.sh
```

### Manual Service Startup
If running services in separate terminals:

**Terminal 1 — Backend API & Background Worker:**
```bash
python -m uvicorn backend.iol.api.app:app --host 127.0.0.1 --port 8000 --reload
```
- Health endpoint: `http://127.0.0.1:8000/api/health`
- Interactive OpenAPI Docs: `http://127.0.0.1:8000/docs`

**Terminal 2 — Next.js Standalone Frontend:**
```bash
cd frontend
npm run dev -- -p 3000
```
- Browser Web Application: [http://localhost:3000](http://localhost:3000)

---

## 2. Automated Real Browser & E2E Verification Suites

Before presenting to an audience or evaluation panel, verify complete system integrity:

### 1. Real Headless Chromium Browser Verification (Playwright)
```bash
cd frontend
npx playwright test
```
*Verified Browser Tests (100% Passing):*
- `Test A`: Complete research journey from intent submission, SSE event streaming, UI outcome table rendering, and CSV/JSON export.
- `Test B`: Reconnection and durable event replay across page reloads (verifies `Last-Event-ID` tracking).
- `Test C`: Immediate task cancellation halting background worker and preserving terminal state.
- `Test D`: Multi-tenant ownership boundary isolation preventing cross-tenant access.
- `Test E`: Graceful failure handling and partial results preservation.

### 2. Full Backend Test Suite
```bash
python -m pytest backend/tests -v
```
*(54/54 automated tests passing)*

### 3. Integrated Outreach Engine Compatibility
```bash
python -m pytest "C:\Workspace\Projects\Outreach Intelligence Engine\tests"
```
*(41/41 automated tests passing)*

---

## 3. Live Demonstrator Script: The 3 Core Demonstrations

Run all three demonstrations via CLI or trigger them directly from the web browser preset buttons at [http://localhost:3000](http://localhost:3000).

```bash
# Recommended for presentations (immune to external API rate limits):
python scripts/run_demo.py --demo ALL --mode replay

# For live external network queries:
python scripts/run_demo.py --demo ALL --mode live
```

---

### Demonstration A: Autonomous Academic Faculty Research
*Audience Focus:* Demonstrates live source acquisition, field extraction, conservative evidence integrity, and semantic relevance gating.

- **Natural Language Intent:**
  > *"Find 10 professors researching autonomous systems and embodied AI, with institution, research interests, official profile URL, and evidence."*
- **Execution Command:**
  ```bash
  python scripts/run_demo.py --demo A --mode replay
  ```
- **What to Highlight to Audience:**
  1. **Dynamic Composition:** The planner generates a 5-step pipeline (`acquisition` -> `extraction` -> `verification` -> `relevance` -> `deduplication`). Outreach drafting and destination scheduling are **omitted** because the user requested pure research.
  2. **Field-Level Evidence:** Click any row in the web UI or inspect the CLI output. Every field has explicit provenance: URL, retrieval timestamp, extraction method, and verification status.
  3. **No 1.00 Certainty Hallucination:** Confidence scores are capped conservatively at 0.88 maximum.
  4. **Semantic Gate:** The system evaluates whether candidate researchers have verified faculty chairs or appointments, rejecting unverified graduate students or general bloggers.

---

### Demonstration B: Indian AI Infrastructure Commercial Discovery
*Audience Focus:* Demonstrates cross-domain generalization without hardcoded domain workflows.

- **Natural Language Intent:**
  > *"Find 10 startups working on AI infrastructure in India, with company name, product focus, official website, location, and supporting evidence."*
- **Execution Command:**
  ```bash
  python scripts/run_demo.py --demo B --mode replay
  ```
- **What to Highlight to Audience:**
  1. **Zero Hardcoding:** The system executes the **exact same capability IDs** (`research.live_source_acquisition`, `research.generalized_extraction`, `research.generalized_verification`, `research.semantic_relevance`, `data.deduplication`) as Demo A, but automatically extracts company-specific columns (`company_name`, `product_focus`, `official_website`, `location`).
  2. **Geographic & Temporal Constraints:** The semantic relevance gate validates that startups are genuinely headquartered in India (e.g. Bengaluru, Chennai) and founded 2021 or later.
  3. **Reachable URLs:** Validates that URLs have active HTTP/HTTPS protocols and rejects parked or spam domains.

---

### Demonstration C: Open-Source AI Developer Frameworks & Warm Skill Reuse
*Audience Focus:* Demonstrates third-domain transfer, comparative matrix generation, and warm-start capability compilation.

- **Natural Language Intent:**
  > *"Find 5 open-source AI evaluation and developer frameworks with repository name, primary language, license, official repository URL, and evidence."*
- **Execution Command:**
  ```bash
  python scripts/run_demo.py --demo C --mode replay
  ```
- **What to Highlight to Audience:**
  1. **SPDX License Verification:** Verifies Apache-2.0, MIT, and permissive open-source licenses directly from repository metadata.
  2. **Comparative Analysis Matrix:** In addition to the candidate table, IOL autonomously renders a comparative multi-entity matrix comparing vLLM, DSPy, LangChain, LlamaIndex, and DeepEval across primary language, stars, and licensing.
  3. **Warm-Start Compilation:** The execution plan is dynamically matched against learned execution traces, compiling the plan in under **15 milliseconds** instead of cold replanning.

---

## 4. Web UI Walkthrough (Engineers' Conclave Interactive Flow)

1. Open [http://localhost:3000](http://localhost:3000) in Chrome or Edge.
2. **Session & Tenant Switcher:** In the top header bar, inspect the authenticated session switcher:
   - Select `Demo Operator (Global Admin)` -> Full cross-tenant oversight.
   - Switch to `Tenant Alpha (Enterprise)` -> Observe that only Tenant Alpha's tasks are visible.
   - Switch to `Tenant Beta (Startup)` -> Observe strict tenant data isolation (403 Forbidden on cross-tenant access).
3. **Intent Submission:**
   - Click one of the Conclave preset buttons: **"🎓 Academic Faculty"**, **"🚀 Indian AI Startups"**, or **"🛠️ Open-Source AI Tools"**.
   - Watch the universal intent bar populate.
   - Click **Execute Intent**.
4. **Real-Time Streaming:**
   - Observe the live SSE timeline updating step-by-step: `step_acquisition` -> `step_extraction` -> `step_verification` -> `step_relevance` -> `step_dedup`.
   - Indeterminate pulse animation displays for active running states.
5. **Live Reconnection Simulation:**
   - While a task is running (or after completion), press **Ctrl+R / F5** to reload the page.
   - Notice that the full event history and UI state immediately replay without loss of state.
6. **Results & Evidence Inspection:**
   - Click on any candidate entity in the results table to open the slide-out Evidence Drawer.
   - Inspect the cryptographic content hash, retrieval timestamp, and field-level evidence excerpts.
7. **Export Outcomes:**
   - Click **Export JSON** or **Export CSV** in the table action bar to download the verified outcome dataset.

---

## 5. Failover & Replay Mode Policy

During live demonstrations, public third-party APIs (OpenAlex, GitHub, arXiv) may experience rate limits (e.g. HTTP 429 Too Many Requests) or network latency.

- **Offline / Presentation Resilience:** By setting `IOL_DEMO_REPLAY=1` or selecting `--mode replay`, IOL loads cryptographically hashed local replay fixtures stored in `backend/data/fixtures/`:
  - `academic_faculty_fixture.json` (10 verified professors)
  - `indian_ai_startups_fixture.json` (10 verified Indian startups)
  - `ai_developer_tools_fixture.json` (10 verified open-source frameworks)
- **Transparent Logging:** When replay fixtures are loaded, IOL logs `"live_network_fallback": True` and `"provider": "recorded_replay_fixture"` in event metadata, ensuring 100% auditability without fabricating live claims.
