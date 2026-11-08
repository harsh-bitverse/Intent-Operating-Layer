"""
Data models and contracts for IOL Browser Substrate.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BrowserActionType(str, Enum):
    GOTO = "goto"
    SNAPSHOT = "snapshot"
    CLICK = "click"
    FILL = "fill"
    SELECT = "select"
    PRESS = "press"
    SCROLL = "scroll"
    EXTRACT = "extract"
    WAIT_FOR = "wait_for"
    HANDOFF = "handoff"


class BrowserActionEffect(str, Enum):
    READ = "READ"
    LOCAL_DRAFT = "LOCAL_DRAFT"
    EXTERNAL_WRITE = "EXTERNAL_WRITE"
    PAYMENT_OR_ORDER = "PAYMENT_OR_ORDER"
    DESTRUCTIVE = "DESTRUCTIVE"


class BrowserAction(BaseModel):
    """
    Validated schema for a browser action request.
    Arbitrary JS execution or eval strings are strictly disallowed.
    """
    action_type: BrowserActionType
    url: Optional[str] = Field(None, description="Target URL for goto navigation")
    selector: Optional[str] = Field(None, description="CSS or text/role locator")
    text: Optional[str] = Field(None, description="Text to type or locate")
    value: Optional[str] = Field(None, description="Value for fill or select operations")
    key: Optional[str] = Field(None, description="Keyboard key name for press operations")
    timeout_ms: int = Field(15000, description="Step timeout in milliseconds")
    expected_origin: Optional[str] = Field(None, description="Expected domain origin for safety check")
    expected_text: Optional[str] = Field(None, description="Precondition text expected on element")
    fields_to_extract: Optional[List[str]] = Field(None, description="Fields to extract when action is extract")
    rationale: Optional[str] = Field(None, description="Operational rationale for audit logging")


class BrowserObservation(BaseModel):
    """
    Structured observation captured from the browser runtime after action execution.
    """
    url: str
    title: str
    status_code: Optional[int] = 200
    observed_at: str
    text_content_snippet: str = ""
    accessible_elements: List[Dict[str, Any]] = Field(default_factory=list)
    screenshot_path: Optional[str] = None
    screenshot_b64: Optional[str] = None
    navigation_history: List[str] = Field(default_factory=list)
    is_blocked: bool = False
    blocker_reason: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None
    action_effect: Optional[BrowserActionEffect] = None
    telemetry: Dict[str, Any] = Field(default_factory=dict)


class BrowserSessionInfo(BaseModel):
    """
    Metadata describing an active sandboxed browser session.
    """
    session_id: str
    tenant_id: str
    task_id: str
    created_at: str
    last_active_at: str
    step_count: int = 0
    is_active: bool = True
