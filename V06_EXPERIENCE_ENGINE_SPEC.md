# IOL v0.6 — Experience Engine Technical Specification

**Author:** IOL Principal Engineering Team  
**Date:** November 7, 2026  
**Status:** Approved Specification  
**Version:** 0.6.0

---

## 1. System Overview

The **Experience Engine** is the visual-first presentation subsystem of the Intent Operating Layer. It runs concurrently with the **Execution Engine**, translating raw intent, task progress, and verified outcomes into adaptive, interactive workspaces.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        USER INTENT INPUT                               │
└───────────────────┬────────────────────────────────┬───────────────────┘
                    │                                │
                    ▼ (Concurrent Execution)         ▼ (Concurrent Experience)
┌──────────────────────────────────────┐  ┌──────────────────────────────┐
│       EXECUTION ENGINE               │  │      EXPERIENCE ENGINE       │
│  - Adaptive Capability Planner       │  │  - Experience Recipe Store   │
│  - Live Source Acquisition           │  │  - Experience Planner        │
│  - Field Extraction & Verification   │  │  - Component Catalog         │
│  - Semantic Relevance Gate           │  │  - Spec Validator            │
│  - Cryptographic Deduplication       │  │  - Progressive Data Binder   │
└──────────────────┬───────────────────┘  └──────────────┬───────────────┘
                   │                                     │
                   │ Emit Verified Data                  │ Compile Layout Spec
                   ▼                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   DURABLE STORE & STREAMING BUS                        │
│         - Task States, Events & Progressive Bindings                   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ SSE (UI_UPDATED / EXPERIENCE_UPDATED)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│               FRONTEND: ADAPTIVE WORKSPACE RENDERER                    │
│  - Full-Screen Adaptive Workspace Mode (FULL_WORKSPACE)               │
│  - Interactive Data Grids with Field-Level Evidence Drawers            │
│  - Interactive 2D Node-Edge Canvas with Mathematical Simulation        │
│  - Reconnection, Tab Recovery & Authentic Recorded Replay              │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. ExperiencePlan JSON Specification

The `ExperiencePlan` defines the complete visual structure of the task interface.

```json
{
  "$schema": "https://iol.ai/schemas/v0.6/experience_plan.json",
  "plan_id": "exp_plan_8f9e1c2a",
  "task_id": "task_a1b2c3d4",
  "mode": "FULL_WORKSPACE",
  "title": "Autonomous AI Research Workspace",
  "subtitle": "Indian AI Infrastructure & Hardware Startups",
  "status": "ACTIVE",
  "components": [
    {
      "id": "metric_strip_main",
      "type": "metric_strip",
      "props": {
        "metrics": [
          { "label": "Status", "value": "RUNNING", "badge_color": "blue" },
          { "label": "Execution Mode", "value": "LIVE (GITHUB REPOSITORIES API)", "badge_color": "green" },
          { "label": "Entities Verified", "value": 10, "badge_color": "emerald" }
        ]
      }
    },
    {
      "id": "research_grid_main",
      "type": "data_grid",
      "props": {
        "title": "Verified Startup Directory",
        "columns": [
          { "key": "company_name", "header": "Startup Name", "type": "text" },
          { "key": "location", "header": "Headquarters", "type": "badge" },
          { "key": "product_category", "header": "Category", "type": "text" },
          { "key": "confidence", "header": "Confidence", "type": "score" }
        ],
        "rows": [],
        "placeholder_count": 5
      }
    }
  ]
}
```

---

## 3. Component Catalog Specification

### 3.1 `workspace_layout`
- **Purpose:** Full-screen responsive grid container managing master-detail splits, sidebar execution roadmaps, and central data canvases.
- **Props:** `variant` (`split_horizontal`, `split_vertical`, `single_canvas`), `sidebar_open` (`boolean`).

### 3.2 `metric_strip`
- **Purpose:** Displays live execution statistics, current step progress, and execution mode badging (`LIVE`, `RECORDED REPLAY`, `FALLBACK REPLAY`).
- **Props:** `metrics` (Array of label, value, unit, badge color).

### 3.3 `data_grid`
- **Purpose:** Interactive tabular outcome viewer with sorting, multi-column search, expandable rows, and CSV/JSON export.
- **Props:** `columns`, `rows`, `placeholder_count`, `searchable_keys`, `exportable`.

### 3.4 `evidence_drawer`
- **Purpose:** Field-level evidence inspector displaying provenance URL, content snippet, SHA-256 verification hash, and conservative confidence scoring.
- **Props:** `field_evidence_map`, `entity_classification`, `validation_flags`.

### 3.5 `interactive_canvas_2d` (Mandatory Demo B)
- **Purpose:** Interactive 2D node-and-edge canvas for mathematical explanations, algorithm simulations, and process flows.
- **Props:**
  - `nodes`: Array of `{ id, label, layer, value, bias, x, y }`.
  - `edges`: Array of `{ id, source, target, weight, animated }`.
  - `step`: Current animation/simulation step (`0` to `total_steps`).
  - `total_steps`: Number of progressive steps in simulation.
  - `playback_state`: `"playing"` | `"paused"` | `"idle"`.
  - `metrics`: Numerical outputs (e.g. `Loss = 0.042`, `Target = 1.0`, `Output = 0.89`).
  - `controls`: Step Forward, Step Backward, Auto Play toggle, Weight Slider.

### 3.6 `skeleton_placeholder`
- **Purpose:** Renders animated loading skeletons matching the target component dimensions before real records are emitted.

---

## 4. Experience Knowledge & Recipe Foundation

An `ExperienceRecipe` encapsulates a proven, abstract presentation strategy:

```python
class ExperienceRecipe(BaseModel):
    recipe_id: str
    target_intent_family: str  # e.g., "research_database", "educational_simulation", "comparison_analysis"
    compatible_entity_types: List[str]
    layout_mode: Literal["INLINE_VISUAL", "EXPANDABLE_VISUAL", "FULL_WORKSPACE"]
    default_components: List[Dict[str, Any]]
    data_binding_slots: Dict[str, str]  # slot_name -> target_component_id
    adaptation_rules: Dict[str, Any]
```

### Matching Algorithm:
1. **Signature Extraction:** Extract intent category (`research`, `educational`, `comparison`), entity schema, and requested attributes.
2. **Recipe Lookup:** Search `ExperienceRecipeStore` for highest compatibility score:
   $$\text{Score} = w_1 \cdot \text{CategoryMatch} + w_2 \cdot \text{SchemaOverlap} + w_3 \cdot \text{ComplexityFit}$$
3. **Recipe Adaptation:**
   - Clone the matching recipe.
   - Inject the task's specific column definitions into the `data_grid`.
   - Update titles, subtitles, and search filters.
   - Emit the customized `ExperiencePlan`.

---

## 5. Incremental Data Binding Protocol

1. **Initial Emission:** Background worker immediately creates and persists the `ExperiencePlan` with empty rows and `placeholder_count: 5`.
2. **Step Updates:** When capability steps finish, the worker binds extracted records directly into `props.rows` of the target `data_grid` or updates `props.metrics` on the `metric_strip`.
3. **Frontend Differential Patching:**
   - The React renderer identifies components by stable `id`.
   - Local state (such as an expanded row or an active tab) is preserved across SSE events.
   - Only modified child elements re-render.
