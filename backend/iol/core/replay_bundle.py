"""
Traceable Replay Bundle Generator and Verifier for IOL.
Produces portable, tamper-evident, privacy-sanitized ReplayBundles labeled 'RECORDED REPLAY'.
"""

from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

from backend.iol.core.models import Task
from backend.iol.core.store import task_store, DurableTaskStore

SECRET_PATTERNS = [
    re.compile(r"(api[_-]?key|token|secret|password|bearer|auth|authorization)", re.IGNORECASE),
]


class ReplayBundle(BaseModel):
    """
    Exportable, self-contained record of a task execution.
    Guarantees verifiable provenance and transparent labeling for offline demonstration.
    """
    bundle_id: str
    original_task_id: str
    intent: str
    label: Literal["RECORDED REPLAY"] = "RECORDED REPLAY"
    recorded_at: str
    events: List[Dict[str, Any]] = Field(default_factory=list)
    outcome_envelope: Optional[Dict[str, Any]] = None
    experience_plan: Optional[Dict[str, Any]] = None
    integrity_hash: str = ""

    def calculate_integrity(self) -> str:
        """Computes deterministic SHA-256 over task metadata and canonical event stream."""
        hasher = hashlib.sha256()
        hasher.update(self.bundle_id.encode())
        hasher.update(self.original_task_id.encode())
        hasher.update(self.intent.encode())
        hasher.update(self.recorded_at.encode())
        for ev in self.events:
            ev_str = json.dumps(ev, sort_keys=True, default=str)
            hasher.update(ev_str.encode())
        return hasher.hexdigest()

    def verify(self) -> bool:
        """Returns True if the bundle has not been tampered with."""
        return self.calculate_integrity() == self.integrity_hash


def sanitize_payload(obj: Any) -> Any:
    """Recursively redacts API keys, credentials, and authentication tokens."""
    if isinstance(obj, dict):
        cleaned = {}
        for k, v in obj.items():
            if any(p.search(k) for p in SECRET_PATTERNS):
                cleaned[k] = "[REDACTED_CREDENTIAL]"
            else:
                cleaned[k] = sanitize_payload(v)
        return cleaned
    elif isinstance(obj, list):
        return [sanitize_payload(i) for i in obj]
    return obj


def create_replay_bundle(task_id: str, store: DurableTaskStore = task_store) -> Optional[ReplayBundle]:
    """Generates a sanitized, tamper-evident ReplayBundle from a completed task."""
    task: Optional[Task] = store.get_task(task_id)
    if not task:
        return None

    raw_events = store.get_events(task_id)
    sanitized_events = []
    for ev in raw_events:
        sanitized_data = sanitize_payload(ev.data)
        sanitized_events.append({
            "event_id": ev.event_id,
            "event_type": ev.event_type,
            "timestamp": ev.timestamp.isoformat(),
            "data": sanitized_data,
        })

    outcome = task.outcome_envelope
    if outcome and isinstance(outcome, dict):
        outcome = sanitize_payload(outcome)
        outcome["source_mode"] = "RECORDED_REPLAY"

    exp_plan = task.experience_plan
    if exp_plan and isinstance(exp_plan, dict):
        exp_plan = sanitize_payload(exp_plan)

    now = datetime.now(timezone.utc).isoformat()
    bundle = ReplayBundle(
        bundle_id=f"replay_{task_id}_{int(datetime.now().timestamp())}",
        original_task_id=task_id,
        intent=task.intent,
        label="RECORDED REPLAY",
        recorded_at=now,
        events=sanitized_events,
        outcome_envelope=outcome,
        experience_plan=exp_plan,
    )
    bundle.integrity_hash = bundle.calculate_integrity()
    return bundle
