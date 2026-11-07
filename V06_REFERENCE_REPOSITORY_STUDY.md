# IOL v0.6 — Reference Repository Deep Study & Comparative Analysis

**Research Date:** November 7, 2026  
**Inspection Workspace:** `C:\Workspace\temp_research\`  
**Target:** Informing IOL v0.6 Experience Engine Architecture

---

## 1. Executive Summary

We performed source-level inspection of six primary open-source references spanning **Generative UI**, **Agent UI Protocols**, **Workflow/Browser Execution**, and **Interactive Graph Visualization**:

| Repository | Focus Area | Latest Commit / Version | License | Primary Architectural Takeaway |
| :--- | :--- | :--- | :--- | :--- |
| **`vercel-labs/json-render`** | Declarative Component Catalog & Spec Renderer | `main` (Nov 2026) | Apache-2.0 | Clean separation of typed **Catalog** (frontend definitions) and **Spec** (model-directed AST). Zero arbitrary code execution. |
| **`ag-ui-protocol/ag-ui`** | Agent UI Protocol | `1.0-draft` | MIT | **JSON Patch (RFC 6902)** for incremental streaming UI mutations over SSE. |
| **`a2ui-project/a2ui`** | Agent-to-User Interface Spec | `v0.9` | Apache-2.0 | Versioned component catalogs and strict schema conformance. |
| **`CopilotKit/OpenIntelligentUI`**| In-Chat Generative UI | `main` | MIT | Demonstrates tool-rendered components, but restricted to chat transcripts. |
| **`xyflow/xyflow` (React Flow)** | 2D Node-Edge Interactive Visualization | `v12.x` | MIT | Standard for interactive 2D graphs, neural network forward-pass step controllers, and pipeline visualization. |
| **`browser-use/browser-use`** | Vision-Driven Browser Automation | `v0.1.x` | MIT | Autonomous Playwright DOM navigation; valuable for P2, but high latency/token overhead. |

---

## 2. In-Depth Project Evaluations

### 2.1 Vercel Labs `json-render`
- **Source Entry Points:** `packages/core/src/schema.ts`, `spec-validator.ts`, `props.ts`, `diff.ts`.
- **Data & Event Flow:** Model emits JSON AST -> `SpecValidator` checks allowed components and prop schemas -> Renderer binds dynamic expressions (`data-binding`) without re-rendering unaffected DOM nodes.
- **Safety Boundaries:** Immune to XSS and arbitrary code execution because components are restricted to pre-registered React components in the Catalog.
- **Adoption Decision:** **ADOPT CONCEPT.** Author an independent, lightweight `ExperiencePlan` schema and `ComponentCatalog` in IOL inspired by `json-render`'s catalog/spec decoupling.

### 2.2 AG-UI Protocol (`ag-ui`)
- **Source Entry Points:** `spec/draft/schema.json`, `spec/README.md`.
- **Data & Event Flow:** Server emits lifecycle events and RFC 6902 JSON Patch operations over SSE/WebSocket. Client applies patches to local state store.
- **Safety Boundaries:** Receiver strips unknown properties rather than crashing. Closed schema definitions.
- **Adoption Decision:** **ADOPT STREAMING INVARIANT.** Incorporate incremental UI patching and `UI_PATCHED` / `UI_UPDATED` events into IOL's SSE stream to prevent re-sending entire layouts during live task execution.

### 2.3 A2UI (`a2ui`)
- **Source Entry Points:** `specification/v0_9/`, `typescript/`, `catalogs/`.
- **Analysis:** Focused on cross-platform native mobile (Flutter/Kotlin/Swift) and Web.
- **Adoption Decision:** **DEFER FULL PROTOCOL.** A2UI's cross-platform multi-language harness adds unnecessary complexity for IOL's Web-first Next.js stack. We adopt its principle of semantic component catalogs.

### 2.4 Open Intelligent UI (`OpenIntelligentUI`)
- **Source Entry Points:** `apps/app/`, `packages/design-system/`.
- **Analysis:** Built on CopilotKit and AG-UI. Strong aesthetic design for in-chat cards.
- **Key Disadvantage:** Traps outcomes in a **chat window**. For complex engineering and research tasks (e.g. 50-row databases, multi-feature comparison matrices), chat transcripts are claustrophobic.
- **Adoption Decision:** **ARCHITECTURAL COUNTER-MODEL.** IOL differentiates by delivering **Full-Screen Adaptive Workspaces** (`FULL_WORKSPACE`), rather than another conversational chat assistant.

### 2.5 XYFlow / React Flow (`xyflow`)
- **Source Entry Points:** `packages/react/src/container/ReactFlow/`.
- **Data & Event Flow:** Declarative nodes array + edges array -> Canvas render with interactive pan, zoom, click, drag, and custom node components.
- **Safety Boundaries:** Pure client-side SVG/HTML DOM rendering.
- **Adoption Decision:** **ADOPT AS FOUNDATION FOR DEMO B.** Lightweight React Flow / SVG node-edge canvas allows us to render real interactive educational models (e.g. neural network forward/backpropagation with step-by-step weight updates).

### 2.6 Browser-Use (`browser-use`)
- **Source Entry Points:** `browser_use/agent/service.py`, `browser_use/browser/context.py`.
- **Analysis:** Uses vision models to look at browser screenshots and click DOM elements.
- **Cost & Latency:** ~5-15 seconds per click; high LLM token consumption.
- **Adoption Decision:** **DEFER TO P2.** IOL's primary value proposition is fast, reliable, source-verified intent execution. Our API-first acquisition (OpenAlex, GitHub, DuckDuckGo) executes in <2 seconds with cryptographic provenance. Browser-use can be added as a specialized fallback capability in future milestones.

---

## 3. Technology Selection Matrix for IOL v0.6

| Subsystem | Selected Architecture | Implementation Strategy |
| :--- | :--- | :--- |
| **ExperiencePlan Spec** | Strongly typed Pydantic (Backend) + TypeScript (Frontend) | Custom IOL spec defining layout containers, grids, tables, cards, and 2D canvas. |
| **Component Catalog** | Whitelisted, sandboxed component library | Hand-authored, styled with Tailwind CSS, supporting `INLINE_VISUAL`, `EXPANDABLE_VISUAL`, and `FULL_WORKSPACE`. |
| **Model Gateway** | Provider-neutral LLM adapter with deterministic fallback | Generates ExperiencePlan from intent & schema; falls back to deterministic recipe if model is offline. |
| **Incremental Data Binding** | Progressive placeholder-first binding | Layout is emitted immediately (`INITIALIZING`/`SKELETON`); real records stream in and populate existing components. |
| **Interactive 2D Canvas** | Declarative Node-and-Edge Graph Engine | Interactive SVG/canvas engine with step-by-step parameter progression for educational demos. |
| **Experience Knowledge** | Recipe Store & Schema Signature Matcher | Stores abstract presentation templates; matches incoming task schemas and adapts layouts dynamically. |
| **Authentic Replay** | Replay Reader & State Restorer | Restores UI specs, binding states, and event logs from stored task runs. |
