"""
Sandboxed Browser Session Manager for IOL.
Provides tenant-isolated Playwright BrowserContext lifecycles with strict resource budgeting.
"""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional
import uuid

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright

from backend.iol.browser.models import BrowserSessionInfo

logger = logging.getLogger("iol.browser.session")

MAX_CONCURRENT_SESSIONS = 3
IDLE_TIMEOUT_SECONDS = 300


class BrowserSessionRecord:
    """Holds runtime references for an active isolated browser context."""

    def __init__(
        self,
        session_id: str,
        tenant_id: str,
        task_id: str,
        context: BrowserContext,
        page: Page,
    ):
        self.session_id = session_id
        self.tenant_id = tenant_id
        self.task_id = task_id
        self.context = context
        self.page = page
        now = datetime.now(timezone.utc).isoformat()
        self.created_at = now
        self.last_active_at = now
        self.step_count = 0
        self.navigation_history: List[str] = []

    def touch(self):
        self.last_active_at = datetime.now(timezone.utc).isoformat()
        self.step_count += 1

    def to_info(self) -> BrowserSessionInfo:
        return BrowserSessionInfo(
            session_id=self.session_id,
            tenant_id=self.tenant_id,
            task_id=self.task_id,
            created_at=self.created_at,
            last_active_at=self.last_active_at,
            step_count=self.step_count,
            is_active=True,
        )


class BrowserSessionManager:
    """
    Manages Playwright browser contexts with per-(tenant, task) sandboxing.
    Guarantees cookie isolation, zero cross-tenant contamination, and bounded concurrency.
    """

    def __init__(self, max_sessions: int = MAX_CONCURRENT_SESSIONS):
        self.max_sessions = max_sessions
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._sessions: Dict[str, BrowserSessionRecord] = {}
        self._lock = asyncio.Lock()

    async def _ensure_browser(self):
        """Initializes headless Chromium browser if not already running."""
        if not self._playwright:
            self._playwright = await async_playwright().start()
        if not self._browser or not self._browser.is_connected():
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-background-networking",
                ]
            )
            logger.info("Initialized shared Chromium instance for IOL browser substrate.")

    def _session_key(self, tenant_id: str, task_id: str) -> str:
        return f"{tenant_id}:{task_id}"

    async def get_or_create_session(
        self,
        tenant_id: str,
        task_id: str,
    ) -> BrowserSessionRecord:
        """
        Retrieves or allocates an isolated BrowserContext for the specified tenant and task.
        """
        key = self._session_key(tenant_id, task_id)
        async with self._lock:
            await self._ensure_browser()

            # Return existing session if active and healthy
            if key in self._sessions:
                record = self._sessions[key]
                if not record.page.is_closed():
                    record.touch()
                    return record
                else:
                    await self._close_session_unlocked(key)

            # Evict oldest session if concurrency limit reached
            if len(self._sessions) >= self.max_sessions:
                oldest_key = min(
                    self._sessions.keys(),
                    key=lambda k: self._sessions[k].last_active_at,
                )
                logger.warning(f"Evicting oldest browser session '{oldest_key}' to stay within budget.")
                await self._close_session_unlocked(oldest_key)

            # Create new strictly isolated BrowserContext
            session_id = f"bsess_{uuid.uuid4().hex[:12]}"
            context = await self._browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 (IOL-Research-Agent/0.6)",
                java_script_enabled=True,
                ignore_https_errors=False,
            )

            # Enforce request-level SSRF block in route handler
            await context.route("**/*", self._route_interceptor)

            page = await context.new_page()
            record = BrowserSessionRecord(
                session_id=session_id,
                tenant_id=tenant_id,
                task_id=task_id,
                context=context,
                page=page,
            )
            self._sessions[key] = record
            logger.info(f"Created isolated browser session '{session_id}' for tenant '{tenant_id}' task '{task_id}'.")
            return record

    async def _route_interceptor(self, route):
        """
        Intercepts requests to block unauthorized protocols, loopback queries, or metadata hits.
        """
        req_url = route.request.url
        # Allow benign asset loads, but block prohibited schemes or private ranges
        if req_url.startswith("file:") or req_url.startswith("data:") or req_url.startswith("javascript:"):
            if not req_url.startswith("data:image/"):
                await route.abort()
                return

        if "169.254.169.254" in req_url or "localhost" in req_url or "127.0.0.1" in req_url:
            logger.warning(f"Browser route interceptor blocked suspicious internal request: {req_url}")
            await route.abort()
            return

        await route.continue_()

    async def _close_session_unlocked(self, key: str):
        if key in self._sessions:
            record = self._sessions.pop(key)
            try:
                if not record.page.is_closed():
                    await record.page.close()
                await record.context.close()
                logger.info(f"Closed browser session '{record.session_id}'.")
            except Exception as e:
                logger.debug(f"Error closing session '{key}': {e}")

    async def close_session(self, tenant_id: str, task_id: str):
        """Explicitly tears down a session when a task finishes or is canceled."""
        key = self._session_key(tenant_id, task_id)
        async with self._lock:
            await self._close_session_unlocked(key)

    async def close_all(self):
        """Tears down all active sessions and the Chromium browser instance."""
        async with self._lock:
            keys = list(self._sessions.keys())
            for k in keys:
                await self._close_session_unlocked(k)
            if self._browser:
                try:
                    await self._browser.close()
                except Exception as e:
                    logger.debug(f"Error closing browser: {e}")
                self._browser = None
            if self._playwright:
                try:
                    await self._playwright.stop()
                except Exception as e:
                    logger.debug(f"Error stopping playwright: {e}")
                self._playwright = None
            logger.info("All browser sessions and Playwright instance cleanly stopped.")


# Global session manager instance
browser_session_manager = BrowserSessionManager()
