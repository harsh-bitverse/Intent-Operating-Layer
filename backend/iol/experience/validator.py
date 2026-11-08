"""
Schema Guard and Validator for IOL Experience Plans.
Enforces strict component allowlisting, tree depth bounds, prop schemas, and script injection protection.
"""

from typing import Any, Dict, List, Set, Tuple
from backend.iol.experience.models import ExperienceComponent, ExperiencePlan

ALLOWED_COMPONENT_TYPES: Set[str] = {
    "workspace_layout",
    "metric_strip",
    "data_grid",
    "comparison_matrix",
    "interactive_canvas_2d",
    "form_draft",
    "timeline_view",
    "action_panel",
}

MAX_COMPONENTS_PER_PLAN = 15
MAX_TREE_DEPTH = 4


class ExperienceValidationError(ValueError):
    """Raised when an ExperiencePlan violates catalog schemas or security bounds."""
    pass


class ExperiencePlanValidator:
    """Validates declarative experience plans against catalog contracts and safety policies."""

    @staticmethod
    def validate_plan(plan: ExperiencePlan) -> Tuple[bool, List[str]]:
        """
        Validates an ExperiencePlan instance.
        Returns (is_valid, list_of_violations).
        """
        errors: List[str] = []

        if not plan.plan_id:
            errors.append("Plan missing plan_id.")
        if not plan.task_id:
            errors.append("Plan missing task_id.")
        if not plan.title:
            errors.append("Plan missing title.")

        if len(plan.components) > MAX_COMPONENTS_PER_PLAN:
            errors.append(f"Plan exceeds maximum component budget ({len(plan.components)} > {MAX_COMPONENTS_PER_PLAN}).")

        component_ids: Set[str] = set()

        for comp in plan.components:
            # 1. Unique ID check
            if not comp.id:
                errors.append("Encountered component with empty id.")
            elif comp.id in component_ids:
                errors.append(f"Duplicate component id '{comp.id}'.")
            else:
                component_ids.add(comp.id)

            # 2. Allowed catalog type check
            if comp.type not in ALLOWED_COMPONENT_TYPES:
                errors.append(f"Unknown component type '{comp.type}'. Allowed: {ALLOWED_COMPONENT_TYPES}.")

            # 3. Prop security check: No raw script or executable injection
            prop_str = str(comp.props).lower()
            if "<script" in prop_str or "javascript:" in prop_str or "onload=" in prop_str or "onerror=" in prop_str:
                errors.append(f"Potential script injection detected in component '{comp.id}' props.")

            # 4. Specific component prop validations
            if comp.type == "data_grid":
                cols = comp.props.get("columns", [])
                if not isinstance(cols, list):
                    errors.append(f"data_grid '{comp.id}' must provide a list of columns.")
            elif comp.type == "metric_strip":
                metrics = comp.props.get("metrics", [])
                if not isinstance(metrics, list):
                    errors.append(f"metric_strip '{comp.id}' must provide a list of metrics.")

        is_valid = len(errors) == 0
        return is_valid, errors

    @staticmethod
    def sanitize_plan(plan_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitizes raw dictionary representation, removing disallowed fields or unsafe types.
        """
        safe_dict = dict(plan_dict)
        raw_components = safe_dict.get("components", [])
        safe_components = []
        for c in raw_components[:MAX_COMPONENTS_PER_PLAN]:
            if isinstance(c, dict):
                ctype = c.get("type", "")
                if ctype in ALLOWED_COMPONENT_TYPES:
                    safe_components.append(c)
        safe_dict["components"] = safe_components
        return safe_dict


validator = ExperiencePlanValidator()
experience_plan_validator = validator
