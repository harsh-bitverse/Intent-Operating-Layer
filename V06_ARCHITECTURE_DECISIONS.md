# IOL v0.6 — Architecture Decision Records (ADR)

**Document Version:** 1.0  
**Date:** November 7, 2026  
**Status:** **APPROVED & FROZEN FOR IMPLEMENTATION**  
**Target Delivery:** IOL v0.6 Experience Engine

---

## 1. Architectural Invariants (Non-Negotiable)

1. **Decoupled Concurrency:** Task execution continues regardless of whether UI planning succeeds or fails.
2. **Authoritative Ground Truth:** Verified task data in the durable store is authoritative; the generative UI layer cannot hallucinate or invent records.
3. **Execution Safety Boundary:** UI components and client-side actions cannot bypass server-side authorization or dispatch unapproved outbound actions.
4. **Independent Persistence:** Task outcomes, execution events, and ExperiencePlans are independently versioned and durably persisted.
5. **Incremental Data Binding:** UI updates bind real data into existing component slots without regenerating or re-rendering the entire layout.
6. **Server-Side Credentials:** All API keys and model credentials remain server-side; none are transmitted to the client.
7. **Privacy-Preserving Recipes:** Experience knowledge stores abstract structural recipes; private entities or personal data are never retained in shared recipes.
8. **Visual-First Interaction:** Presentation prioritizes full-screen adaptive workspaces over vertical chat transcripts.
9. **Creative Adaptation:** Presentation reuse adapts to new schemas and tasks rather than repeatedly cloning a rigid static template.
10. **Authentic Replay Distinction:** Recorded replays are explicitly and visually distinguished from live network executions.

---

## 2. Subsystem Decisions

### ADR-01: ExperiencePlan Specification
- **Decision:** Define a strongly-typed Pydantic model (`backend/iol/experience/models.py`) and matching TypeScript schema (`frontend/src/types/experience.ts`).
- **Container Modes:**
  - `INLINE_VISUAL`: Compact visual embedded in standard task timeline.
  - `EXPANDABLE_VISUAL`: Drawer/modal for deep evidence and comparison inspection.
  - `FULL_WORKSPACE`: Full-screen adaptive workspace with master-detail navigation, filterable tables, entity cards, and 2D canvas controls.
- **Alternatives Considered:** Raw HTML/JSX streaming (rejected: high XSS risk), JSON-LD (rejected: poor UI expressiveness).
- **Effort / Latency:** Low effort (<2 hours); sub-millisecond serialization overhead.

### ADR-02: Component Catalog & Sandboxed Renderer
- **Decision:** Pre-register an expressive set of safe, styled React components in `ExperienceRenderer.tsx`:
  - `workspace_layout`: Multi-panel responsive grids, split panes, and header action bars.
  - `metric_strip`: Real-time execution indicators, step metrics, and source counters.
  - `data_grid`: Sortable, filterable tables with column formatters (scores, badges, links).
  - `evidence_drawer`: Field-level provenance inspector with cryptographic hash citations.
  - `comparison_view`: Multi-entity side-by-side feature matrix.
  - `interactive_canvas_2d`: Declarative node-and-edge visual canvas with step controllers (Play/Pause/Step) and real mathematical state computation.
  - `skeleton_placeholder`: Progressive loading skeletons during initial task phases.
- **Security:** Model only emits component types and prop mappings; arbitrary JavaScript execution (`eval`, `dangerouslySetInnerHTML`) is strictly prohibited.

### ADR-03: Model Gateway & Experience Planner
- **Decision:** Implement a provider-neutral `ModelGateway` with deterministic fallback. If an external LLM is not configured, the Experience Planner uses deterministic recipe matching (`ExperienceRecipeStore`) to compile the ExperiencePlan.
- **Performance:** Deterministic fallback plans compile in `< 10ms`. When an LLM is active, it runs asynchronously in parallel with worker startup, never delaying task execution.

### ADR-04: Streaming Data Binding & Progressive Placeholders
- **Decision:** 
  1. At task submission, worker or Experience Planner immediately attaches an initial `ExperiencePlan` containing skeleton placeholders.
  2. As capabilities execute, data is published into component slots (`target_component_id: "candidate_grid"`) via `UI_UPDATED` / `EXPERIENCE_UPDATED` events.
  3. The frontend maintains component state across updates (selected rows, active tab, zoom level) using stable component IDs.

### ADR-05: Interactive 2D Educational Visualization (Mandatory Demo B)
- **Decision:** Build an interactive 2D node-and-edge canvas component (`interactive_canvas_2d`) driven by genuine mathematical simulation:
  - Architecture: Multi-layer neural network (Input layer -> Hidden layer -> Output layer) with weighted synapses and activation biases.
  - Controls: Step Forward, Step Backward, Auto Play (1s tick), Pause, Weight Adjustment slider, and Input perturbation.
  - State: Real forward-propagation numerical calculations:
    $$\text{Hidden} = \sigma(W_1 \cdot X + b_1), \quad \hat{y} = \sigma(W_2 \cdot \text{Hidden} + b_2), \quad \text{Loss} = \frac{1}{2}(y - \hat{y})^2$$
  - Real calculations ensure the educational experience is authentic and not a static looping GIF.

### ADR-06: Experience Knowledge & Recipe Adaptation
- **Decision:** Implement `ExperienceRecipeStore` in `backend/iol/experience/recipes.py`:
  - Stores abstract layout recipes: `ResearchWorkspaceRecipe`, `EducationalExplanationRecipe`, `ComparativeMatrixRecipe`.
  - Signature matcher: Matches incoming intent category and requested fields to candidate recipes.
  - Adaptation: Clones recipe, injects task-specific column schemas, title, and default filters, producing a customized `ExperiencePlan`.

### ADR-07: Authentic Recorded Replay
- **Decision:** Replay reader in `TaskView.tsx` and `scripts/run_demo.py` restores stored `ExperiencePlan`, step timeline, and evidence payloads from durable storage.
- **Transparency:** Prominent `[📼 RECORDED REPLAY]` badge displayed.

---

## 3. Implementation Roadmap

- **Step 1:** Experience Models & Spec (`backend/iol/experience/models.py`, `frontend/src/types/experience.ts`)
- **Step 2:** Experience Recipes & Knowledge Store (`backend/iol/experience/recipes.py`, `planner.py`)
- **Step 3:** Component Catalog & Generative UI Renderer (`frontend/src/components/experience/ExperienceRenderer.tsx`, `InteractiveCanvas2D.tsx`)
- **Step 4:** Progressive Data Binding & Worker Integration (`backend/iol/worker/background_worker.py`)
- **Step 5:** Demonstrations: Research Workspace (Demo A) & Interactive Educational 2D Neural Network (Demo B)
- **Step 6:** Test Suites (Pytest + Playwright) & Verification
