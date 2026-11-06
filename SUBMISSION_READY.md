# Intent Operating Layer (IOL) — Engineers' Conclave Submission Package

**Application Status:** **READY FOR FORMAL SUBMISSION & LIVE DEMONSTRATION**  
**Submission Deadline:** November 8, 2026, 5:00 PM IST  
**Release Tag:** `v0.5.0-mvp`  
**Git Repository:** [https://github.com/harsh-bitverse/Intent-Operating-Layer.git](https://github.com/harsh-bitverse/Intent-Operating-Layer.git)  
**Target Branch:** `main`

---

## 1. Executive Submission Index

This submission package contains all technical, empirical, and presentation assets required for the Engineers' Conclave jury review:

| Asset | File Link | Purpose & Content |
| :--- | :--- | :--- |
| **Application Brief** | [`EC_APPLICATION_BRIEF.md`](file:///c:/Workspace/Products/Intent%20Operating%20Layer/EC_APPLICATION_BRIEF.md) | Official Engineers' Conclave application document outlining problem, innovation, technical architecture, and impact. |
| **Founder Pitch & Demo Script** | [`FOUNDER_PITCH.md`](file:///c:/Workspace/Products/Intent%20Operating%20Layer/FOUNDER_PITCH.md) | 60-second elevator pitch, 3-minute live demonstration script, clear definitions of AI boundaries, and jury Q&A. |
| **Demo Runbook** | [`DEMO_RUNBOOK.md`](file:///c:/Workspace/Products/Intent%20Operating%20Layer/DEMO_RUNBOOK.md) | Complete step-by-step operator guide for launching the application locally, browser walkthrough, and offline replay mode. |
| **Empirical Evidence** | [`MVP_EVIDENCE.md`](file:///c:/Workspace/Products/Intent%20Operating%20Layer/MVP_EVIDENCE.md) | Scorecard with 100/100 automated test logs, Playwright browser traces, 36-case benchmark confusion matrix, and user journey log. |
| **Technical Architecture** | [`TECHNICAL_ARCHITECTURE.md`](file:///c:/Workspace/Products/Intent%20Operating%20Layer/TECHNICAL_ARCHITECTURE.md) | In-depth engineering specification, Mermaid architecture diagrams, 11-capability registry catalog, and security boundaries. |
| **Release Verification** | [`RELEASE_VERIFICATION.md`](file:///c:/Workspace/Products/Intent%20Operating%20Layer/RELEASE_VERIFICATION.md) | Release freeze audit, gap closure verification, limitations disclosure, and release readiness verdict. |
| **Semantic Relevance Report** | [`INTENT_SATISFACTION_REPORT.md`](file:///c:/Workspace/Products/Intent%20Operating%20Layer/INTENT_SATISFACTION_REPORT.md) | 36-case intent satisfaction benchmark report achieving 100% Precision, 100% Recall, and 0% False Positive Rate. |

---

## 2. Visual Demonstration Artifacts (Real Chromium Browser)

All screenshots were captured by Playwright in real headless Chromium against the live running Next.js frontend (`http://localhost:3000`) and FastAPI backend (`http://localhost:8000`):

1. **Declarative UI & Field-Level Evidence Inspector:**  
   [`docs/screenshots/dashboard_outcomes.png`](file:///c:/Workspace/Products/Intent%20Operating%20Layer/docs/screenshots/dashboard_outcomes.png)  
   *Visualizes live public API execution (`⚡ LIVE (GITHUB REPOSITORIES API)`), multi-metric cards, 5-step DAG timeline, candidate entities table, and expanded field-level evidence drawer showing exact provenance and conservative confidence scoring.*

2. **Durable SSE Event Stream & Recorded Replay:**  
   [`docs/screenshots/sse_event_stream.png`](file:///c:/Workspace/Products/Intent%20Operating%20Layer/docs/screenshots/sse_event_stream.png)  
   *Visualizes offline replay execution (`📼 RECORDED REPLAY`), sequential event ordering (`#3230` to `#3242`), JSON payloads, and timestamps.*

3. **In-Browser Multi-Tenant Security Isolation:**  
   [`docs/screenshots/tenant_isolation_403.png`](file:///c:/Workspace/Products/Intent%20Operating%20Layer/docs/screenshots/tenant_isolation_403.png)  
   *Visualizes the in-browser security card displayed when Tenant Beta attempts to access Tenant Alpha's research task via direct URL deep-linking (`/?task_id=...`).*

---

## 3. How to Launch and Inspect Locally

### Option A: One-Command Startup
**Windows PowerShell:**
```powershell
.\scripts\run_local.ps1
```
**Linux / macOS:**
```bash
bash scripts/run_local.sh
```

### Option B: Docker Compose
```bash
docker-compose up --build
```
- Web Application: `http://localhost:3000`
- API Backend & Swagger Docs: `http://localhost:8000/docs`

### Option C: Run Full Automated Verification (100 Tests)
```bash
# 1. Backend IOL Pytest (54 tests)
python -m pytest backend/tests

# 2. Outreach Engine Pytest (41 tests)
cd "..\Outreach Intelligence Engine"
python -m pytest tests
cd "..\Intent Operating Layer"

# 3. Playwright Real-Browser Chromium Suite (5 tests)
cd frontend
npx playwright test
```

### Option D: Run Conclave Demonstration Scenarios
```bash
# Recorded Replay Mode (Guaranteed sub-2s offline demonstration)
python scripts/run_demo.py --demo ALL --mode replay

# Live Network Mode (Direct live queries to OpenAlex, GitHub, and web)
python scripts/run_demo.py --demo ALL --mode live
```

---

## 4. Security & Compliance Checklist

- [x] **No Credentials Committed:** Repository contains zero API keys, passwords, or personal datasets (`.gitignore` enforced).
- [x] **Header-Based Authentication:** All API requests pass `X-API-Key` strictly via HTTP headers; query string auth is rejected.
- [x] **Multi-Tenant Isolation:** Database store enforces tenant ownership checks on all task reads, writes, and event streams.
- [x] **Outbound Communication Gated:** Legacy outreach adapter strictly enforces `dry_run=True`; automated email dispatch is blocked without human operator cryptographic tickets.
- [x] **SSRF Protection:** Web retrieval capabilities validate URLs against local network and private IP ranges before initiating connections.

---
*The IOL team certifies that the Intent Operating Layer MVP v0.5.0 is complete, audited, and ready for evaluation.*
