"""
Provider-Independent Agent Adapter Interface for IOL.
Decouples intent planning and decision making from specific proprietary LLM vendors.
Supports deterministic orchestrators, local models, and external foundation models.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from backend.iol.capabilities.base import CapabilityMetadata


class PlanStep(BaseModel):
    """An individual capability invocation step within an execution plan."""
    step_id: str
    capability_id: str
    title: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    dynamic_param_mappings: Dict[str, str] = Field(
        default_factory=dict,
        description="Maps parameter keys to outputs from previous steps, e.g. {'entities': 'step_1.entities'}"
    )


class ExecutionPlan(BaseModel):
    """Structured plan composed of capability steps to fulfill user intent."""
    plan_id: str
    intent: str
    rationale: str
    steps: List[PlanStep] = Field(default_factory=list)


class BaseAgentAdapter(ABC):
    """Abstract interface for provider-independent agent planners."""

    @abstractmethod
    async def plan(
        self,
        intent: str,
        available_capabilities: List[CapabilityMetadata],
        context: Optional[Dict[str, Any]] = None
    ) -> ExecutionPlan:
        """Translates user intent into a validated, capability-aligned execution plan."""
        pass
