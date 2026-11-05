"""
Learned Skill Models and Lifecycle State Machine for IOL.
Defines versioned skill representations extracted from successful task execution traces.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.iol.core.research_models import utc_now_iso


class SkillLifecycleState(str, Enum):
    """Formal lifecycle states for extracted skills."""
    CANDIDATE = "CANDIDATE"
    VALIDATED_FOR_TASK_FAMILY = "VALIDATED_FOR_TASK_FAMILY"
    TRUSTED_FOR_BOUNDED_REUSE = "TRUSTED_FOR_BOUNDED_REUSE"
    DEPRECATED = "DEPRECATED"


class SkillStepPattern(BaseModel):
    """Parameterized capability step blueprint."""
    step_id: str
    capability_id: str
    title: str
    description: str
    parameter_template: Dict[str, Any] = Field(default_factory=dict)
    dynamic_param_mappings: Dict[str, str] = Field(default_factory=dict)


class SkillValidationRecord(BaseModel):
    """Audit record of a validation run on a new task."""
    task_id: str
    validated_at: str = Field(default_factory=utc_now_iso)
    success: bool
    domain: str
    notes: str


class LearnedSkill(BaseModel):
    """
    A learned, versioned capability pipeline synthesized from successful executions.
    Completely sanitized of user-specific identities, emails, or credentials.
    """
    skill_id: str
    name: str
    task_family: str
    version: str = "1.0.0"
    lifecycle_state: SkillLifecycleState = SkillLifecycleState.CANDIDATE
    intent_pattern: str = Field(description="Regex or keyword pattern matching target task family")
    description: str
    steps: List[SkillStepPattern]
    source_task_id: str
    created_at: str = Field(default_factory=utc_now_iso)
    validation_history: List[SkillValidationRecord] = Field(default_factory=list)
    usage_count: int = 0
    success_rate: float = 1.0
    benchmark_metrics: Dict[str, Any] = Field(default_factory=dict)
