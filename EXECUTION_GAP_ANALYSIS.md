# IOL Execution Gap Analysis: From Static Pipelines to Dynamic Live Research

**Date:** November 2026  
**Repository:** `harsh-bitverse/Intent-Operating-Layer` (`c:\Workspace\Products\Intent Operating Layer`)  
**Scope:** Architecture baseline audit following Implementation Task 001.

---

## 1. Executive Ground Truth Assessment

Implementation Task 001 successfully established the execution foundation for IOL: a FastAPI server, durable SQLite WAL/PostgreSQL store with sequential event replay, an asynchronous background worker, declarative UI schemas, a typed capability registry, and an initial Outreach adapter with 20 passing unit/integration tests.

However, a thorough audit of the actual code reveals significant architectural gaps between the current implementation and a true general-purpose, adaptive execution engine:

1. **Static Pipeline Sequencing vs. Dynamic Planning:**
   The current `IntentOrchestrator` does not dynamically reason about or compose capabilities based on the user's intent. Instead, it uses a trivial binary keyword check (`"startup" in intent` vs. default `"faculty"`) and always outputs a fixed, hardcoded 7-step pipeline:
   $$\text{Discovery} \longrightarrow \text{Extraction} \longrightarrow \text{Verification} \longrightarrow \text{Deduplication} \longrightarrow \text{Personalization} \longrightarrow \text{Scheduling} \longrightarrow \text{Approval}$$
   If a user asks only to "Find 10 professors and extract their official profile URLs", the engine still unnecessarily generates email outreach drafts, schedules morning delivery windows, and triggers an email approval gate.

2. **Fixtures and Local Datasets vs. Fresh Live Information:**
   The `research.entity_discovery` capability in `backend/iol/adapters/outreach/adapter.py` does not query the internet or live directories. It filters a static in-memory dictionary `SAMPLE_ENTITIES` containing 5 hardcoded professors and 4 hardcoded startups. The live execution demonstrated in Task 001 operated entirely against this local dictionary. **Zero fresh external information was discovered over the wire.**

3. **Synthetic Field Generation vs. Evidence Extraction:**
   The `research.structured_extraction` capability currently fabricates email addresses using string heuristics (e.g. appending `@mit.edu` or `@stanford.edu` based on organization name) rather than extracting genuine contact details and citations from real source pages.

4. **Domain Coupling in Capabilities:**
   Several capabilities contain hardcoded assumptions tailored exclusively to Harshith N's Summer 2027 internship search at IIT Delhi.

---

## 2. Component-by-Component Ground Truth Breakdown

### 2.1 Planner (`backend/iol/agent/orchestrator.py`)
- **Actual Implementation:** Statically maps any intent to the same 7 sequential steps.
- **Limitation:** Cannot prune unneeded steps. Cannot compose a 3-step research pipeline or a 2-step verification pipeline.
- **Contract Adherence:** Does not inspect the capability input/output contracts to dynamically bind step dependencies.

### 2.2 Capability Registry (`backend/iol/capabilities/registry.py`)
- **Status:** **Genuinely sound.** Provides typed Pydantic input/output schemas, metadata contracts, and execution wrappers.
- **Limitation:** Needs a live search/retrieval capability and more granular domain-neutral contracts.

### 2.3 Task Worker (`backend/iol/worker/background_worker.py`)
- **Actual Implementation:** Asynchronous queue consumer running decoupled from browser connections. Budget tracking (`BudgetTracker`) and cancellation checking work as intended.
- **Limitation:** The Declarative UI enrichment method (`_enrich_ui`) contains rigid `if cap_id == ...` branches tied specifically to the 7 initial capabilities. If new capabilities are introduced or unneeded capabilities omitted, the UI generator lacks adaptive rendering.

### 2.4 Outreach Adapter (`backend/iol/adapters/outreach/adapter.py`)
- **Domain-Neutral Capabilities:**
  - `data.deduplication`: Domain-neutral. Uses composite key hashing over arbitrary fields.
  - `security.human_approval_gateway`: Domain-neutral safety gate. Enforces session tokens and dry-run boundaries.
