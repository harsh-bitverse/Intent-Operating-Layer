"""
Capability Registry for IOL.
Provides registration, lookup, input validation, and discovery of capabilities.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ValidationError
from backend.iol.capabilities.base import BaseCapability, CapabilityMetadata, CapabilityResult, ExecutionContext


class CapabilityNotFoundError(Exception):
    pass


class CapabilityValidationError(Exception):
    pass


class CapabilityRegistry:
    """Registry maintaining active IOL capabilities."""

    def __init__(self):
        self._capabilities: Dict[str, BaseCapability] = {}

    def register(self, capability: BaseCapability) -> None:
        """Register a new capability implementation."""
        self._capabilities[capability.capability_id] = capability

    def get(self, capability_id: str) -> Optional[BaseCapability]:
        """Retrieve capability by ID."""
        return self._capabilities.get(capability_id)

    def list_capabilities(self) -> List[CapabilityMetadata]:
        """List metadata for all registered capabilities."""
        return [cap.get_metadata() for cap in self._capabilities.values()]

    def validate_input(self, capability_id: str, raw_params: Dict[str, Any]) -> BaseModel:
        """Validate input parameters against the capability's typed input model."""
        cap = self.get(capability_id)
        if not cap:
            raise CapabilityNotFoundError(f"Capability '{capability_id}' not found in registry.")

        try:
            return cap.input_model.model_validate(raw_params)
        except ValidationError as e:
            raise CapabilityValidationError(f"Invalid parameters for '{capability_id}': {e}") from e

    async def invoke(
        self,
        capability_id: str,
        params: Dict[str, Any],
        context: ExecutionContext
    ) -> CapabilityResult:
        """Validate input and execute capability."""
        cap = self.get(capability_id)
        if not cap:
            raise CapabilityNotFoundError(f"Capability '{capability_id}' not found in registry.")

        validated_params = self.validate_input(capability_id, params)
        return await cap.execute(validated_params, context)


capability_registry = CapabilityRegistry()
