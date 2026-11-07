# Intent Operating Layer (IOL) v0.6

> **The Visual-First Intent-to-Outcome Execution Platform with Reusable Capability Learning**
>
> **Release:** `v0.6.0` | **Status:** Shipped & Verified | **Automated Tests:** 109 / 109 Passing (100%)

---

## 1. Product Philosophy & Core Principles

**Intent Operating Layer (IOL)** is engineered around two fundamental operational rules:

1. **Primary:** Complete the user's requested work with verifiable rigor, factual grounding, and execution safety.
2. **Secondary:** Learn and register reusable capabilities from execution—both **how to execute work** (`SkillLearningEngine`) and **how to present work** (`ExperienceRecipeStore`)—so similar and related tasks can be completed faster, more reliably, and more intuitively for future users.

---

## 2. Two Cooperating Engines (IOL v0.6)

IOL v0.6 operates through two decoupled, asynchronous engines:

1. **The Execution Engine:** Understands intent, dynamically synthesizes multi-step capability pipelines, queries live public APIs (OpenAlex, GitHub, web) with SSRF guards, extracts schemas, computes cryptographic SHA-256 provenance hashes, filters candidates via semantic relevance gates, and persists results to durable storage.
2. **The Experience Engine:** An asynchronous, non-blocking presentation subsystem that plans adaptive visual workspaces in $<5\text{ms}$, initializes skeleton layouts, dynamically binds verified records via Server-Sent Events (`EXPERIENCE_UPDATED`), and renders rich interactive graphical interfaces—including sortable/filterable multi-column data grids and interactive 2D node-edge simulation canvases.

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

## 5. Running Automated Tests (109 Tests Total)

### 5.1 Run Full IOL Backend Test Suite (60 Passing Tests)
Covers store CRUD, multi-tenant auth & ownership, SSRF guards, semantic relevance gates, skill learning, live cross-domain transfer, evidence integrity, experience recipe matching, and neural network simulations:
```powershell
$env:PYTHONPATH="C:\Workspace\Products\Intent Operating Layer"
python -m pytest backend/tests -v
```

### 5.2 Run Experience Engine Tests
```powershell
$env:PYTHONPATH="C:\Workspace\Products\Intent Operating Layer"
python -m pytest backend/tests/test_experience_engine.py -v
```

### 5.3 Run Real-Browser Playwright Chromium Tests (8 Passing Tests)
Runs both the Core Launch Suite and the v0.6 Experience Engine Suite (Demos A & B) in headless Chromium:
```powershell
cd "C:\Workspace\Products\Intent Operating Layer\frontend"
npx playwright test
```

### 5.4 Run Existing Outreach Intelligence Engine Tests (41 Tests)
Ensures zero degradation or regressions in the existing Outreach Intelligence Engine codebase:
```powershell
cd "C:\Workspace\Projects\Outreach Intelligence Engine"
python -m pytest -v
```

---

## 6. Key Deliverables & Artifact Index

### IOL v0.6 Milestone Artifacts:
- **`V06_IMPLEMENTATION_REPORT.md`**: Technical report on IOL v0.6 implementation, architecture, test scorecards, and verification.
- **`V06_DEMO_RUNBOOK.md`**: Step-by-step presentation runbook for Conclave evaluators covering Demos A & B.
- **`V06_EXPERIENCE_ENGINE_SPEC.md`**: Formal specification of ExperiencePlan, component catalog, and streaming data binding.
- **`V06_ARCHITECTURE_DECISIONS.md`**: Architecture Decision Records (ADR-001 through ADR-007) with explicit rationale.
- **`V06_REFERENCE_REPOSITORY_STUDY.md`**: Comparative analysis of open-source frameworks (json-render, ag-ui, a2ui, OpenIntelligentUI, xyflow).
- **`IOL_DIFFERENTIATION_MATRIX.md`**: Competitive landscape analysis against CopilotKit, A2UI, JSON-Render, and Browser-Use.
- **`V06_EXISTING_SYSTEM_AUDIT.md`**: Source-level audit of v0.5 codebase, boundary invariants, and reusability analysis.

### Foundational Milestones & Evidence:
- **`SUBMISSION_READY.md`**: Official Engineers' Conclave submission package index, live verification scorecard, and demonstration setup.
- **`FOUNDER_PITCH.md`**: 60-second elevator pitch, 3-minute interactive demonstration script, system boundary definitions, and jury Q&A.
- **`RELEASE_VERIFICATION.md`**: Complete release verification audit, test pass records, and release readiness verdict.
- **`EC_APPLICATION_BRIEF.md`**: Formal Engineers' Conclave application document detailing problem statement, technical innovation, and impact.
- **`MVP_EVIDENCE.md`**: Empirical evidence report with automated test execution traces, Playwright logs, and benchmark confusion matrix.
- **`TECHNICAL_ARCHITECTURE.md`**: Technical architecture specification, Mermaid diagrams, and capability catalog.
- **`docs/screenshots/`**: Visual evidence gallery captured in real Chromium via Playwright:
  - `v06_demo_a_research_workspace.png`: Adaptive research workspace with full-screen grid and field-level evidence drawer.
  - `v06_demo_b_neural_simulation.png`: Interactive 2D neural network learning simulation canvas.
  - `dashboard_outcomes.png`: Multi-tenant authenticated dashboard.
  - `tenant_isolation_403.png`: Cross-tenant security barrier.