- **Partially Coupled Capabilities:**
  - `scheduling.destination_window`: The scheduling mathematics (`zoneinfo`, DST, weekday rollover) are completely domain-neutral, but the university-to-timezone map is hardcoded for ~13 entities.
  - `research.verification`: Validates emails and URLs, but mandates that every entity must possess an email address.
- **Severely Coupled / Static Capabilities:**
  - `research.entity_discovery`: Operates on static in-memory fixtures (`SAMPLE_ENTITIES`).
  - `research.structured_extraction`: Synthesizes fake email addresses when missing.
  - `content.constrained_personalization`: Hardcoded with IIT Delhi student identity and 4-paragraph internship rhetoric.

---

## 3. Capability Reusability Matrix

| Capability ID | Current Status | Coupling Level | Required Transformation for Task 002 |
| :--- | :--- | :--- | :--- |
| `research.live_source_acquisition` | **Missing** | N/A | **Add new capability**: Live web search & HTTP page acquisition with URL, timestamp, title, and raw text evidence. |
| `research.entity_discovery` | Static Fixture | High | **Refactor**: Query live search sources and parse real candidate entities without hardcoded lists. |
| `research.structured_extraction` | Synthetic Heuristic | Medium | **Refactor**: Extract actual fields requested by the schema from retrieved source content without fabricating emails. |
| `research.verification` | Regex Only | Low | **Generalize**: Support configurable validation rules (e.g. profile URL required, email optional). |
| `data.deduplication` | Reusable | None | **Preserve**: Keep composite SHA-256 key deduplication. |
| `content.constrained_personalization`| Hardcoded | High | **Decouple**: Make sender profile, purpose, and constraints completely configurable; make optional in research tasks. |
| `scheduling.destination_window` | Reusable Logic | Low | **Generalize**: Make optional; dynamically resolve IANA timezones from country/location attributes. |
| `security.human_approval_gateway` | Reusable Gate | None | **Preserve**: Enforce strict approval before any sensitive dispatch. |

---

## 4. Architectural Requirements for Task 002

To satisfy Implementation Task 002 without replacing the existing architecture:

1. **Phase 2 — Live Source Acquisition:**
   Implement `research.live_source_acquisition` using real external search and retrieval providers (e.g. live search, OpenAlex API for academic faculty, and real-time web page acquisition via HTTP with HTML parsing) that captures source URL, retrieval timestamp, page title, and verifiable excerpt text.

2. **Phase 3 — Generalized Research Request Contract:**
   Define `ResearchRequest` specifying:
   - `entity_type` (e.g. `faculty`, `startup`, `researcher`, `company`)
   - `goal_and_constraints` (natural language query and filters)
   - `requested_fields` (e.g. `["name", "institution", "research_interests", "official_profile_url", "evidence"]` vs. `["company_name", "product_focus", "official_website", "location", "evidence"]`)
   - `max_records` and `execution_budget`

3. **Phase 4 — Adaptive Capability Composition:**
   Upgrade `IntentOrchestrator` to an `AdaptiveCapabilityPlanner` that:
   - Parses the intent into a `ResearchRequest`.
   - Composes *only* the necessary capabilities (e.g. 4 steps for pure research: Acquisition $\to$ Extraction $\to$ Verification $\to$ Deduplication).
   - Only includes Personalization or Scheduling if the user's intent explicitly asks for outreach or dispatch scheduling.
   - Accurately labels the execution path (`DYNAMIC_PLAN` vs. `DETERMINISTIC_FALLBACK`).

4. **Phase 5 — Blind Cross-Domain Verification:**
   Execute real live runs for both:
   - **Task A (Professors):** Autonomous systems & embodied AI faculty.
   - **Task B (Startups):** AI infrastructure startups in India.
   Assert at least 5 genuinely fresh, evidence-backed records per domain with different schemas, provenance metadata, and zero fabricated records.
