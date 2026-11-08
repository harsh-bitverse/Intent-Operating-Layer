"""
Reusable Browser Automation Capabilities for IOL.
Exposes sandboxed Playwright navigation, extraction, and interaction to the IOL Capability Registry.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.iol.capabilities.base import BaseCapability, CapabilityResult, ExecutionContext
from backend.iol.browser.models import (
    BrowserAction,
    BrowserActionType,
    BrowserActionEffect,
    BrowserObservation,
)
from backend.iol.browser.executor import BrowserActionExecutor, browser_executor


class BrowserNavigateInput(BaseModel):
    url: str = Field(description="Target public HTTP/HTTPS URL to navigate to")
    timeout_ms: int = Field(default=15000, description="Navigation timeout in milliseconds")
    expected_origin: Optional[str] = Field(default=None, description="Expected origin domain for SSRF sanity check")


class BrowserNavigateOutput(BaseModel):
    url: str
    title: str
    status_code: int = 200
    text_snippet: str
    screenshot_path: Optional[str] = None
    screenshot_b64: Optional[str] = None
    accessible_elements: List[Dict[str, Any]] = Field(default_factory=list)
    is_blocked: bool = False
    blocker_reason: Optional[str] = None
    telemetry: Dict[str, Any] = Field(default_factory=dict)


class BrowserExtractInput(BaseModel):
    fields: Optional[List[str]] = Field(default=None, description="Specific fields or semantic keys to extract")
    selector: Optional[str] = Field(default=None, description="Optional container selector to scope extraction")


class BrowserExtractOutput(BaseModel):
    extracted_data: Dict[str, Any] = Field(default_factory=dict)
    url: str
    title: str
    evidence: Dict[str, Any] = Field(default_factory=dict)


class BrowserActionInput(BaseModel):
    action_type: str = Field(description="Action verb: click, fill, select, press, scroll, wait_for, handoff")
    selector: Optional[str] = Field(default=None, description="CSS or text locator")
    text: Optional[str] = Field(default=None, description="Text for fill or button text locator")
    value: Optional[str] = Field(default=None, description="Value for fill or select")
    key: Optional[str] = Field(default=None, description="Key name for press")
    timeout_ms: int = Field(default=15000, description="Action timeout in milliseconds")


class BrowserActionOutput(BaseModel):
    url: str
    title: str
    status_code: int = 200
    action_effect: str = "READ"
    is_blocked: bool = False
    blocker_reason: Optional[str] = None
    telemetry: Dict[str, Any] = Field(default_factory=dict)


class BrowserNavigateCapability(BaseCapability):
    capability_id = "browser.navigate"
    name = "Sandboxed Browser Navigation"
    description = "Navigates to an external public URL inside a tenant-isolated browser session with SSRF guards."
    version = "1.0.0"
    input_model = BrowserNavigateInput
    output_model = BrowserNavigateOutput
    required_permissions = ["network.browser.navigate"]
    verification_metadata = {
        "sandbox": "playwright_chromium",
        "ssrf_enforced": True,
        "isolation": "per_task_context",
    }

    async def execute(self, params: BaseModel, context: ExecutionContext) -> CapabilityResult:
        nav_params: BrowserNavigateInput = params  # type: ignore
        tenant_id = context.metadata.get("tenant_id", "default_tenant")
        task_id = context.task_id

        action = BrowserAction(
            action_type=BrowserActionType.GOTO,
            url=nav_params.url,
            timeout_ms=nav_params.timeout_ms,
            expected_origin=nav_params.expected_origin,
            rationale=f"Navigating to {nav_params.url} for task {task_id}",
        )

        obs: BrowserObservation = await browser_executor.execute_action(
            tenant_id=tenant_id,
            task_id=task_id,
            action=action,
            capture_screenshot=True,
        )

        if obs.is_blocked:
            return CapabilityResult(
                success=False,
                data={
                    "url": obs.url,
                    "title": obs.title,
                    "status_code": obs.status_code or 403,
                    "text_snippet": obs.text_content_snippet,
                    "is_blocked": True,
                    "blocker_reason": obs.blocker_reason,
                    "telemetry": obs.telemetry,
                },
                error_message=obs.blocker_reason,
                verification_score=0.0,
            )

        return CapabilityResult(
            success=True,
            data={
                "url": obs.url,
                "title": obs.title,
                "status_code": obs.status_code or 200,
                "text_snippet": obs.text_content_snippet,
                "screenshot_path": obs.screenshot_path,
                "screenshot_b64": obs.screenshot_b64,
                "accessible_elements": obs.accessible_elements,
                "is_blocked": False,
                "telemetry": obs.telemetry,
            },
            verification_score=1.0,
            verification_details={
                "provenance_url": obs.url,
                "observed_at": obs.observed_at,
                "elements_found": len(obs.accessible_elements),
            },
        )


class BrowserExtractCapability(BaseCapability):
    capability_id = "browser.extract"
    name = "Structured Browser Data Extraction"
    description = "Extracts structured metadata, headings, tables, or text facts from the current page session."
    version = "1.0.0"
    input_model = BrowserExtractInput
    output_model = BrowserExtractOutput
    required_permissions = ["network.browser.extract"]
    verification_metadata = {
        "sandbox": "playwright_chromium",
        "method": "dom_structure_analysis",
    }

    async def execute(self, params: BaseModel, context: ExecutionContext) -> CapabilityResult:
        ext_params: BrowserExtractInput = params  # type: ignore
        tenant_id = context.metadata.get("tenant_id", "default_tenant")
        task_id = context.task_id

        action = BrowserAction(
            action_type=BrowserActionType.EXTRACT,
            fields_to_extract=ext_params.fields,
            selector=ext_params.selector,
            rationale=f"Extracting structured DOM data for task {task_id}",
        )

        obs: BrowserObservation = await browser_executor.execute_action(
            tenant_id=tenant_id,
            task_id=task_id,
            action=action,
            capture_screenshot=False,
        )

        extracted = obs.extracted_data or {}
        return CapabilityResult(
            success=True,
            data={
                "extracted_data": extracted,
                "url": obs.url,
                "title": obs.title,
                "evidence": {
                    "source_url": obs.url,
                    "observed_at": obs.observed_at,
                    "title": obs.title,
                    "snippet": obs.text_content_snippet[:300],
                },
            },
            verification_score=1.0,
            verification_details={
                "source_url": obs.url,
                "fields_extracted": list(extracted.keys()),
            },
        )


class BrowserActionCapability(BaseCapability):
    capability_id = "browser.action"
    name = "Sandboxed Browser Interaction"
    description = "Executes schema-checked interaction verbs (click, fill, select, press, scroll) with approval gates."
    version = "1.0.0"
    input_model = BrowserActionInput
    output_model = BrowserActionOutput
    required_permissions = ["network.browser.action"]
    verification_metadata = {
        "sandbox": "playwright_chromium",
        "policy_enforced": True,
    }

    async def execute(self, params: BaseModel, context: ExecutionContext) -> CapabilityResult:
        act_params: BrowserActionInput = params  # type: ignore
        tenant_id = context.metadata.get("tenant_id", "default_tenant")
        task_id = context.task_id
        is_approved = context.metadata.get("is_approved", False)

        try:
            verb = BrowserActionType(act_params.action_type.lower())
        except ValueError:
            return CapabilityResult(
                success=False,
                error_message=f"Unsupported browser action verb: '{act_params.action_type}'.",
            )

        action = BrowserAction(
            action_type=verb,
            selector=act_params.selector,
            text=act_params.text,
            value=act_params.value,
            key=act_params.key,
            timeout_ms=act_params.timeout_ms,
        )

        obs: BrowserObservation = await browser_executor.execute_action(
            tenant_id=tenant_id,
            task_id=task_id,
            action=action,
            is_approved=is_approved,
            capture_screenshot=True,
        )

        if obs.is_blocked:
            return CapabilityResult(
                success=False,
                data={
                    "url": obs.url,
                    "title": obs.title,
                    "status_code": obs.status_code or 403,
                    "action_effect": obs.action_effect.value if obs.action_effect else "UNKNOWN",
                    "is_blocked": True,
                    "blocker_reason": obs.blocker_reason,
                    "telemetry": obs.telemetry,
                },
                error_message=obs.blocker_reason,
                verification_score=0.0,
            )

        return CapabilityResult(
            success=True,
            data={
                "url": obs.url,
                "title": obs.title,
                "status_code": obs.status_code or 200,
                "action_effect": obs.action_effect.value if obs.action_effect else "READ",
                "is_blocked": False,
                "telemetry": obs.telemetry,
            },
            verification_score=1.0,
            verification_details={
                "action_type": act_params.action_type,
                "effect": obs.action_effect.value if obs.action_effect else "READ",
            },
        )


def register_browser_capabilities(registry) -> None:
    """Registers all browser capabilities into the centralized IOL capability registry."""
    registry.register(BrowserNavigateCapability())
    registry.register(BrowserExtractCapability())
    registry.register(BrowserActionCapability())
