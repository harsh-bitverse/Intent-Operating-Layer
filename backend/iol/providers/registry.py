"""
Provider Registry for Intent Operating Layer.
Manages provider adapters, secure credential resolution, runtime health checks,
and dynamic model discovery across cloud APIs and local runtimes.
"""

from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.iol.providers.adapters.base import BaseProviderAdapter
from backend.iol.providers.adapters.gemini import GeminiProviderAdapter
from backend.iol.providers.adapters.openai import OpenAIProviderAdapter
from backend.iol.providers.adapters.anthropic import AnthropicProviderAdapter
from backend.iol.providers.adapters.ollama import OllamaProviderAdapter
from backend.iol.providers.adapters.openai_compatible import OpenAICompatibleProviderAdapter
from backend.iol.providers.adapters.mock import MockProviderAdapter
from backend.iol.providers.models import (
    DiagnosticResult,
    ModelCapability,
    ProviderConfig,
    ProviderType,
)
from backend.iol.providers.ssrf import validate_provider_endpoint

logger = logging.getLogger("iol.providers.registry")


class ProviderRegistry:
    """Central registry and lifecycle manager for all model providers."""

    def __init__(self):
        self._adapters: Dict[str, BaseProviderAdapter] = {}
        self._configs: Dict[str, ProviderConfig] = {}
        self._initialize_from_environment()

    def _initialize_from_environment(self):
        """Initializes standard provider adapters from environment variables."""
        # Ensure .env is read once at registry init
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except Exception:
            pass

        # 1. Google Gemini Cloud Provider
        gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        gemini_model = os.environ.get("IOL_EXP_MODEL", "gemini-3.8-flash")
        gemini_cfg = ProviderConfig(
            provider_id="gemini",
            provider_type=ProviderType.GEMINI,
            display_name="Google Gemini API",
            base_url="https://generativelanguage.googleapis.com/v1beta",
            api_key=gemini_key,
            default_model=gemini_model,
            available_models=["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-4-argon", "gemini-2.5-flash"],
            capabilities=[ModelCapability.STRUCTURED_OUTPUT, ModelCapability.JSON_MODE, ModelCapability.MULTIMODAL, ModelCapability.STREAMING],
            is_local=False,
            is_enabled=bool(gemini_key),
        )
        self.register_provider(gemini_cfg)

        # 2. OpenAI Cloud Provider
        openai_key = os.environ.get("OPENAI_API_KEY")
        openai_model = os.environ.get("IOL_EXP_MODEL", "gpt-4o-mini")
        openai_cfg = ProviderConfig(
            provider_id="openai",
            provider_type=ProviderType.OPENAI,
            display_name="OpenAI Platform",
            base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            api_key=openai_key,
            default_model=openai_model,
            available_models=["gpt-4o-mini", "gpt-4o", "o1", "o3-mini"],
            capabilities=[ModelCapability.STRUCTURED_OUTPUT, ModelCapability.JSON_MODE, ModelCapability.TOOL_CALLING],
            is_local=False,
            is_enabled=bool(openai_key),
        )
        self.register_provider(openai_cfg)

        # 3. Anthropic Cloud Provider
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        anthropic_cfg = ProviderConfig(
            provider_id="anthropic",
            provider_type=ProviderType.ANTHROPIC,
            display_name="Anthropic Claude",
            base_url="https://api.anthropic.com/v1",
            api_key=anthropic_key,
            default_model="claude-3-5-haiku-20241022",
            available_models=["claude-3-5-haiku-20241022", "claude-3-5-sonnet-20241022", "claude-3-opus-20240229"],
            capabilities=[ModelCapability.STRUCTURED_OUTPUT, ModelCapability.JSON_MODE, ModelCapability.MULTIMODAL],
            is_local=False,
            is_enabled=bool(anthropic_key),
        )
        self.register_provider(anthropic_cfg)

        # 4. Ollama Local Runtime Provider
        ollama_url = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
        ollama_cfg = ProviderConfig(
            provider_id="ollama",
            provider_type=ProviderType.OLLAMA,
            display_name="Ollama Local Daemon",
            base_url=ollama_url,
            default_model="llama3.2:1b",
            available_models=["llama3.2:1b", "qwen2.5:0.5b", "qwen2.5:1.5b", "qwen2.5:3b"],
            capabilities=[ModelCapability.STRUCTURED_OUTPUT, ModelCapability.JSON_MODE, ModelCapability.LOCAL_EXECUTION],
            is_local=True,
            is_enabled=True,
        )
        self.register_provider(ollama_cfg)

        # 5. Deterministic Test Mock Provider
        mock_cfg = ProviderConfig(
            provider_id="mock",
            provider_type=ProviderType.MOCK,
            display_name="Deterministic Test Synthesizer",
            base_url="mock://iol",
            default_model="iol-test-synthesizer-v1",
            available_models=["iol-test-synthesizer-v1"],
            capabilities=[ModelCapability.STRUCTURED_OUTPUT, ModelCapability.JSON_MODE],
            is_local=True,
            is_enabled=True,
        )
        self.register_provider(mock_cfg)

    def register_provider(self, config: ProviderConfig) -> BaseProviderAdapter:
        """Registers or updates a provider adapter after validating SSRF safety."""
        if config.provider_type != ProviderType.MOCK:
            is_valid, msg = validate_provider_endpoint(config.base_url)
            if not is_valid:
                raise ValueError(f"Provider '{config.provider_id}' endpoint validation failed: {msg}")

        self._configs[config.provider_id] = config

        if config.provider_type == ProviderType.GEMINI:
            adapter = GeminiProviderAdapter(config)
        elif config.provider_type == ProviderType.OPENAI:
            adapter = OpenAIProviderAdapter(config)
        elif config.provider_type == ProviderType.ANTHROPIC:
            adapter = AnthropicProviderAdapter(config)
        elif config.provider_type == ProviderType.OLLAMA:
            adapter = OllamaProviderAdapter(config)
        elif config.provider_type in (ProviderType.VLLM, ProviderType.LLAMA_CPP, ProviderType.OPENAI_COMPATIBLE):
            adapter = OpenAICompatibleProviderAdapter(config)
        elif config.provider_type == ProviderType.MOCK:
            adapter = MockProviderAdapter(config)
        else:
            adapter = OpenAICompatibleProviderAdapter(config)

        self._adapters[config.provider_id] = adapter
        return adapter

    def get_adapter(self, provider_id: str) -> Optional[BaseProviderAdapter]:
        """Returns the registered adapter for a provider ID."""
        return self._adapters.get(provider_id)

    def get_config(self, provider_id: str) -> Optional[ProviderConfig]:
        """Returns configuration for a provider ID."""
        return self._configs.get(provider_id)

    def list_providers(self, sanitized: bool = True) -> List[Dict[str, Any]]:
        """Lists all registered providers. Always sanitized by default to protect secrets."""
        results = []
        for pid, cfg in self._configs.items():
            if sanitized:
                results.append(cfg.to_sanitized_dict())
            else:
                results.append(cfg.model_dump())
        return results

    async def test_provider(self, provider_id: str) -> DiagnosticResult:
        """Runs health check and model discovery on the requested provider."""
        adapter = self.get_adapter(provider_id)
        if not adapter:
            return DiagnosticResult(
                provider_id=provider_id,
                provider_type=ProviderType.OPENAI_COMPATIBLE,
                status="UNHEALTHY",
                is_connected=False,
                message=f"Provider '{provider_id}' is not registered",
                error_reason="NOT_REGISTERED",
            )
        return await adapter.check_health()

    def discover_local_disk_models(self) -> List[Dict[str, Any]]:
        """Scans local ~/.ollama model weights on disk to report pre-installed assets."""
        models: List[Dict[str, Any]] = []
        try:
            home = Path.home()
            manifests_root = home / ".ollama" / "models" / "manifests"
            blobs_root = home / ".ollama" / "models" / "blobs"
            if not manifests_root.exists():
                return models

            for f in manifests_root.rglob("*"):
                if f.is_file() and not f.is_symlink():
                    try:
                        rel = f.relative_to(manifests_root).parts
                        if len(rel) >= 2:
                            tag = rel[-1]
                            model_name = rel[-2]
                            content = json.loads(f.read_text(encoding="utf-8", errors="replace"))
                            size = 0
                            for layer in content.get("layers", []):
                                if layer.get("mediaType") == "application/vnd.ollama.image.model":
                                    size = layer.get("size", 0)
                                    break
                            models.append({
                                "model_id": f"{model_name}:{tag}",
                                "name": model_name,
                                "tag": tag,
                                "size_bytes": size,
                                "size_mb": round(size / (1024 * 1024), 1),
                                "manifest_file": str(f.name),
                            })
                    except Exception:
                        continue
        except Exception as e:
            logger.debug(f"Error discovering local models: {e}")
        return models


# Global singleton instance
provider_registry = ProviderRegistry()
