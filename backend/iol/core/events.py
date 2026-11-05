"""
Event Stream and SSE (Server-Sent Events) Infrastructure for IOL.
Provides typed event types and SSE wire protocol formatting.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict
from pydantic import BaseModel, Field


class EventType:
    TASK_CREATED = "TASK_CREATED"
    TASK_STARTED = "TASK_STARTED"
    PLAN_GENERATED = "PLAN_GENERATED"
    STEP_STARTED = "STEP_STARTED"
    STEP_COMPLETED = "STEP_COMPLETED"
    STEP_FAILED = "STEP_FAILED"
    CAPABILITY_INVOKED = "CAPABILITY_INVOKED"
    CAPABILITY_COMPLETED = "CAPABILITY_COMPLETED"
    UI_UPDATED = "UI_UPDATED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"
    TASK_CANCELLED = "TASK_CANCELLED"


def format_sse_message(event_id: int, event_type: str, data: Dict[str, Any]) -> str:
    """
    Format a message according to the W3C Server-Sent Events specification.
    Includes sequential event id for reliable replay and reconnection.
    """
    payload = json.dumps(data, default=str)
    return f"id: {event_id}\nevent: {event_type}\ndata: {payload}\n\n"
