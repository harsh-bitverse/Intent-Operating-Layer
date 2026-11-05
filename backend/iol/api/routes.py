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
    CancelTaskRequest, CreateTaskRequest, Task, TaskStatus
)
from backend.iol.core.store import task_store
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
