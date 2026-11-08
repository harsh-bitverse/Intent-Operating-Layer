# TASK 008 — Architecture Decision Records (ADR-008 to ADR-015)

**Status:** Approved & Frozen for Implementation  
**Date:** November 8, 2026  
**Context:** IOL v0.6+ General-Purpose Browser Execution × Generative Experience Substrate

---

### ADR-008: Sandboxed Headless Browser Execution via Python Playwright
- **Decision:** Adopt official Python `playwright` (`async_api` and sync wrappers) running headless Chromium inside the task worker environment.
- **Isolation:** Each browser session is strictly isolated per `(tenant_id, task_id)` in an ephemeral `BrowserContext` with dedicated cookie jar and storage.
- **Lifecycle:** Budgets enforce maximum 3 concurrent browser instances, 30s per-step timeout, 10 maximum navigation steps per task, and automatic teardown upon task termination or cancellation.
- **Alternative Rejected:** External browser container zoo / microservices (adds unnecessary latency and network complexity).

---

### ADR-009: Composability via Universal Tool Grammar
- **Decision:** The capability planner composes tasks using universal operational semantics: `observe`, `navigate`, `extract`, `interact`, `compute`, `transform`, `compare`, `handoff`, `verify`.
- **Contract:** All tools, whether browser-based, HTTP APIs, or mathematical routines, consume and produce typed Pydantic payloads with field-level evidence.
- **Alternative Rejected:** Bespoke domain agents (`flight_agent`, `movie_agent`, `govt_agent`).

---

### ADR-010: Bounded Plan Semantics with Explicit Partial & Blocked States
- **Decision:** Execution plans are bounded DAGs or ordered step sequences. Every tool execution is recorded in the durable event store.
- **Graceful Failure:** If a target website blocks (CAPTCHA, 403, Cloudflare challenge) or credentials are missing, the task transitions to `PARTIAL` or `BLOCKED` with an explicit blocker message and captured evidence, rather than crashing or synthesizing fake data.
- **Alternative Rejected:** Hard failure on missing external tools or synthesizing unverified mock data.

---

### ADR-011: Strict Declarative UI Schema with Trusted Component Catalog
- **Decision:** The Experience Engine renders only declarative JSON describing components from a trusted catalog (`WorkspaceDataGrid`, `ComparisonView`, `InteractiveCanvas2D`, `FormDraftView`, `TimelineView`, `EvidenceDrawer`, `ActionPanel`).
- **Safety:** Zero arbitrary JavaScript, zero `dangerouslySetInnerHTML`, zero unsanitized URL fetches from the frontend.
- **Alternative Rejected:** Model-generated raw JSX or unvalidated HTML rendering.

---

### ADR-012: Provider-Neutral Experience Planner with Deterministic Fallback
- **Decision:** Experience planning accepts user intent, expected data shape, and component catalog. When a model provider (OpenAI, Gemini, Anthropic) is configured in environment, it requests a declarative layout schema with a one-turn repair policy on schema errors. If unconfigured or failed, it falls back to recipe adaptation and deterministic layout compilation `<5ms`.
- **Invariance:** Experience planning runs on an independent budget and can NEVER block, delay, or crash the Execution Engine.
- **Alternative Rejected:** Hard dependency on LLM availability for basic UI rendering.

---

### ADR-013: Domain-Neutral OutcomeEnvelope & Monotonic SSE Streaming
- **Decision:** Data is decoupled from UI via `OutcomeEnvelopeV1` possessing explicit `shape` (`collection`, `comparison`, `document`, `form`, `timeline`, `graph`, `simulation`, `single_answer`, `partial`, `blocked`), `field_schema`, `items`, `evidence`, `source_mode`, and `blockers`.
- **Streaming:** Updates stream through durable SSE with monotonically increasing revisions (`revision: 1, 2, 3...`), enabling seamless reconnects and client-side data binding with zero LLM calls per row.
- **Alternative Rejected:** Coupling raw database records directly to specific UI components.

---

### ADR-014: Backend-Enforced Scoped Approvals for Consequential Actions
- **Decision:** All UI-triggered actions route through `POST /api/tasks/{task_id}/actions`. Actions classified as `EXTERNAL_WRITE`, `PAYMENT_OR_ORDER`, or `DESTRUCTIVE` are paused by the backend policy gate, generating a cryptographic approval fingerprint with a 15-minute expiry.
- **Execution:** Execution only proceeds when a verified human operator posts to `POST /api/tasks/{task_id}/actions/approve` with the valid fingerprint.
- **Alternative Rejected:** Frontend directly invoking side-effect APIs or bypassable client-side confirmation modals.

---

### ADR-015: Structural Recipe Signatures & Privacy-Preserving Knowledge Transfer
- **Decision:** Learned experience recipes are keyed by structural data signatures (e.g., entity schema, interaction demands, output shape) rather than user-specific keywords.
- **Tenant Privacy:** All tenant identifiers, personal names, private credentials, and entity values are scrubbed before an experience recipe is cataloged in the shared recipe store.
- **Alternative Rejected:** Storing unscrubbed raw task outputs as global UI templates.
