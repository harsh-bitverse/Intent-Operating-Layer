# Intent Operating Layer (IOL)

> **A General-Purpose Intent-to-Outcome Execution Platform with Reusable Capability Learning**

---

## 1. Product Philosophy & Core Principles

**Intent Operating Layer (IOL)** is engineered around two fundamental operational rules:

1. **Primary:** Complete the user's requested work with verifiable rigor, factual grounding, and execution safety.
2. **Secondary:** Learn and register reusable capabilities from execution so similar and related tasks can be completed faster, more reliably, and more efficiently for future users.

---

## 2. Architecture Overview

IOL is built with a strictly modular, decoupled architecture:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                   Next.js 14 / TypeScript Frontend                     │
│  - Intent Input Bar with Domain Autocompletion                         │
│  - Persistent Task Queue & Status Monitor                              │
│  - SSE Event Stream Hook with Last-Event-ID Reconnect & Replay         │
│  - Declarative UI Renderer: Tables, Metric Cards, Timelines            │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / SSE (/api)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     FastAPI Application Server                         │
│  - REST Endpoints: /api/tasks, /api/capabilities, /api/health         │
│  - Replayable SSE Stream: /api/tasks/{task_id}/events                  │
└──────────────────┬─────────────────────────────────┬───────────────────┘
                   │                                 │
                   ▼                                 ▼
┌──────────────────────────────────────┐  ┌──────────────────────────────┐
│       Durable Store (Postgres/SQLite) │  │  Background Worker Loop      │
│  - Tasks, States, Budgets, Results   │  │  - Independent of Browser    │
│  - Append-Only Sequential Events     │  │  - Budget Enforcement        │
│  - Reconnection via Event IDs        │  │  - Retries & Cancellation    │
└──────────────────────────────────────┘  └──────────────┬───────────────┘
                                                         │
                                                         ▼
                                          ┌──────────────────────────────┐
                                          │  Agent Adapter & Orchestrator│
                                          │  - Provider-Independent      │
                                          │  - Multi-Step Dynamic Plan   │
                                          └──────────────┬───────────────┘
                                                         │
                                                         ▼
                                          ┌──────────────────────────────┐
                                          │  IOL Capability Registry     │
                                          │  - Typed Inputs/Outputs      │
                                          │  - Verification Metadata     │
                                          │  - Permissions & Budgets     │
                                          └──────────────┬───────────────┘
                                                         │
                                                         ▼
                                          ┌──────────────────────────────┐
                                          │  Outreach Engine Adapter     │
                                          │  - research.entity_discovery │
                                          │  - research.extraction       │
                                          │  - research.verification     │
                                          │  - data.deduplication        │
                                          │  - content.personalization   │
                                          │  - scheduling.window         │
                                          │  - security.approval_gateway │
                                          └──────────────────────────────┘
```

---

## 3. Reusable Capability Registry

IOL abstracts domain-specific tasks into universal capability contracts. The same capability IDs execute across academic research and enterprise venture research:

| Capability ID | Name | Typed Input Schema | Typed Output Schema | Verification & Safety |
| :--- | :--- | :--- | :--- | :--- |
| `research.live_source_acquisition` | Live External Source Acquisition | `SourceAcquisitionInput` | `SourceAcquisitionOutput` | Live OpenAlex & web/GitHub search with cryptographic SHA-256 provenance hashes. |
| `research.generalized_extraction` | Generalized Schema Extraction | `GeneralizedExtractionInput` | `GeneralizedExtractionOutput` | Dynamically maps arbitrary requested fields without hallucinating missing data. |
| `research.generalized_verification`| Evidence & Field Quality Gate | `GeneralizedVerificationInput`| `GeneralizedVerificationOutput`| Multi-tier confidence scoring, validates URL formats and presence of evidence quotes. |
| `research.semantic_relevance` | Semantic Relevance & Intent Gate | `SemanticRelevanceInput` | `SemanticRelevanceOutput` | Evaluates candidates against inclusion rules; rejects recruitment repos, CVs, and student homework. |
| `data.deduplication` | Entity Deduplication & Resolution | `DeduplicationInput` | `DeduplicatedOutput` | Deterministic SHA-256 composite hashing on dynamic identity keys. |
| `content.constrained_personalization`| Constrained Grounded Personalization | `PersonalizationInput` | `PersonalizationOutput` | 130–180 words, grounded strictly in substantiated user context (omitted in pure research). |
| `scheduling.destination_window` | Destination-Local Window Scheduler | `SchedulingInput` | `SchedulingOutput` | IANA zoneinfo, DST, operator IST mapping (omitted in pure research). |
| `security.human_approval_gateway` | Human-in-the-Loop Approval Gate | `ApprovalGatewayInput` | `ApprovalGatewayOutput` | **Live email sending permanently blocked** without explicit human operator session. |

---

## 4. Exact Setup, Run Commands & Production Deployment

### Prerequisites
- Python 3.12+ (tested with Python 3.12.10 on Windows)
- Node.js 18+ (tested with Node v26.3.0 and npm 12.0.1)
- Docker & Docker Compose (optional, for containerized deployment)

### 4.1 Local Backend Execution

1. **Navigate to the IOL root directory:**
   ```powershell
   cd "C:\Workspace\Products\Intent Operating Layer"
   ```

2. **Install Python dependencies:**
   ```powershell
   python -m pip install fastapi uvicorn pydantic pydantic-settings sqlalchemy aiosqlite psycopg-binary pytest pytest-asyncio httpx requests tzdata beautifulsoup4
   ```

3. **Start the FastAPI Backend Server:**
   ```powershell
   $env:PYTHONPATH="C:\Workspace\Products\Intent Operating Layer"
   python -m uvicorn backend.iol.api.app:app --host 127.0.0.1 --port 8000 --reload
   ```
   *The API will be available at:* `http://127.0.0.1:8000`  
   *Interactive Swagger docs:* `http://127.0.0.1:8000/docs`  
   *Container Liveness Probe:* `http://127.0.0.1:8000/healthz`

