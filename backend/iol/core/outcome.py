"""
Unified Outcome Envelope & Evidence Language for IOL v0.6+.
Decouples outcome data, field schema, and evidence provenance from specific UI presentations.
"""

from datetime import datetime, timezone
from enum import Enum
import hashlib
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class OutcomeShape(str, Enum):
    COLLECTION = "collection"
    COMPARISON = "comparison"
    DOCUMENT = "document"
    FORM = "form"
    TIMELINE = "timeline"
    GRAPH = "graph"
    SIMULATION = "simulation"
    SINGLE_ANSWER = "single_answer"
    PARTIAL = "partial"
    BLOCKED = "blocked"


class SourceMode(str, Enum):
    LIVE_API = "LIVE_API"
    LIVE_BROWSER = "LIVE_BROWSER"
    LOCAL_COMPUTATION = "LOCAL_COMPUTATION"
    USER_SUPPLIED = "USER_SUPPLIED"
    RECORDED_REPLAY = "RECORDED_REPLAY"
    TEST_FIXTURE = "TEST_FIXTURE"


class OutcomeFieldSchema(BaseModel):
    """Semantic specification of a data column or field."""
    key: str
    header: str
    type: Literal["text", "badge", "number", "link", "score", "json", "boolean"] = "text"
    role: Optional[str] = Field(default=None, description="Semantic role: title, subtitle, metric, url, status, tag")
    unit: Optional[str] = None
    description: Optional[str] = None


class OutcomeEvidenceRecord(BaseModel):
    """Field-level provenance and verification record."""
    field_name: Optional[str] = None
    source_url: Optional[str] = None
    source_mode: SourceMode = SourceMode.LIVE_API
    retrieval_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    content_hash: Optional[str] = None
    excerpt: Optional[str] = None
    verification_method: str = "direct_retrieval"
    verification_status: str = "verified"
    confidence: float = 1.0


class OutcomeItem(BaseModel):
    """An individual entity, fact, comparison row, or data unit."""
    id: str
    fields: Dict[str, Any]
    evidence: List[OutcomeEvidenceRecord] = Field(default_factory=list)
    status: str = "verified"
    observed_at: Optional[str] = None


class OutcomeEnvelopeV1(BaseModel):
    """
    Standardized top-level envelope for all IOL task outcomes.
    Emitted monotonically across SSE events and bound progressively into ExperiencePlans.
    """
    shape: OutcomeShape
    title: str
    summary: Optional[str] = None
    field_schema: List[OutcomeFieldSchema] = Field(default_factory=list)
    items: List[OutcomeItem] = Field(default_factory=list)
    source_mode: SourceMode = SourceMode.LIVE_API
    blockers: List[str] = Field(default_factory=list)
    revision: int = 1
    meta: Dict[str, Any] = Field(default_factory=dict)

    def compute_integrity_hash(self) -> str:
        """Computes a deterministic SHA-256 fingerprint over items and evidence."""
        hasher = hashlib.sha256()
        hasher.update(self.shape.value.encode())
        hasher.update(str(self.revision).encode())
        for item in self.items:
            hasher.update(item.id.encode())
            for k in sorted(item.fields.keys()):
                hasher.update(f"{k}:{item.fields[k]}".encode())
        return hasher.hexdigest()

    def add_item(self, item: OutcomeItem) -> None:
        self.items.append(item)
        self.revision += 1

    def to_legacy_rows(self) -> List[Dict[str, Any]]:
        """Backwards compatibility adapter for TaskView and Declarative Table rendering."""
        rows = []
        for it in self.items:
            row = dict(it.fields)
            row["id"] = it.id
            if it.evidence:
                row["_evidence"] = [e.model_dump() for e in it.evidence]
            rows.append(row)
        return rows
