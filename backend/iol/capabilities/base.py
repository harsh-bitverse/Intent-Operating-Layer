"""
General Capability Contract and Base Interface for IOL.
Every capability exposes typed inputs (Pydantic), typed outputs, permissions, and verification metadata.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, Field


class ExecutionContext(BaseModel):
    """Runtime context provided to a capability upon execution."""
    task_id: str
    step_id: str
    operator_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CapabilityMetadata(BaseModel):
    """Declarative specification of a capability for discovery and planning."""
    capability_id: str
    name: str
    description: str
    version: str = "1.0.0"
    required_permissions: List[str] = Field(default_factory=list)
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    verification_metadata: Dict[str, Any] = Field(default_factory=dict)
    estimated_cost_usd: float = 0.0


class CapabilityResult(BaseModel):
    """Standardized result returned by capability execution."""
    success: bool
    data: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    verification_score: float = Field(default=1.0, ge=0.0, le=1.0)
    verification_details: Dict[str, Any] = Field(default_factory=dict)
    cost_usd: float = 0.0


class BaseCapability(ABC):
    """Abstract base class for all IOL reusable capabilities."""

    capability_id: str
    name: str
    description: str
    version: str = "1.0.0"
    input_model: Type[BaseModel]
    output_model: Type[BaseModel]
    required_permissions: List[str] = []
    estimated_cost_usd: float = 0.0
    verification_metadata: Dict[str, Any] = {}

    @abstractmethod
    async def execute(self, params: BaseModel, context: ExecutionContext) -> CapabilityResult:
        """Executes the capability with validated typed parameters."""
        pass

    def get_metadata(self) -> CapabilityMetadata:
        """Generates typed metadata contract including JSON schemas."""
        return CapabilityMetadata(
            capability_id=self.capability_id,
            name=self.name,
            description=self.description,
            version=self.version,
            required_permissions=self.required_permissions,
            input_schema=self.input_model.model_json_schema(),
            output_schema=self.output_model.model_json_schema(),
            verification_metadata=self.verification_metadata,
            estimated_cost_usd=self.estimated_cost_usd
        )