### 4.2 Local Frontend Execution

1. **Navigate to the frontend directory:**
   ```powershell
   cd "C:\Workspace\Products\Intent Operating Layer\frontend"
   ```

2. **Install frontend dependencies:**
   ```powershell
   npm install
   ```

3. **Build & Start Frontend:**
   ```powershell
   npm run build
   npm start
   ```
   *Open browser at:* **`http://localhost:3000`**

### 4.3 Containerized Production Deployment (Docker Compose)

Deploy the entire IOL stack (PostgreSQL 16, FastAPI Backend, Next.js Frontend) with one command:
```powershell
docker compose up -d --build
```
- **PostgreSQL 16:** `localhost:5432`
- **FastAPI Core & Background Worker:** `http://localhost:8000`
- **Next.js Web Dashboard:** `http://localhost:3000`

---

## 5. Running Automated Tests

### 5.1 Run Full IOL Test Suite (54 Passing Tests)
Covers store CRUD, multi-tenant auth & ownership, SSRF guards, semantic relevance gates, skill learning, live cross-domain transfer, evidence integrity, and declarative UI matrix generation:
```powershell
$env:PYTHONPATH="C:\Workspace\Products\Intent Operating Layer"
python -m pytest backend/tests -v
```

### 5.2 Run Phase A: Semantic Relevance & Intent Satisfaction Benchmark
```powershell
$env:PYTHONPATH="C:\Workspace\Products\Intent Operating Layer"
python -m pytest backend/tests/test_semantic_relevance.py -v
```

### 5.3 Run Phase B: Authentication, Authorization & Hardened SSRF Tests
```powershell
$env:PYTHONPATH="C:\Workspace\Products\Intent Operating Layer"
python -m pytest backend/tests/test_auth_and_ownership.py -v
```

### 5.4 Run Phase C: Demonstrable Skill Learning & Warm-Start Benchmark
```powershell
$env:PYTHONPATH="C:\Workspace\Products\Intent Operating Layer"
python -m pytest backend/tests/test_skill_learning.py -v
```

### 5.5 Run Phase D: Autonomous 10-Step End-to-End User Journey Verification
```powershell
$env:PYTHONPATH="C:\Workspace\Products\Intent Operating Layer"
python scripts/verify_e2e_journey.py
```

### 5.6 Run Existing Outreach Intelligence Engine Tests (41 Tests)
Ensures zero degradation or regressions in the existing Outreach Intelligence Engine codebase:
```powershell
cd "C:\Workspace\Projects\Outreach Intelligence Engine"
python -m pytest -v
```

---

## 6. Key Deliverables & Artifact Index

- **`SUBMISSION_READY.md`**: Official Engineers' Conclave submission package index, live verification scorecard, and demonstration setup.
- **`FOUNDER_PITCH.md`**: 60-second elevator pitch, 3-minute interactive demonstration script, system boundary definitions, and jury Q&A.
- **`RELEASE_VERIFICATION.md`**: Complete release verification audit, 100/100 test pass records, gap closure audit, and release readiness verdict.
- **`EC_APPLICATION_BRIEF.md`**: Formal Engineers' Conclave application document detailing problem statement, technical innovation, and impact.
- **`MVP_EVIDENCE.md`**: Empirical evidence report with automated test execution traces, Playwright logs, and 36-case benchmark confusion matrix.
- **`TECHNICAL_ARCHITECTURE.md`**: In-depth technical architecture specification, Mermaid diagrams, and 11-capability catalog.
- **`INTENT_SATISFACTION_REPORT.md`**: Phase A report evaluating 36 held-out entities across domains, demonstrating 100% precision and 100% recall, eliminating recruiting/CV false positives, and analyzing the 4-tier verification states.
- **`SKILL_LEARNING_EXPERIMENT.md`**: Phase C report demonstrating execution trace analysis, parameter sanitization, the 3-stage validation state machine (`CANDIDATE` -> `VALIDATED_FOR_TASK_FAMILY` -> `TRUSTED_FOR_BOUNDED_REUSE`), and warm-start speedups.
- **`DEMO_RUNBOOK.md`**: Complete runbook providing exact step-by-step reproduction instructions for all 3 demo scenarios and automated user journeys.
- **`EVIDENCE_INTEGRITY_REPORT.md`**: Workstream A audit distinguishing directly supported vs. derived vs. inferred vs. unknown evidence tiers, and conservative confidence calibration.
- **`THIRD_DOMAIN_TRANSFER_REPORT.md`**: Transfer report to open-source AI developer frameworks and evaluation tools, SPDX license verification, and declarative comparison matrix generation.
- **`docs/screenshots/`**: Visual evidence gallery captured in real headless Chromium via Playwright (`dashboard_outcomes.png`, `sse_event_stream.png`, `tenant_isolation_403.png`).
