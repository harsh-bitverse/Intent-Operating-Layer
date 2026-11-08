"""
IOL Browser Execution Substrate.
Provides sandboxed, policy-guarded Playwright browser automation
for generic web observation, navigation, extraction, and authorized interactions.
"""

from backend.iol.browser.models import (
    BrowserAction,
    BrowserActionType,
    BrowserActionEffect,
    BrowserObservation,
    BrowserSessionInfo,
)
from backend.iol.browser.policy import BrowserPolicy
from backend.iol.browser.session import BrowserSessionManager, browser_session_manager
from backend.iol.browser.executor import BrowserActionExecutor, browser_executor

__all__ = [
    "BrowserAction",
    "BrowserActionType",
    "BrowserActionEffect",
    "BrowserObservation",
    "BrowserSessionInfo",
    "BrowserPolicy",
    "BrowserSessionManager",
    "browser_session_manager",
    "BrowserActionExecutor",
    "browser_executor",
]
