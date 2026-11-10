"""
Data models and contracts for the IOL Universal Model Provider Layer.
Defines provider types, functional roles, model capabilities, inference requests,
telemetry responses, and security-validated routing policies.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ProviderType(str, Enum):
    """Supported model provider engine types."""
    GEMINI = "gemini"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    VLLM = "vllm"
    LLAMA_CPP = "llama_cpp"
    OPENAI_COMPATIBLE = "openai_compatible"
    MOCK = "mock"


class FunctionalRole(str, Enum):
    """Specific IOL subsystem roles that require model intelligence."""
    INTENT_UNDERSTANDING = "intent_understanding"
    PLANNING = "planning"
    BROWSER_REASONING = "browser_reasoning"
    EXPERIENCE_SYNTHESIS = "experience_synthesis"
    KNOWLEDGE_EXTRACTION = "knowledge_extraction"
    VERIFICATION = "verification"


class ModelCapability(str, Enum):
    """Functional capabilities supported by specific models."""
    STRUCTURED_OUTPUT = "structured_output"
    JSON_MODE = "json_mode"
    TOOL_CALLING = "tool_calling"
    STREAMING = "streaming"
    MULTIMODAL = "multimodal"
    LOCAL_EXECUTION = "local_execution"
    REASONING_EFFORT = "reasoning_effort"


class InferenceRequest(BaseModel):
    """Universal model inference invocation request."""
    system_prompt: str
    user_content: str
    model: Optional[str] = None
    temperature: float = 0.2
    max_tokens: int = 2000
    require_json: bool = True
    json_schema: Optional[Dict[str, Any]] = None
    timeout_seconds: float = 15.0
    task_id: Optional[str] = None
    role: Optional[FunctionalRole] = None


class UsageMetadata(BaseModel):
    """Provider-reported and validated token consumption metrics."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    usage_type: str = "ACTUAL"  # "ACTUAL" | "SIMULATED"
    is_estimated: bool = False
    cost_estimate_usd: Optional[float] = None


class InferenceResponse(BaseModel):
    """Standardized response from any model provider."""
    raw_text: str
    parsed_json: Optional[Dict[str, Any]] = None
    usage: UsageMetadata
    latency_ms: float
    transport_ms: float
    inference_ms: Optional[float] = None
    request_id: Optional[str] = None
    model_name: str
    provider_id: str
    provider_type: ProviderType
    is_trusted_foundation_model: bool
    trust_reason: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ProviderConfig(BaseModel):
    """Configuration descriptor for a registered model provider instance."""
    provider_id: str
    provider_type: ProviderType
    display_name: str
    base_url: str
    api_key: Optional[str] = None
    default_model: str
    available_models: List[str] = Field(default_factory=list)
    capabilities: List[ModelCapability] = Field(default_factory=list)
    is_local: bool = False
    is_enabled: bool = True
    timeout_seconds: float = 15.0
    max_retries: int = 2

    def to_sanitized_dict(self) -> Dict[str, Any]:
        """Returns safe representation with API keys redacted for client/API exposure."""
        data = self.model_dump()
        has_key = bool(self.api_key)
        data.pop("api_key", None)
        data["has_api_key"] = has_key
        data["key_hint"] = f"••••{self.api_key[-4:]}" if (has_key and len(self.api_key or "") > 8) else ("Configured" if has_key else "None")
        return data


class RoutingPolicy(BaseModel):
    """Policy governing provider selection and fallback for a functional role."""
    role: FunctionalRole
    primary_provider_id: str
    fallback_provider_id: Optional[str] = None
    allow_cloud: bool = True
    allow_local: bool = True
    max_latency_ms: float = 30000.0
    require_structured_output: bool = True
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DiagnosticResult(BaseModel):
    """Connectivity and diagnostic health check result for a provider."""
    provider_id: str
    provider_type: ProviderType
    status: str  # "HEALTHY" | "DEGRADED" | "UNHEALTHY" | "BLOCKED"
    is_connected: bool
    latency_ms: Optional[float] = None
    discovered_models: List[str] = Field(default_factory=list)
    message: str = ""
    error_reason: Optional[str] = None
    checked_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
