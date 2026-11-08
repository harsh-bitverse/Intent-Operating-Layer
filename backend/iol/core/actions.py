"""
Action Approval Gateway & UI Action Relay for IOL.
Provides cryptographic scoping, anti-replay guards, and approval gates for consequential actions.
"""

from datetime import datetime, timedelta, timezone
from enum import Enum
import hashlib
import json
import logging
from typing import Any, Dict, Optional, Tuple
import uuid
from pydantic import BaseModel, Field

from backend.iol.browser.models import BrowserActionEffect

logger = logging.getLogger("iol.actions")

TICKET_EXPIRY_MINUTES = 15


class ActionStatus(str, Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"
    EXPIRED = "EXPIRED"


class TaskActionRequest(BaseModel):
    """Action requested via UI or capability pipeline."""
    action_id: str = Field(default_factory=lambda: f"act_{uuid.uuid4().hex[:8]}")
    task_id: Optional[str] = None
    action_type: str  # e.g. "submit_form", "browser_click", "external_api_call"
    effect: BrowserActionEffect = BrowserActionEffect.READ
    target_endpoint: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    expected_task_version: Optional[int] = None
    rationale: Optional[str] = None


class ActionApprovalTicket(BaseModel):
    """Scoped cryptographic ticket granting one-time execution rights."""
    ticket_id: str
    action_id: str
    task_id: str
    fingerprint: str
    effect: BrowserActionEffect
    created_at: str
    expires_at: str
    status: ActionStatus = ActionStatus.PENDING_APPROVAL
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    execution_result: Optional[Dict[str, Any]] = None


class ActionApprovalManager:
    """Manages ticket issuance, cryptographic fingerprinting, and replay prevention."""

    def __init__(self):
        self._tickets: Dict[str, ActionApprovalTicket] = {}

    def _compute_fingerprint(self, task_id: str, action_id: str, effect: str, params: Dict[str, Any], created_at: str) -> str:
        payload = f"{task_id}:{action_id}:{effect}:{json.dumps(params, sort_keys=True)}:{created_at}"
        return hashlib.sha256(payload.encode()).hexdigest()

    def create_ticket(self, request: TaskActionRequest) -> ActionApprovalTicket:
        """Issues an approval ticket with 15-minute expiry."""
        ticket_id = f"tkt_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        created_at = now.isoformat()
        expires_at = (now + timedelta(minutes=TICKET_EXPIRY_MINUTES)).isoformat()

        fingerprint = self._compute_fingerprint(
            task_id=request.task_id,
            action_id=request.action_id,
            effect=request.effect.value,
            params=request.parameters,
            created_at=created_at,
        )

        ticket = ActionApprovalTicket(
            ticket_id=ticket_id,
            action_id=request.action_id,
            task_id=request.task_id,
            fingerprint=fingerprint,
            effect=request.effect,
            created_at=created_at,
            expires_at=expires_at,
            status=ActionStatus.PENDING_APPROVAL,
        )
        self._tickets[ticket_id] = ticket
        return ticket

    def get_ticket(self, ticket_id: str) -> Optional[ActionApprovalTicket]:
        ticket = self._tickets.get(ticket_id)
        if not ticket:
            return None

        # Check expiry
        now = datetime.now(timezone.utc)
        expires = datetime.fromisoformat(ticket.expires_at)
        if now > expires and ticket.status == ActionStatus.PENDING_APPROVAL:
            ticket.status = ActionStatus.EXPIRED

        return ticket

    def approve_ticket(self, ticket_id: str, fingerprint: Optional[str] = None, approver_id: str = "operator") -> Tuple[bool, Optional[str]]:
        """Validates fingerprint (if provided) and marks ticket as approved."""
        ticket = self.get_ticket(ticket_id)
        if not ticket:
            return False, "Ticket not found."

        if ticket.status == ActionStatus.EXPIRED:
            return False, "Ticket has expired."

        if ticket.status == ActionStatus.EXECUTED:
            return False, "Replay rejected: Ticket has already been executed."

        if fingerprint is not None and ticket.fingerprint != fingerprint:
            return False, "Security violation: Approval fingerprint mismatch."

        ticket.status = ActionStatus.APPROVED
        ticket.approved_by = approver_id
        ticket.approved_at = datetime.now(timezone.utc).isoformat()
        return True, None

    def mark_executed(self, ticket_id: str, result: Dict[str, Any]) -> None:
        """Records execution to prevent replay."""
        ticket = self._tickets.get(ticket_id)
        if ticket:
            ticket.status = ActionStatus.EXECUTED
            ticket.execution_result = result


action_approval_manager = ActionApprovalManager()
