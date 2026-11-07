# IOL v0.6 — Existing System Audit & Baseline Architecture Map

**Audit Date:** November 7, 2026  
**Baseline Version:** `v0.5.0-MVP` (Commit `f9b736a`)  
**Repository:** `https://github.com/harsh-bitverse/Intent-Operating-Layer.git`  
**Test Baseline Status:** **100% Passed** (54 Backend Pytest + 41 Outreach Pytest + 5 Playwright Chromium E2E)

---

## 1. Subsystem Architecture Map

### 1.1 FastAPI Routes & Endpoints (`backend/iol/api/routes.py`, `app.py`)
- `GET /api/health`: Service health, version string (`0.5.0-mvp`), capability count.
- `POST /api/tasks`: Authenticated task creation with intent string, budget, and metadata.
- `GET /api/tasks`: Scoped listing of tasks for the authenticated tenant/user.
- `GET /api/tasks/{task_id}`: Detailed retrieval of single task (returns status, steps, budget, UI state, results).
- `POST /api/tasks/{task_id}/cancel`: Halts execution immediately via budget tracker cancellation flag.
- `GET /api/tasks/{task_id}/events`: Monotonic SSE stream supporting reconnection and replay via `Last-Event-ID` header.
- `GET /api/capabilities`: Catalog of all 11 registered capability contracts.

### 1.2 Task & Event Models (`backend/iol/core/models.py`, `backend/iol/core/events.py`)
- **`Task`**: Durable entity holding `task_id`, `intent`, `status` (`PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`, `PAUSED_FOR_APPROVAL`), `user_id`, `budget`, `current_step`, `total_steps`, `result`, and `ui_state` (`DeclarativeUIRoot`).
- **`ExecutionBudget`**: Strict constraints: `max_duration_seconds` (default 300s), `max_steps` (20), `max_cost_usd` ($1.00), and `retry_limit` (2).
- **`TaskEvent`**: Append-only event ledger: `event_id` (monotonic integer primary key), `task_id`, `event_type`, `timestamp`, `data` payload.
- **`EventType`**: Lifecycle enum: `TASK_CREATED`, `TASK_STARTED`, `PLAN_GENERATED`, `STEP_STARTED`, `CAPABILITY_INVOKED`, `STEP_COMPLETED`, `STEP_FAILED`, `UI_UPDATED`, `TASK_COMPLETED`, `TASK_CANCELLED`, `TASK_FAILED`.

### 1.3 Adaptive Planner & Background Worker (`backend/iol/agent/planner.py`, `backend/iol/worker/background_worker.py`)
- **`AdaptiveCapabilityPlanner`**: Parses raw intent into typed `ResearchRequest` + `IntentConstraints`, checks for warm-start learned skill in `SkillRegistry`, and dynamically compiles a capability DAG.
- **`BackgroundWorker`**: Independent consumer loop using `asyncio.Queue`. Decoupled from browser tabs and HTTP request lifetimes. Executes steps, tracks timeouts, triggers retries, mutates `ui_state`, and appends events to the durable store.

### 1.4 Typed Capability Registry (`backend/iol/capabilities/registry.py`, `base.py`)
- 11 registered capability contracts with Pydantic input/output schemas:
  1. `research.live_source_acquisition`
  2. `research.generalized_extraction`
  3. `research.generalized_verification`
  4. `research.semantic_relevance`
  5. `data.deduplication`
  6. `research.entity_discovery`
  7. `research.structured_extraction`
  8. `research.verification`
  9. `content.constrained_personalization`
  10. `scheduling.destination_window`
  11. `security.human_approval_gateway`

### 1.5 Durable Store & Event Ledger (`backend/iol/core/store.py`)
- **`DurableTaskStore`**: Supports SQLite with Write-Ahead Logging (WAL) and PostgreSQL via SQLAlchemy.
- Atomic state updates, event appending, and monotonic integer ID tracking for SSE replay.

### 1.6 Skill Learning & Extraction (`backend/iol/skills/extractor.py`, `models.py`, `registry.py`)
- Extracts domain-agnostic capability sequences from successful execution histories.
- Parameter sanitization removes private names, emails, and phone numbers.
- Dual-memory store: Candidate Skills vs Trusted Reusable Skills.
- Warm-start compilation executes in `< 5ms`.

### 1.7 Declarative UI System (`frontend/src/components/DeclarativeUIRenderer.tsx`, `TaskView.tsx`)
- Server-driven declarative UI components:
  - `CardComponent`: Metric summary cards with `Execution Mode` (`LIVE`, `RECORDED REPLAY`, `FALLBACK REPLAY`).
  - `TimelineComponent`: Capability execution roadmap with step statuses and timestamps.
  - `TableComponent`: Candidate entities table with expandable field-level evidence trays.
  - `ComparisonComponent`: Multi-entity comparison matrix.
- Progressive updates sent via `UI_UPDATED` SSE events.

### 1.8 Security & Multi-Tenant Isolation (`backend/iol/api/auth.py`, `backend/iol/core/security.py`)
- Constant-time API key verification (`X-API-Key` strictly via HTTP headers).
- Multi-tenant data segregation: cross-tenant access returns 403 Forbidden.
- SSRF-protected HTTP client (`safe_http_get`) blocking private IP ranges and cloud metadata.
- Gated outbound communication (`dry_run=True` enforced; live email sending blocked without cryptographic operator ticket).

---

## 2. Reusability Matrix (What We Keep vs What We Extend)

| Subsystem | Baseline State | v0.6 Adoption Decision | Rationale |
| :--- | :--- | :--- | :--- |
| **FastAPI Core & Routes** | Clean REST API | **REUSE AS-IS** | Solid, fast, already handles auth, tasks, and SSE replay. |
| **Durable Store & SQLite WAL** | Robust event ledger | **REUSE AS-IS** | High integrity, zero test failures, supports Postgres migration. |
| **Background Worker** | Decoupled async worker | **REUSE AS-IS** | Perfectly isolated from browser sessions; executes tasks reliably. |
| **Capability Registry (11 Caps)** | Typed Pydantic contracts | **REUSE & EXTEND** | Core execution engine; add educational/computation capabilities if needed. |
| **Semantic Relevance Gate** | 36-case verified gate | **REUSE AS-IS** | Proven 100% precision/recall on domain constraints. |
| **Skill Learning Engine** | Sub-5ms warm planning | **REUSE AS-IS** | Handles execution-level reuse; experience reuse will complement it. |
| **Declarative UI Renderer** | Level 1 Table/Card/Timeline | **EXTEND INTO EXPERIENCE ENGINE** | Currently static component set. Needs model-directed planning, adaptive workspaces, and 2D interactive graphs. |
| **Task View & Frontend Layout** | Single 2-column view | **EXTEND** | Add full-screen adaptive task workspaces, placeholder skeletons, and 2D educational canvases. |

---

## 3. Backward Compatibility Invariants for v0.6

1. **Zero Execution Blockers:** The Experience Engine must run asynchronously; UI generation failure must never fail the underlying execution task.
2. **Existing SSE Protocol Preserved:** The `UI_UPDATED` event and `DeclarativeUIRoot` schema must remain valid fallbacks.
3. **Data Integrity:** UI components only bind verified data emitted by the execution engine; the generative UI layer cannot hallucinate or invent records.
4. **All 100 Baseline Tests Must Continue Passing:** Any changes to backend schemas or frontend routes must maintain green test suites.
