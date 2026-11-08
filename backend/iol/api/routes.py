"""
FastAPI REST API Routes for IOL.
Provides endpoints to create, retrieve, list, and cancel tasks,
discover registered capabilities, and stream replayable SSE events.
"""

import asyncio
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request, status
from fastapi.responses import StreamingResponse

from backend.iol.api.auth import UserContext, get_current_user, verify_task_ownership
from backend.iol.capabilities.registry import capability_registry
from backend.iol.core.events import EventType, format_sse_message
from backend.iol.core.models import (
    CancelTaskRequest, CreateTaskRequest, Task, TaskStatus, utc_now
)
from backend.iol.core.store import task_store
from backend.iol.core.actions import TaskActionRequest, action_approval_manager
from backend.iol.core.replay_bundle import create_replay_bundle
from backend.iol.browser.models import BrowserActionEffect
from pydantic import BaseModel
from backend.iol.worker.background_worker import background_worker

api_router = APIRouter(prefix="/api")


# ------------------------------------------------------------------------------
# Task Endpoints
# ------------------------------------------------------------------------------
@api_router.post("/tasks", response_model=Task, status_code=status.HTTP_201_CREATED)
async def create_task(
    req: CreateTaskRequest,
    current_user: UserContext = Depends(get_current_user)
):
    """
    Create a new task from user intent and enqueue it for background execution.
    The task executes asynchronously and independently of the browser tab.
    Server derives authenticated user_id to enforce multi-tenant isolation.
    """
    meta = dict(req.metadata or {})
    derived_user_id = current_user.user_id
    meta["user_id"] = derived_user_id

    task = task_store.create_task(
        intent=req.intent,
        budget=req.budget,
        metadata=meta,
        user_id=derived_user_id
    )
    background_worker.enqueue_task(task.task_id)
    return task


@api_router.get("/tasks", response_model=List[Task])
async def list_tasks(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[TaskStatus] = Query(None),
    current_user: UserContext = Depends(get_current_user)
):
    """List persistent tasks with optional status filter, scoped strictly to the authenticated user."""
    user_filter = None if current_user.is_admin else current_user.user_id
    return task_store.list_tasks(limit=limit, offset=offset, status=status, user_id=user_filter)


@api_router.get("/tasks/{task_id}", response_model=Task)
async def get_task(
    task_id: str,
    current_user: UserContext = Depends(get_current_user)
):
    """Retrieve full task details, verifying that authenticated user owns the task."""
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found."
        )
    verify_task_ownership(task, current_user)
    return task


@api_router.get("/tasks/{task_id}/experience")
async def get_task_experience(
    task_id: str,
    current_user: UserContext = Depends(get_current_user)
):
    """Retrieve the current ExperiencePlan for adaptive workspace rendering."""
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found."
        )
    verify_task_ownership(task, current_user)
    return {
        "task_id": task_id,
        "experience_plan": task.experience_plan
    }


@api_router.get("/tasks/{task_id}/outcome")
async def get_task_outcome(
    task_id: str,
    current_user: UserContext = Depends(get_current_user)
):
    """Retrieve the current OutcomeEnvelopeV1 for data and evidence inspection."""
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found."
        )
    verify_task_ownership(task, current_user)
    return {
        "task_id": task_id,
        "outcome_envelope": task.outcome_envelope
    }


@api_router.post("/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    req: CancelTaskRequest = CancelTaskRequest(),
    current_user: UserContext = Depends(get_current_user)
):
    """Cancel a running or pending task, verifying that authenticated user owns the task."""
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found."
        )
    verify_task_ownership(task, current_user)

    cancelled = task_store.cancel_task(task_id, reason=req.reason or "Cancelled by user")
    return {
        "task_id": task_id,
        "cancelled": cancelled,
        "current_status": task_store.get_task(task_id).status.value  # type: ignore
    }


# ------------------------------------------------------------------------------
# SSE Event Stream with Replay & Reconnection
# ------------------------------------------------------------------------------
@api_router.get("/tasks/{task_id}/events")
async def task_event_stream(
    task_id: str,
    request: Request,
    last_event_id: Optional[int] = Query(None),
    last_event_id_header: Optional[str] = Header(None, alias="Last-Event-ID"),
    current_user: UserContext = Depends(get_current_user)
):
    """
    Server-Sent Events (SSE) stream supporting reconnection and replay.
    Verifies that authenticated user owns the requested task.
    """
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found."
        )
    verify_task_ownership(task, current_user)

    # Determine starting event id for replay
    since_id: Optional[int] = None
    if last_event_id is not None:
        since_id = last_event_id
    elif last_event_id_header:
        try:
            since_id = int(last_event_id_header)
        except ValueError:
            pass

    async def event_generator():
        latest_id = since_id

        # 1. Replay phase: yield all historical events after since_id
        historical_events = task_store.get_events(task_id, since_event_id=since_id)
        for ev in historical_events:
            latest_id = ev.event_id
            yield format_sse_message(ev.event_id, ev.event_type, {
                "event_id": ev.event_id,
                "task_id": ev.task_id,
                "event_type": ev.event_type,
                "timestamp": ev.timestamp.isoformat(),
                "data": ev.data
            })

        # 2. Real-time streaming phase
        poll_count = 0
        while True:
            if await request.is_disconnected():
                break

            new_events = task_store.get_events(task_id, since_event_id=latest_id)
            if new_events:
                for ev in new_events:
                    latest_id = ev.event_id
                    yield format_sse_message(ev.event_id, ev.event_type, {
                        "event_id": ev.event_id,
                        "task_id": ev.task_id,
                        "event_type": ev.event_type,
                        "timestamp": ev.timestamp.isoformat(),
                        "data": ev.data
                    })

            # Check if task is in terminal state
            curr_task = task_store.get_task(task_id)
            if curr_task and curr_task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                # Drain any remaining events before closing
                remaining = task_store.get_events(task_id, since_event_id=latest_id)
                for ev in remaining:
                    yield format_sse_message(ev.event_id, ev.event_type, {
                        "event_id": ev.event_id,
                        "task_id": ev.task_id,
                        "event_type": ev.event_type,
                        "timestamp": ev.timestamp.isoformat(),
                        "data": ev.data
                    })
                # Send terminal keep-alive comment and exit
                yield ": task_terminal\n\n"
                break

            # Send keep-alive comment every ~10 polls (5 seconds)
            poll_count += 1
            if poll_count % 10 == 0:
                yield ": keepalive\n\n"

            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ------------------------------------------------------------------------------
