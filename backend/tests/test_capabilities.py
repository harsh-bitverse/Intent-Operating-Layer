"""
Tests for IOL Capability Interface and Registry.
Validates typed input schemas, output schemas, validation errors, and execution.
"""

import pytest
from pydantic import BaseModel, Field
from backend.iol.capabilities.base import BaseCapability, CapabilityResult, ExecutionContext
from backend.iol.capabilities.registry import (
    CapabilityNotFoundError, CapabilityRegistry, CapabilityValidationError
)


class DummyInput(BaseModel):
    query: str = Field(..., min_length=2)
    count: int = Field(default=5, ge=1)


class DummyOutput(BaseModel):
    items: list[str]


class DummyCapability(BaseCapability):
    capability_id = "test.dummy_search"
    name = "Dummy Search Capability"
    description = "Test capability returning mock items."
    input_model = DummyInput
    output_model = DummyOutput
    required_permissions = ["TEST_PERMISSION"]
    verification_metadata = {"deterministic": True}

    async def execute(self, params: DummyInput, context: ExecutionContext) -> CapabilityResult:
        results = [f"{params.query}_{i}" for i in range(params.count)]
        return CapabilityResult(
            success=True,
            data=DummyOutput(items=results).model_dump(),
            verification_score=1.0
        )


@pytest.mark.asyncio
async def test_capability_registry():
    registry = CapabilityRegistry()
    cap = DummyCapability()
    registry.register(cap)

    # Retrieval and discovery
    meta_list = registry.list_capabilities()
    assert len(meta_list) == 1
    assert meta_list[0].capability_id == "test.dummy_search"
    assert "query" in meta_list[0].input_schema["properties"]

    # Input validation success
    validated = registry.validate_input("test.dummy_search", {"query": "robotics", "count": 3})
    assert validated.query == "robotics"
    assert validated.count == 3

    # Input validation failure
    with pytest.raises(CapabilityValidationError):
        registry.validate_input("test.dummy_search", {"query": "a"})  # min_length=2

    # Capability not found
    with pytest.raises(CapabilityNotFoundError):
        registry.validate_input("nonexistent.capability", {})

    # Invocation
    ctx = ExecutionContext(task_id="task_123", step_id="step_1")
    res = await registry.invoke("test.dummy_search", {"query": "vision", "count": 2}, ctx)
    assert res.success is True
    assert res.data["items"] == ["vision_0", "vision_1"]
    assert res.verification_score == 1.0
