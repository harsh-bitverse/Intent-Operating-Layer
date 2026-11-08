"""
Action Execution Engine for IOL Browser Substrate.
Safely executes validated browser actions, enforces redirect SSRF checks, and extracts telemetry.
"""

import base64
from datetime import datetime, timezone
import logging
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Optional

from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from backend.iol.browser.models import (
    BrowserAction,
    BrowserActionEffect,
    BrowserActionType,
    BrowserObservation,
)
from backend.iol.browser.policy import BrowserPolicy, browser_policy
from backend.iol.browser.session import BrowserSessionManager, browser_session_manager

logger = logging.getLogger("iol.browser.executor")

SCREENSHOT_DIR = Path("docs/screenshots/browser")


class BrowserActionExecutor:
    """
    Executes schema-checked browser actions within tenant-isolated sessions.
    Captures telemetry, elements, text snippets, and provenance evidence.
    """

    def __init__(
        self,
        session_manager: BrowserSessionManager = browser_session_manager,
        policy: BrowserPolicy = browser_policy,
    ):
        self.session_manager = session_manager
        self.policy = policy
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    async def execute_action(
        self,
        tenant_id: str,
        task_id: str,
        action: BrowserAction,
        is_approved: bool = False,
        capture_screenshot: bool = True,
    ) -> BrowserObservation:
        """
        Executes a single validated browser action and returns a fresh BrowserObservation.
        """
        start_time = time.perf_counter()
        session = await self.session_manager.get_or_create_session(tenant_id, task_id)
        page = session.page

        # 1. Budget check
        can_proceed, budget_err = self.policy.check_step_budget(session.step_count)
        if not can_proceed:
            return BrowserObservation(
                url=page.url if not page.is_closed() else "about:blank",
                title="Step Budget Exceeded",
                observed_at=datetime.now(timezone.utc).isoformat(),
                is_blocked=True,
                blocker_reason=budget_err,
                navigation_history=session.navigation_history,
                telemetry={"step_count": session.step_count},
            )

        # 2. Action effect & approval check
        effect = self.policy.classify_action_effect(action)
        if self.policy.requires_approval(effect) and not is_approved:
            return BrowserObservation(
                url=page.url if not page.is_closed() else "about:blank",
                title="Action Approval Required",
                observed_at=datetime.now(timezone.utc).isoformat(),
                is_blocked=True,
                blocker_reason=f"Action '{action.action_type.value}' has effect '{effect.value}' and requires operator approval.",
                action_effect=effect,
                navigation_history=session.navigation_history,
                telemetry={"requires_approval": True, "effect": effect.value},
            )

        # 3. Action execution
        extracted_data: Optional[Dict[str, Any]] = None
        status_code = 200

        try:
            if action.action_type == BrowserActionType.GOTO:
                if not action.url:
                    raise ValueError("URL must be provided for goto action.")

                # Pre-navigation SSRF check
                is_safe, ssrf_err = self.policy.validate_navigation(action.url)
                if not is_safe:
                    return BrowserObservation(
                        url=action.url,
                        title="Navigation Blocked (SSRF)",
                        observed_at=datetime.now(timezone.utc).isoformat(),
                        is_blocked=True,
                        blocker_reason=ssrf_err,
                        action_effect=effect,
                        navigation_history=session.navigation_history,
                    )

                # Execute navigation
                response = await page.goto(
                    action.url,
                    wait_until="domcontentloaded",
                    timeout=action.timeout_ms,
                )
                if response:
                    status_code = response.status

                # Post-navigation redirect validation
                current_url = page.url
                is_redirect_safe, redirect_err = self.policy.validate_navigation(current_url)
                if not is_redirect_safe:
                    await self.session_manager.close_session(tenant_id, task_id)
                    return BrowserObservation(
                        url=current_url,
                        title="Redirect Blocked (SSRF)",
                        observed_at=datetime.now(timezone.utc).isoformat(),
                        is_blocked=True,
                        blocker_reason=f"Post-navigation redirect landed on prohibited destination: {redirect_err}",
                        action_effect=effect,
                        navigation_history=session.navigation_history,
                    )

                session.navigation_history.append(current_url)

            elif action.action_type == BrowserActionType.CLICK:
                if not action.selector and not action.text:
                    raise ValueError("Selector or text must be provided for click action.")
                try:
                    if action.selector:
                        await page.click(action.selector, timeout=action.timeout_ms)
                    elif action.text:
                        await page.get_by_text(action.text, exact=False).first.click(timeout=action.timeout_ms)
                except Exception as click_err:
                    logger.warning(f"Initial click failed: {click_err}. Attempting retry/recovery...")
                    await page.wait_for_timeout(400)
                    if action.selector:
                        await page.locator(action.selector).first.click(timeout=action.timeout_ms)
                    elif action.text:
                        await page.get_by_role("button", name=action.text).click(timeout=action.timeout_ms)
                await page.wait_for_timeout(500)

            elif action.action_type == BrowserActionType.FILL:
                if not action.selector:
                    raise ValueError("Selector must be provided for fill action.")
                val = action.value or action.text or ""
                try:
                    await page.fill(action.selector, val, timeout=action.timeout_ms)
                except Exception as fill_err:
                    logger.warning(f"Initial fill failed: {fill_err}. Attempting retry/recovery...")
                    await page.wait_for_timeout(400)
                    await page.locator(action.selector).first.fill(val, timeout=action.timeout_ms)

            elif action.action_type == BrowserActionType.SELECT:
                if not action.selector:
                    raise ValueError("Selector must be provided for select action.")
                val = action.value or action.text or ""
                try:
                    await page.select_option(action.selector, value=val, timeout=action.timeout_ms)
                except Exception:
                    try:
                        await page.select_option(action.selector, label=val, timeout=action.timeout_ms)
                    except Exception:
                        await page.wait_for_timeout(400)
                        await page.locator(action.selector).first.select_option(value=val, timeout=action.timeout_ms)

            elif action.action_type == BrowserActionType.PRESS:
                key = action.key or "Enter"
                await page.keyboard.press(key)
                await page.wait_for_timeout(500)

            elif action.action_type == BrowserActionType.SCROLL:
                await page.evaluate("window.scrollBy(0, 600)")
                await page.wait_for_timeout(300)

            elif action.action_type == BrowserActionType.WAIT_FOR:
                if action.selector:
                    await page.wait_for_selector(action.selector, timeout=action.timeout_ms)
                else:
                    await page.wait_for_timeout(1000)

            elif action.action_type == BrowserActionType.EXTRACT:
                # Perform structured extraction from page DOM
                extracted_data = await self._extract_page_data(page, action.fields_to_extract)

            elif action.action_type == BrowserActionType.HANDOFF:
                extracted_data = {
                    "handoff_url": page.url,
                    "handoff_reason": action.rationale or "User interactive takeover required.",
                }

        except PlaywrightTimeoutError as e:
            logger.warning(f"Browser action timeout ({action.action_type}): {e}")
            return BrowserObservation(
                url=page.url if not page.is_closed() else "about:blank",
                title="Action Timeout",
                observed_at=datetime.now(timezone.utc).isoformat(),
                is_blocked=True,
                blocker_reason=f"Action timed out after {action.timeout_ms}ms.",
                action_effect=effect,
                navigation_history=session.navigation_history,
            )
        except Exception as e:
            logger.error(f"Browser action error: {e}", exc_info=True)
            return BrowserObservation(
                url=page.url if not page.is_closed() else "about:blank",
                title="Action Error",
                observed_at=datetime.now(timezone.utc).isoformat(),
                is_blocked=True,
                blocker_reason=f"Action failed with error: {str(e)}",
                action_effect=effect,
                navigation_history=session.navigation_history,
            )

        session.touch()

        # 4. Gather observation data
        url = page.url
        try:
            title = await page.title()
        except Exception:
            title = ""

        # Extract bounded text content
        try:
            body_text = await page.inner_text("body", timeout=3000)
            text_snippet = " ".join(body_text.split())[:4000]
        except Exception:
            text_snippet = ""

        # Defang prompt injection and neutralize malicious tokens in untrusted content
        title = self.policy.sanitize_untrusted_text(title)
        text_snippet = self.policy.sanitize_untrusted_text(text_snippet)

        # Extract accessible interactive elements
        elements = await self._discover_accessible_elements(page)

        # Detect blockers (Cloudflare, CAPTCHA, 403)
        is_blocked, blocker_reason = self.policy.detect_blockers(title, text_snippet)

        # Capture screenshot if requested and not blocked by policy
        screenshot_path = None
        screenshot_b64 = None
        if capture_screenshot and not page.is_closed():
            try:
                fname = f"browser_{session.session_id}_{session.step_count}.png"
                full_path = SCREENSHOT_DIR / fname
                raw_bytes = await page.screenshot(type="png", full_page=False)
                with open(full_path, "wb") as f:
                    f.write(raw_bytes)
                screenshot_path = str(full_path).replace("\\", "/")
                # Create compact thumbnail base64 for direct UI embedding
                screenshot_b64 = f"data:image/png;base64,{base64.b64encode(raw_bytes).decode('utf-8')[:50000]}"
            except Exception as e:
                logger.debug(f"Failed to capture screenshot: {e}")

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return BrowserObservation(
            url=url,
            title=title,
            status_code=status_code,
            observed_at=datetime.now(timezone.utc).isoformat(),
            text_content_snippet=text_snippet,
            accessible_elements=elements,
            screenshot_path=screenshot_path,
            screenshot_b64=screenshot_b64,
            navigation_history=list(session.navigation_history),
            is_blocked=is_blocked,
            blocker_reason=blocker_reason,
            extracted_data=extracted_data,
            action_effect=effect,
            telemetry={
                "duration_ms": duration_ms,
                "step_count": session.step_count,
                "session_id": session.session_id,
            },
        )

    async def _discover_accessible_elements(self, page) -> List[Dict[str, Any]]:
        """
        Extracts key interactive elements (buttons, links, inputs) with accessible roles and labels.
        """
        try:
            elements_data = await page.evaluate(
                """() => {
                    const results = [];
                    const interactive = document.querySelectorAll('button, a[href], input, select, textarea, h1, h2');
                    let count = 0;
                    for (const el of interactive) {
                        if (count >= 35) break;
                        const rect = el.getBoundingClientRect();
                        if (rect.width === 0 || rect.height === 0) continue;
                        
                        const tag = el.tagName.toLowerCase();
                        let role = el.getAttribute('role') || tag;
                        let text = (el.innerText || el.value || el.getAttribute('aria-label') || el.getAttribute('placeholder') || '').trim();
                        text = text.replace(/\\s+/g, ' ').substring(0, 100);
                        
                        let selector = '';
                        if (el.id) {
                            selector = '#' + el.id;
                        } else if (el.getAttribute('data-testid')) {
                            selector = '[data-testid="' + el.getAttribute('data-testid') + '"]';
                        } else if (el.name) {
                            selector = tag + '[name="' + el.name + '"]';
                        } else if (tag === 'a' && el.getAttribute('href')) {
                            selector = 'a[href="' + el.getAttribute('href') + '"]';
                        } else {
                            selector = tag;
                        }

                        let options = [];
                        if (tag === 'select' && el.options) {
                            options = Array.from(el.options).map(o => ({ value: o.value, text: o.text.trim() }));
                        }

                        results.push({
                            tag: tag,
                            role: role,
                            text: text,
                            selector: selector,
                            href: el.getAttribute('href') || null,
                            input_type: el.type || null,
                            checked: !!el.checked,
                            options: options
                        });
                        count++;
                    }
                    return results;
                }"""
            )
            return elements_data or []
        except Exception as e:
            logger.debug(f"Element discovery error: {e}")
            return []

    async def _extract_page_data(self, page, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Extracts structured semantic facts from headings, metadata, and key containers.
        """
        try:
            data = await page.evaluate(
                """() => {
                    const getMeta = (name) => {
                        const el = document.querySelector(`meta[name="${name}"], meta[property="${name}"]`);
                        return el ? el.getAttribute('content') : null;
                    };
                    const headings = Array.from(document.querySelectorAll('h1, h2')).map(h => h.innerText.trim()).filter(Boolean).slice(0, 5);
                    const links = Array.from(document.querySelectorAll('a[href^="http"]')).map(a => ({
                        text: a.innerText.trim(),
                        href: a.href
                    })).filter(l => l.text.length > 2).slice(0, 8);

                    return {
                        title: document.title,
                        description: getMeta('description') || getMeta('og:description'),
                        author: getMeta('author'),
                        headings: headings,
                        external_links: links
                    };
                }"""
            )
            return data or {}
        except Exception as e:
            logger.debug(f"Structured extraction error: {e}")
            return {}


# Global browser executor instance
browser_executor = BrowserActionExecutor()
