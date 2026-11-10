"""
Base Provider Adapter Interface for the Universal Model Provider Layer.
All model provider adapters implement this contract.
"""

from abc import ABC, abstractmethod
import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple
import urllib.request
import urllib.error

from backend.iol.providers.models import (
    DiagnosticResult,
    InferenceRequest,
    InferenceResponse,
    ModelCapability,
    ProviderConfig,
    ProviderType,
    UsageMetadata,
)
from backend.iol.providers.ssrf import validate_provider_endpoint

logger = logging.getLogger("iol.providers.adapter")


class BaseProviderAdapter(ABC):
    """Abstract interface for all foundation model provider adapters."""

    def __init__(self, config: ProviderConfig):
        self.config = config
        self._validate_config()

    def _validate_config(self):
        """Enforces SSRF boundary check on provider base_url."""
        if self.config.provider_type == ProviderType.MOCK:
            return
        is_valid, msg = validate_provider_endpoint(self.config.base_url)
        if not is_valid:
            logger.warning(f"Provider {self.config.provider_id} endpoint validation warning: {msg}")

    def _get_opener(self) -> urllib.request.OpenerDirector:
        """Returns proxy-bypassing opener for loopback, or default opener for cloud."""
        if self.config.is_local or any(h in self.config.base_url for h in ["127.0.0.1", "localhost", "::1"]):
            return urllib.request.build_opener(urllib.request.ProxyHandler({}))
        return urllib.request.build_opener()

    @abstractmethod
    async def check_health(self) -> DiagnosticResult:
        """Performs non-destructive health and connectivity probe."""
        pass

    @abstractmethod
    async def discover_models(self) -> List[str]:
        """Discovers available models from provider API or local runtime."""
        pass

    @abstractmethod
    async def execute_inference(self, request: InferenceRequest) -> InferenceResponse:
        """Executes structured or text completion according to the universal contract."""
        pass

    def _clean_json_text(self, text: str) -> str:
        """Strips markdown code fences (```json ... ```) from model completion text."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            parts = cleaned.split("\n", 1)
            if len(parts) > 1:
                cleaned = parts[1].rsplit("```", 1)[0].strip()
        return cleaned

    def _parse_json_safely(self, text: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Parses JSON text into a dict, returning (dict, error_string)."""
        cleaned = self._clean_json_text(text)
        try:
            return json.loads(cleaned), None
        except Exception as e:
            return None, f"JSON parse error: {e}"
