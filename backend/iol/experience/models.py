"""
Domain models for the IOL Experience Engine.
Defines schemas for ExperiencePlan, ExperienceComponent, ExperienceRecipe, and rendering modes.
"""

from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class ExperienceMode(str, Enum):
    """Rendering modes supported by the Experience Engine."""
    INLINE_VISUAL = "INLINE_VISUAL"
    EXPANDABLE_VISUAL = "EXPANDABLE_VISUAL"
    FULL_WORKSPACE = "FULL_WORKSPACE"


class ExperienceComponent(BaseModel):
    """
    Individual UI component specification in the catalog.
    Matches the declarative, validated component schema.
    """
    id: str
    type: str  # workspace_layout, metric_strip, data_grid, interactive_canvas_2d, etc.
    props: Dict[str, Any] = Field(default_factory=dict)
    children: Optional[List[str]] = None


class ExperiencePlan(BaseModel):
    """
    Complete visual layout and interactive specification for a task workspace.
    Emitted by ExperiencePlanner, persisted with task state, and streamed to frontend.
    """
    plan_id: str
    task_id: str
    mode: ExperienceMode = ExperienceMode.FULL_WORKSPACE
    title: str
    subtitle: Optional[str] = None
    status: str = "ACTIVE"  # "ACTIVE", "COMPLETED", "FAILED"
    components: List[ExperienceComponent] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def get_component(self, component_id: str) -> Optional[ExperienceComponent]:
        """Find a component by ID."""
        for comp in self.components:
            if comp.id == component_id:
                return comp
        return None

    def update_component_props(self, component_id: str, new_props: Dict[str, Any]) -> bool:
        """Update properties of an existing component."""
        comp = self.get_component(component_id)
        if comp:
            comp.props.update(new_props)
            return True
        return False


class ExperienceRecipe(BaseModel):
    """
    Reusable template/recipe for rendering a family of task outcomes.
    Allows Experience Engine to adapt prior presentation knowledge across similar tasks.
    """
    recipe_id: str
    name: str
    target_intent_family: str  # "research_database", "educational_simulation", "comparison_analysis"
    description: str
    compatible_entity_types: List[str]
    layout_mode: ExperienceMode = ExperienceMode.FULL_WORKSPACE
    default_components: List[Dict[str, Any]]
    data_binding_slots: Dict[str, str] = Field(default_factory=dict)
    adaptation_rules: Dict[str, Any] = Field(default_factory=dict)
