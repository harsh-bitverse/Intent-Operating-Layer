"""
Data Models and Entity Schemas for Intent Operating Layer (IOL).
Defines Task, TaskEvent, TaskStatus, ExecutionBudget, and Declarative UI components.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    PAUSED_FOR_APPROVAL = "PAUSED_FOR_APPROVAL"


class ExecutionBudget(BaseModel):
    """Budget constraints enforced on each task execution."""
    max_duration_seconds: float = Field(default=300.0, description="Max execution time in seconds")
    max_steps: int = Field(default=20, description="Max capability execution steps")
    max_cost_usd: float = Field(default=1.0, description="Max spend in USD")
    retry_limit: int = Field(default=2, description="Max retries per step")


# ==============================================================================
# Declarative UI Schema
# Safe, declarative specifications rendered directly by the frontend.
# Supports tables, cards, and timelines.
# ==============================================================================

class CardMetric(BaseModel):
    label: str
    value: Union[str, int, float]
    unit: Optional[str] = None
    change: Optional[str] = None


class CardComponent(BaseModel):
    type: Literal["card"] = "card"
    id: str
    title: str
    subtitle: Optional[str] = None
    variant: Literal["default", "highlight", "warning", "success", "info"] = "default"
    metrics: List[CardMetric] = Field(default_factory=list)
    badges: List[str] = Field(default_factory=list)
    content: Optional[str] = None


class TableColumn(BaseModel):
    key: str
    header: str
    type: Literal["text", "badge", "number", "link", "score"] = "text"
    format: Optional[str] = None


class TableComponent(BaseModel):
    type: Literal["table"] = "table"
    id: str
    title: str
    subtitle: Optional[str] = None
    columns: List[TableColumn]
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    total_count: Optional[int] = None


class TimelineItem(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    status: Literal["pending", "running", "success", "failed", "skipped"] = "pending"
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TimelineComponent(BaseModel):
    type: Literal["timeline"] = "timeline"
    id: str
    title: str
    items: List[TimelineItem] = Field(default_factory=list)


class ComparisonEntity(BaseModel):
    entity_id: str
    name: str
    subtitle: Optional[str] = None
    badge: Optional[str] = None
    primary_metric: Optional[str] = None
    url: Optional[str] = None


class ComparisonFeature(BaseModel):
    key: str
    label: str
    values: Dict[str, Any]  # entity_id -> value
    winner_entity_id: Optional[str] = None
    confidence_tier: Optional[str] = "HIGH"


class ComparisonComponent(BaseModel):
    type: Literal["comparison"] = "comparison"
    id: str
    title: str
    subtitle: Optional[str] = None
    entities: List[ComparisonEntity] = Field(default_factory=list)
    features: List[ComparisonFeature] = Field(default_factory=list)


UIComponent = Union[CardComponent, TableComponent, TimelineComponent, ComparisonComponent]


class DeclarativeUIRoot(BaseModel):
    """Top-level container for declarative UI rendered in the task view."""
    title: str
    summary: Optional[str] = None
    components: List[UIComponent] = Field(default_factory=list)
    last_updated: str = Field(default_factory=lambda: utc_now().isoformat())


# ==============================================================================
# Task and Event Models
# ==============================================================================

class Task(BaseModel):
    task_id: str
    intent: str
    status: TaskStatus = TaskStatus.PENDING
    user_id: Optional[str] = "default_user"
    created_at: datetime = Field(default_factory=utc_now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    budget: ExecutionBudget = Field(default_factory=ExecutionBudget)
    current_step: int = 0
    total_steps: int = 0
    error_message: Optional[str] = None
    retry_count: int = 0
    result: Optional[Dict[str, Any]] = None
    ui_state: Optional[DeclarativeUIRoot] = None
    experience_plan: Optional[Dict[str, Any]] = None
    outcome_envelope: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskEvent(BaseModel):
    event_id: int
    task_id: str
    event_type: str
    timestamp: datetime = Field(default_factory=utc_now)
    data: Dict[str, Any] = Field(default_factory=dict)


class CreateTaskRequest(BaseModel):
    intent: str = Field(..., min_length=3, description="User intent in natural language")
    user_id: Optional[str] = Field(default="default_user", description="Scoped user or tenant identifier")
    budget: Optional[ExecutionBudget] = None
    metadata: Optional[Dict[str, Any]] = None


class CancelTaskRequest(BaseModel):
    reason: Optional[str] = Field(default="Cancelled by user")