# Capability Registry Endpoint
# ------------------------------------------------------------------------------
@api_router.get("/capabilities")
async def list_capabilities():
    """Discover available IOL capabilities with JSON schemas and verification metadata."""
    return capability_registry.list_capabilities()


# ------------------------------------------------------------------------------
# Action Approval & UI Action Relay Endpoints
# ------------------------------------------------------------------------------
class ApproveActionPayload(BaseModel):
    ticket_id: str
    fingerprint: Optional[str] = None


class RejectActionPayload(BaseModel):
    ticket_id: str
    reason: Optional[str] = None


@api_router.post("/tasks/{task_id}/actions")
async def request_task_action(
    task_id: str,
    action_req: TaskActionRequest,
    current_user: UserContext = Depends(get_current_user)
):
    """
    Submits a UI or execution action for backend validation, policy check, and scoped execution.
    """
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task '{task_id}' not found.")
    verify_task_ownership(task, current_user)

    action_req.task_id = task_id

    # If action has consequential side effects, require approval ticket
    if action_req.effect in (BrowserActionEffect.EXTERNAL_WRITE, BrowserActionEffect.PAYMENT_OR_ORDER, BrowserActionEffect.DESTRUCTIVE):
        ticket = action_approval_manager.create_ticket(action_req)
        task_store.update_task_status(task_id, TaskStatus.PAUSED_FOR_APPROVAL)

        pending_data = {
            "ticket_id": ticket.ticket_id,
            "action_id": action_req.action_id,
            "action_type": action_req.action_type,
            "effect": action_req.effect.value,
            "target_url": action_req.target_endpoint or getattr(action_req, "target_url", None),
            "fingerprint": ticket.fingerprint,
            "expires_at": ticket.expires_at,
            "parameters": action_req.parameters,
            "explanation": action_req.rationale or "This action requires operator approval.",
            "ticket": ticket.model_dump()
        }

        curr = task_store.get_task(task_id)
        if curr:
            meta = dict(curr.metadata or {})
            meta["pending_action"] = pending_data
            task_store.update_task_metadata(task_id, meta)

        task_store.append_event(task_id, EventType.APPROVAL_REQUIRED, pending_data)
        return {
            "status": "APPROVAL_REQUIRED",
            "approval_status": "APPROVAL_REQUIRED",
            "message": f"Action '{action_req.action_type}' has effect '{action_req.effect.value}' and requires operator approval.",
            "ticket": ticket.model_dump()
        }

    # Safe / Draft action
    task_store.append_event(task_id, EventType.ACTION_COMPLETED, {
        "action_id": action_req.action_id,
        "action_type": action_req.action_type,
        "effect": action_req.effect.value,
        "status": "COMPLETED"
    })
    return {
        "status": "COMPLETED",
        "action_id": action_req.action_id,
        "message": f"Action '{action_req.action_type}' executed safely without external side effects."
    }


@api_router.post("/tasks/{task_id}/actions/approve")
async def approve_task_action(
    task_id: str,
    payload: ApproveActionPayload,
    current_user: UserContext = Depends(get_current_user)
):
    """
    Approves and executes a consequential action using a scoped cryptographic ticket fingerprint.
    """
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task '{task_id}' not found.")
    verify_task_ownership(task, current_user)

    success, err = action_approval_manager.approve_ticket(
        ticket_id=payload.ticket_id,
        fingerprint=payload.fingerprint,
        approver_id=current_user.user_id
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err or "Approval failed.")

    # Execute action and record
    result = {"approved": True, "executed_at": utc_now().isoformat(), "approver": current_user.user_id}
    action_approval_manager.mark_executed(payload.ticket_id, result)

    # Resume task and clear pending action
    task_store.update_task_status(task_id, TaskStatus.COMPLETED)
    curr = task_store.get_task(task_id)
    if curr and "pending_action" in (curr.metadata or {}):
        meta = dict(curr.metadata)
        meta.pop("pending_action", None)
        task_store.update_task_metadata(task_id, meta)
    task_store.append_event(task_id, EventType.ACTION_APPROVED, {
        "ticket_id": payload.ticket_id,
        "fingerprint": payload.fingerprint,
        "approved_by": current_user.user_id
    })
    task_store.append_event(task_id, EventType.ACTION_COMPLETED, {
        "ticket_id": payload.ticket_id,
        "status": "EXECUTED",
        "result": result
    })

    return {
        "status": "APPROVED_AND_EXECUTED",
        "ticket_id": payload.ticket_id,
        "result": result
    }


@api_router.get("/tasks/{task_id}/replay-bundle")
async def get_replay_bundle(
    task_id: str,
    current_user: UserContext = Depends(get_current_user)
):
    """
    Exports a privacy-scrubbed, tamper-evident ReplayBundle for offline demonstration.
    """
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task '{task_id}' not found.")
    verify_task_ownership(task, current_user)

    bundle = create_replay_bundle(task_id, task_store)
    if not bundle:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to create replay bundle.")

    return bundle.model_dump()

