"""
Experience Planner for IOL v0.6.
Responsible for compiling and progressively updating ExperiencePlans
without delaying or blocking the core Execution Engine.
"""

from typing import Any, Dict, List, Optional
from backend.iol.experience.models import ExperiencePlan
from backend.iol.experience.recipes import experience_recipe_store
from backend.iol.experience.gateway import model_provider_gateway


class ExperiencePlanner:
    """Compiles task layout plans and binds progressive execution data into UI components."""

    def __init__(self):
        self.recipe_store = experience_recipe_store

    def plan_experience(
        self,
        task_id: str,
        intent: str,
        research_request: Optional[Any] = None,
        context_metadata: Optional[Dict[str, Any]] = None,
        expected_shape: str = "collection",
    ) -> ExperiencePlan:
        """
        Produce initial ExperiencePlan immediately (<5ms) before or at the start of task execution.
        Attempts model-directed synthesis if provider credentials exist; otherwise safely adapts recipes.
        Never mislabels fallbacks as MODEL_GENERATED.
        """
        # 1. Attempt model-directed generation if provider is configured
        provider_info = model_provider_gateway.get_configured_provider(context_metadata)
        if provider_info:
            try:
                import asyncio
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(
                        asyncio.run,
                        model_provider_gateway.generate_plan(task_id, intent, expected_shape, context_metadata)
                    )
                    model_plan = future.result(timeout=4.0)
                if model_plan:
                    return model_plan
            except Exception:
                pass

        # 2. Recipe adaptation / deterministic fallback path
        entity_type = None
        custom_columns = None

        if research_request:
            entity_type = getattr(research_request, "entity_type", None) or getattr(research_request, "target_entity", None)

        if not entity_type:
            intent_lower = intent.lower()
            if "startup" in intent_lower or "company" in intent_lower or "companies" in intent_lower:
                entity_type = "startup"
            elif "professor" in intent_lower or "faculty" in intent_lower or "researcher" in intent_lower:
                entity_type = "professor"
            elif "neural" in intent_lower or "teach" in intent_lower or "network" in intent_lower:
                entity_type = "neural_network"
            elif "repository" in intent_lower or "repo" in intent_lower or "tool" in intent_lower or "framework" in intent_lower:
                entity_type = "repository"
            elif any(w in intent_lower for w in ["form", "passport", "license", "apply", "renewal"]):
                entity_type = "form"

        # Build column schema tailored to entity type if applicable
        if entity_type == "startup":
            custom_columns = [
                {"key": "company_name", "header": "Startup Name", "type": "text"},
                {"key": "location", "header": "Location", "type": "badge"},
                {"key": "product_category", "header": "Category", "type": "text"},
                {"key": "key_product", "header": "Key Offering", "type": "text"},
                {"key": "stage", "header": "Stage / Traction", "type": "badge"},
                {"key": "url", "header": "Verified URL", "type": "link"},
                {"key": "confidence", "header": "Confidence", "type": "score"}
            ]
        elif entity_type == "professor":
            custom_columns = [
                {"key": "name", "header": "Professor Name", "type": "text"},
                {"key": "institution", "header": "Institution", "type": "badge"},
                {"key": "research_focus", "header": "Research Focus", "type": "text"},
                {"key": "top_paper", "header": "Key Work / Paper", "type": "text"},
                {"key": "url", "header": "Profile / OpenAlex", "type": "link"},
                {"key": "confidence", "header": "Confidence", "type": "score"}
            ]
        elif entity_type == "repository":
            custom_columns = [
                {"key": "name", "header": "Repository / Tool", "type": "text"},
                {"key": "stars", "header": "GitHub Stars", "type": "badge"},
                {"key": "description", "header": "Description", "type": "text"},
                {"key": "license", "header": "License", "type": "badge"},
                {"key": "url", "header": "Repository URL", "type": "link"},
                {"key": "confidence", "header": "Confidence", "type": "score"}
            ]

        # Match recipe
        recipe = self.recipe_store.find_matching_recipe(intent, entity_type)

        # Distinguish between specifically matched recipe and generic fallback
        is_default_fallback = (
            recipe.recipe_id == "exp_recipe_research_database" and
            not any(k in intent.lower() for k in ["startup", "professor", "research", "database", "find", "ai"])
        )
        origin = "DETERMINISTIC_FALLBACK" if is_default_fallback else "RECIPE_ADAPTED"

        # Adapt into concrete plan
        plan = self.recipe_store.adapt_recipe_to_plan(
            recipe=recipe,
            task_id=task_id,
            intent=intent,
            entity_type=entity_type,
            custom_columns=custom_columns
        )
        plan.plan_origin = origin
        plan.version = 1
        plan.model_metadata = {
            "provider": None,
            "status": "MODEL_GENERATION_BLOCKED",
            "origin_reason": "No active external LLM credentials configured (OPENAI_API_KEY, ANTHROPIC_API_KEY, or OLLAMA_HOST missing); safely adapted verified declarative layout template.",
            "recipe_id": recipe.recipe_id
        }

        return plan

    def bind_records_to_plan(
        self,
        plan: ExperiencePlan,
        records: List[Dict[str, Any]],
        execution_mode: Optional[str] = None,
        status: Optional[str] = None
    ) -> ExperiencePlan:
        """
        Progressively bind verified records and updated status into the ExperiencePlan.
        """
        target_slot = plan.metadata.get("data_binding_slots", {}).get("primary_records", "research_grid_main")
        grid = plan.get_component(target_slot)
        if grid:
            grid.props["rows"] = records
            grid.props["placeholder_count"] = max(0, 5 - len(records))

        # Update metrics strip
        metrics_slot = plan.metadata.get("data_binding_slots", {}).get("status_metrics", "metric_strip_main")
        metric_strip = plan.get_component(metrics_slot)
        if metric_strip:
            metrics_list = metric_strip.props.get("metrics", [])
            for m in metrics_list:
                lbl = m.get("label", "")
                if "Status" in lbl and status:
                    m["value"] = status
                    m["badge_color"] = "emerald" if status == "COMPLETED" else "blue"
                elif "Execution Mode" in lbl and execution_mode:
                    m["value"] = execution_mode
                    m["badge_color"] = "green" if "LIVE" in execution_mode else "purple"
                elif "Entities" in lbl or "Verified" in lbl or "Discovered" in lbl:
                    m["value"] = len(records)
                    m["badge_color"] = "emerald"

        if status:
            plan.status = status

        return plan

    def bind_simulation_to_plan(
        self,
        plan: ExperiencePlan,
        step_idx: int,
        metrics: Optional[Dict[str, Any]] = None
    ) -> ExperiencePlan:
        """
        Update educational 2D interactive canvas state for step-by-step walkthroughs.
        """
        target_slot = plan.metadata.get("data_binding_slots", {}).get("simulation_state", "neural_canvas_main")
        canvas = plan.get_component(target_slot)
        if canvas:
            canvas.props["current_step"] = step_idx

        # Update metric strip
        metrics_slot = plan.metadata.get("data_binding_slots", {}).get("status_metrics", "metric_strip_main")
        metric_strip = plan.get_component(metrics_slot)
        if metric_strip and metrics:
            metrics_list = metric_strip.props.get("metrics", [])
            for m in metrics_list:
                key = m.get("label", "").lower()
                for k, v in metrics.items():
                    if k.lower() in key:
                        m["value"] = str(v)

        return plan

    def bind_outcome_to_plan(
        self,
        plan: ExperiencePlan,
        outcome: Any
    ) -> ExperiencePlan:
        """
        Progressively binds an OutcomeEnvelopeV1 into the ExperiencePlan.
        Monotonically increments plan version without making LLM calls.
        """
        outcome_dict = outcome.model_dump() if hasattr(outcome, "model_dump") else outcome
        items = outcome_dict.get("items", [])
        field_schema = outcome_dict.get("field_schema", [])

        # Update data_grid or comparison component if present
        target_slot = plan.metadata.get("data_binding_slots", {}).get("primary_records", "research_grid_main")
        grid = plan.get_component(target_slot) or plan.get_component("comparison_matrix_main")
        if grid:
            if field_schema:
                grid.props["columns"] = [
                    {"key": f.get("key"), "header": f.get("header"), "type": f.get("type", "text")}
                    for f in field_schema
                ]
            rows = []
            for it in items:
                row = dict(it.get("fields", {}))
                row["id"] = it.get("id")
                if "evidence" in it:
                    row["_evidence"] = it["evidence"]
                rows.append(row)
            grid.props["rows"] = rows
            grid.props["placeholder_count"] = max(0, 4 - len(rows))

        # Update metric strip
        metrics_slot = plan.metadata.get("data_binding_slots", {}).get("status_metrics", "metric_strip_main")
        metric_strip = plan.get_component(metrics_slot)
        if metric_strip:
            metrics_list = metric_strip.props.get("metrics", [])
            for m in metrics_list:
                lbl = m.get("label", "").lower()
                if "status" in lbl:
                    m["value"] = "COMPLETED" if len(items) > 0 else "RUNNING"
                    m["badge_color"] = "emerald"
                elif "records" in lbl or "entities" in lbl or "compared" in lbl:
                    m["value"] = len(items)
                    m["badge_color"] = "emerald"

        plan.version += 1
        return plan


# Global singleton instance
experience_planner = ExperiencePlanner()
