"""
Security and Action Policy Engine for IOL Browser Substrate.
Enforces SSRF protections, step budgets, action classification, and approval requirements.
"""

import logging
import re
import urllib.parse
from typing import Optional, Tuple
from backend.iol.browser.models import BrowserAction, BrowserActionEffect, BrowserActionType
from backend.iol.core.security import validate_url_safety, SSRFSecurityError

logger = logging.getLogger("iol.browser.policy")

MAX_STEPS_PER_SESSION = 10
DEFAULT_ACTION_TIMEOUT_MS = 20000
MAX_SNIPPET_LENGTH = 5000

PAYMENT_KEYWORDS = {"pay", "purchase", "checkout", "buy", "order", "subscribe", "charge"}
DESTRUCTIVE_KEYWORDS = {"delete", "destroy", "terminate", "remove", "drop", "wipe"}
EXTERNAL_WRITE_KEYWORDS = {"submit", "send email", "send message", "confirm booking", "publish", "post comment"}

INJECTION_TOKENS = (
    "<|im_start|>",
    "<|im_end|>",
    "<|system|>",
    "<|user|>",
    "<|assistant|>",
    "<|prompt|>",
    "[INST]",
    "[/INST]",
    "<<SYS>>",
    "<</SYS>>",
    "<s>",
    "</s>",
)

ADVERSARIAL_PHRASES = (
    "ignore previous instructions",
    "ignore all previous instructions",
    "ignore prior instructions",
    "disregard previous instructions",
    "disregard all prior instructions",
    "forget your previous instructions",
    "forget your instructions",
    "system override",
    "you are now an unfiltered",
    "developer mode enabled",
    "bypass safety filters",
)


class BrowserPolicy:
    """Enforces safety, SSRF constraints, prompt-injection defenses, and action authorizations."""

    def sanitize_untrusted_text(self, text: Optional[str]) -> str:
        """
        Sanitizes untrusted DOM text or titles before feeding downstream to models or telemetry.
        Defangs model control tokens, system override instructions, and raw control characters.
        """
        if not text:
            return ""

        # 1. Strip null bytes and control chars (preserve standard whitespace)
        cleaned = "".join(ch for ch in text if ch in ("\n", "\r", "\t") or (ord(ch) >= 32 and ord(ch) != 127))

        # 2. Defang known delimiter/control tokens
        for token in INJECTION_TOKENS:
            if token in cleaned:
                cleaned = cleaned.replace(token, f"[DEFANGED_TOKEN:{token.strip('<>[]')}]")

        # 3. Neutralize adversarial prompt-override phrases (case-insensitive)
        for phrase in ADVERSARIAL_PHRASES:
            pattern = re.compile(re.escape(phrase), re.IGNORECASE)
            cleaned = pattern.sub("[FILTERED_PROMPT_INJECTION]", cleaned)

        return cleaned

    def __init__(
        self,
        max_steps: int = MAX_STEPS_PER_SESSION,
        max_timeout_ms: int = DEFAULT_ACTION_TIMEOUT_MS,
    ):
        self.max_steps = max_steps
        self.max_timeout_ms = max_timeout_ms

    def validate_navigation(self, url: str) -> Tuple[bool, Optional[str]]:
        """
        Validates whether target URL is permissible under strict SSRF policy.
        """
        if not url:
            return False, "Target URL cannot be empty."

        is_safe, error = validate_url_safety(url)
        if not is_safe:
            return False, f"Navigation blocked by SSRF policy: {error}"

        return True, None

    def classify_action_effect(self, action: BrowserAction) -> BrowserActionEffect:
        """
        Determines the potential impact and side-effect tier of a browser action.
        """
        if action.action_type in (
            BrowserActionType.GOTO,
            BrowserActionType.SNAPSHOT,
            BrowserActionType.SCROLL,
            BrowserActionType.WAIT_FOR,
            BrowserActionType.EXTRACT,
        ):
            return BrowserActionEffect.READ

        if action.action_type in (BrowserActionType.FILL, BrowserActionType.SELECT):
            # Check if entering payment or sensitive credentials
            selector_lower = (action.selector or "").lower()
            if any(k in selector_lower for k in ("card", "cvv", "pan", "expiry", "password", "pin")):
                return BrowserActionEffect.PAYMENT_OR_ORDER
            return BrowserActionEffect.LOCAL_DRAFT

        if action.action_type == BrowserActionType.CLICK:
            selector_lower = (action.selector or "").lower()
            text_lower = (action.text or "").lower()
            combined = f"{selector_lower} {text_lower}"

            if any(k in combined for k in PAYMENT_KEYWORDS):
                return BrowserActionEffect.PAYMENT_OR_ORDER
            if any(k in combined for k in DESTRUCTIVE_KEYWORDS):
                return BrowserActionEffect.DESTRUCTIVE
            if any(k in combined for k in EXTERNAL_WRITE_KEYWORDS):
                return BrowserActionEffect.EXTERNAL_WRITE
            return BrowserActionEffect.READ

        if action.action_type == BrowserActionType.HANDOFF:
            return BrowserActionEffect.READ

        return BrowserActionEffect.READ

    def requires_approval(self, effect: BrowserActionEffect) -> bool:
        """
        Returns True if the action effect tier mandates operator or user approval.
        """
        return effect in (
            BrowserActionEffect.EXTERNAL_WRITE,
            BrowserActionEffect.PAYMENT_OR_ORDER,
            BrowserActionEffect.DESTRUCTIVE,
        )

    def check_step_budget(self, current_steps: int) -> Tuple[bool, Optional[str]]:
        """
        Guards against infinite browsing loops or runaway step budgets.
        """
        if current_steps >= self.max_steps:
            return False, f"Browser session exceeded maximum step budget of {self.max_steps} steps."
        return True, None

    def detect_blockers(self, title: str, content: str) -> Tuple[bool, Optional[str]]:
        """
        Detects anti-bot, CAPTCHA, or rate-limiting blockers on the visited page.
        """
        combined = f"{title} {content[:2000]}".lower()
        if "cloudflare" in combined and ("attention required" in combined or "turnstile" in combined or "challenge" in combined):
            return True, "Cloudflare bot challenge or verification wall encountered."
        if "captcha" in combined or "verify you are human" in combined:
            return True, "CAPTCHA verification requested by target site."
        if "access denied" in combined or "403 forbidden" in combined:
            return True, "Access Denied / 403 Forbidden on destination page."
        return False, None


# Global browser policy instance
browser_policy = BrowserPolicy()
