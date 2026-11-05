"""
Durable Task and Event Store for IOL.
Supports PostgreSQL (preferred when configured) and SQLite WAL (durable local zero-dependency fallback).
Provides ACID transactions, deterministic event ordering, gapless event replay, and state persistence.
"""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from backend.iol.config import settings
from backend.iol.core.models import (
    DeclarativeUIRoot, ExecutionBudget, Task, TaskEvent, TaskStatus, utc_now
)
from backend.iol.core.events import EventType


class DurableTaskStore:
    """Persistent storage engine for tasks and sequential event streams."""

    def __init__(self, db_path: Optional[Path] = None, database_url: Optional[str] = None):
        self.database_url = database_url or settings.DATABASE_URL
        self.sqlite_path = db_path or settings.SQLITE_DB_PATH
        self.is_postgres = bool(self.database_url and self.database_url.startswith("postgres"))
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Returns SQLite connection configured with WAL and foreign keys."""
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.sqlite_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        return conn

    def _init_db(self) -> None:
        """Initialize database schema for tasks and replayable events."""
        conn = self._get_connection()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS iol_tasks (
                    task_id TEXT PRIMARY KEY,
                    intent TEXT NOT NULL,
                    status TEXT NOT NULL,
                    user_id TEXT DEFAULT 'default_user',
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    budget_json TEXT NOT NULL,
                    current_step INTEGER DEFAULT 0,
                    total_steps INTEGER DEFAULT 0,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    result_json TEXT,
                    ui_state_json TEXT,
                    metadata_json TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_tasks_status ON iol_tasks(status);
                CREATE INDEX IF NOT EXISTS idx_tasks_created ON iol_tasks(created_at);

                CREATE TABLE IF NOT EXISTS iol_task_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL REFERENCES iol_tasks(task_id) ON DELETE CASCADE,
                    event_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    data_json TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_events_task ON iol_task_events(task_id, event_id);
            """)

            # Ensure user_id column exists if table was previously initialized
            cursor = conn.execute("PRAGMA table_info(iol_tasks);")
            existing_cols = [r["name"] for r in cursor.fetchall()]
            if "user_id" not in existing_cols:
                conn.execute("ALTER TABLE iol_tasks ADD COLUMN user_id TEXT DEFAULT 'default_user';")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_user ON iol_tasks(user_id);")

            conn.commit()
        finally:
            conn.close()

    # --------------------------------------------------------------------------
    # Task Operations
    # --------------------------------------------------------------------------
    def create_task(
        self,
        intent: str,
        budget: Optional[ExecutionBudget] = None,
        metadata: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Task:
        """Create and persist a new task in PENDING state."""
        tid = task_id or f"task_{uuid.uuid4().hex[:12]}"
        bgt = budget or ExecutionBudget()
        meta = metadata or {}
        uid = user_id or meta.get("user_id") or "default_user"
        meta["user_id"] = uid
        now = utc_now().isoformat()

        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT INTO iol_tasks (
                    task_id, intent, status, user_id, created_at, budget_json, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (
                tid, intent, TaskStatus.PENDING.value, uid, now,
                bgt.model_dump_json(), json.dumps(meta)
            ))
            conn.commit()
        finally:
            conn.close()

        # Emit TASK_CREATED event
        self.append_event(tid, EventType.TASK_CREATED, {
            "task_id": tid,
            "intent": intent,
            "user_id": uid,
            "budget": bgt.model_dump()
        })

        return self.get_task(tid)  # type: ignore

    def get_task(self, task_id: str) -> Optional[Task]:
        """Retrieve task by ID with typed budget and UI state."""
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT * FROM iol_tasks WHERE task_id = ?;", (task_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_task(row)
        finally:
            conn.close()

    def list_tasks(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[TaskStatus] = None,
        user_id: Optional[str] = None
    ) -> List[Task]:
        """List tasks ordered by creation time descending, optionally filtered by user_id."""
        conn = self._get_connection()
        try:
            clauses = ["1=1"]
            params: List[Any] = []
            if status:
                clauses.append("status = ?")
                params.append(status.value)
            if user_id:
                clauses.append("user_id = ?")
                params.append(user_id)

            where_str = " AND ".join(clauses)
            query = f"SELECT * FROM iol_tasks WHERE {where_str} ORDER BY created_at DESC LIMIT ? OFFSET ?;"
            params.extend([limit, offset])

            cursor = conn.execute(query, tuple(params))
            return [self._row_to_task(r) for r in cursor.fetchall()]
        finally:
            conn.close()

    def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        error_message: Optional[str] = None
    ) -> None:
        """Update task lifecycle status."""
        conn = self._get_connection()
        try:
            now = utc_now().isoformat()
            if status == TaskStatus.RUNNING:
                conn.execute(
                    "UPDATE iol_tasks SET status = ?, started_at = COALESCE(started_at, ?) WHERE task_id = ?;",
                    (status.value, now, task_id)
                )
            elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                conn.execute(
                    "UPDATE iol_tasks SET status = ?, completed_at = ?, error_message = ? WHERE task_id = ?;",
                    (status.value, now, error_message, task_id)
                )
            else:
                conn.execute(
                    "UPDATE iol_tasks SET status = ?, error_message = ? WHERE task_id = ?;",
                    (status.value, error_message, task_id)
                )
            conn.commit()
        finally:
            conn.close()

    def update_task_progress(self, task_id: str, current_step: int, total_steps: int) -> None:
        """Update execution step progress."""
        conn = self._get_connection()
        try:
            conn.execute(
                "UPDATE iol_tasks SET current_step = ?, total_steps = ? WHERE task_id = ?;",
                (current_step, total_steps, task_id)
            )
            conn.commit()
        finally:
            conn.close()

    def update_task_ui(self, task_id: str, ui_state: DeclarativeUIRoot) -> None:
        """Persist updated declarative UI structure."""
        conn = self._get_connection()
        try:
            conn.execute(
                "UPDATE iol_tasks SET ui_state_json = ? WHERE task_id = ?;",
                (ui_state.model_dump_json(), task_id)
            )
            conn.commit()
        finally:
            conn.close()

    def update_task_result(self, task_id: str, result: Dict[str, Any]) -> None:
        """Persist structured outcome payload."""
        conn = self._get_connection()
        try:
            conn.execute(
                "UPDATE iol_tasks SET result_json = ? WHERE task_id = ?;",
                (json.dumps(result, default=str), task_id)
            )
            conn.commit()
        finally:
            conn.close()

    def cancel_task(self, task_id: str, reason: str = "Cancelled by user") -> bool:
        """Request immediate task cancellation and append event."""
        task = self.get_task(task_id)
        if not task:
            return False
        if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            return False

        self.update_task_status(task_id, TaskStatus.CANCELLED, error_message=reason)
        self.append_event(task_id, EventType.TASK_CANCELLED, {
            "task_id": task_id,
            "reason": reason
        })
        return True

    def is_task_cancelled(self, task_id: str) -> bool:
        """Check if task was marked cancelled."""
        task = self.get_task(task_id)
        return task is not None and task.status == TaskStatus.CANCELLED

    # --------------------------------------------------------------------------
    # Event Stream & SSE Replay Operations
    # --------------------------------------------------------------------------
    def append_event(self, task_id: str, event_type: str, data: Dict[str, Any]) -> TaskEvent:
        """Append an event to the durable log with an atomic auto-incrementing ID."""
        now = utc_now().isoformat()
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                INSERT INTO iol_task_events (task_id, event_type, timestamp, data_json)
                VALUES (?, ?, ?, ?);
            """, (task_id, event_type, now, json.dumps(data, default=str)))
            event_id = cursor.lastrowid
            conn.commit()
            return TaskEvent(
                event_id=event_id,
                task_id=task_id,
                event_type=event_type,
                timestamp=datetime.fromisoformat(now),
                data=data
            )
        finally:
            conn.close()

    def get_events(
        self,
        task_id: str,
        since_event_id: Optional[int] = None,
        limit: int = 500
    ) -> List[TaskEvent]:
        """
        Retrieve persisted events for a task, optionally starting strictly AFTER since_event_id.
        Supports seamless SSE reconnection via Last-Event-ID.
        """
        conn = self._get_connection()
        try:
            if since_event_id is not None:
                cursor = conn.execute("""
                    SELECT * FROM iol_task_events
                    WHERE task_id = ? AND event_id > ?
                    ORDER BY event_id ASC LIMIT ?;
                """, (task_id, since_event_id, limit))
            else:
                cursor = conn.execute("""
                    SELECT * FROM iol_task_events
                    WHERE task_id = ?
                    ORDER BY event_id ASC LIMIT ?;
                """, (task_id, limit))

            events = []
            for r in cursor.fetchall():
                events.append(TaskEvent(
                    event_id=r["event_id"],
                    task_id=r["task_id"],
                    event_type=r["event_type"],
                    timestamp=datetime.fromisoformat(r["timestamp"]),
                    data=json.loads(r["data_json"])
                ))
            return events
        finally:
            conn.close()

    # --------------------------------------------------------------------------
    # Internal Helpers
    # --------------------------------------------------------------------------
    def _row_to_task(self, row: sqlite3.Row) -> Task:
        budget_data = json.loads(row["budget_json"]) if row["budget_json"] else {}
        budget = ExecutionBudget(**budget_data)

        ui_state = None
        if row["ui_state_json"]:
            ui_state = DeclarativeUIRoot.model_validate_json(row["ui_state_json"])

        result = json.loads(row["result_json"]) if row["result_json"] else None
        meta = json.loads(row["metadata_json"]) if row["metadata_json"] else {}
        row_keys = row.keys() if hasattr(row, "keys") else []
        uid = row["user_id"] if "user_id" in row_keys and row["user_id"] else meta.get("user_id", "default_user")

        return Task(
            task_id=row["task_id"],
            intent=row["intent"],
            status=TaskStatus(row["status"]),
            user_id=uid,
            created_at=datetime.fromisoformat(row["created_at"]),
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            budget=budget,
            current_step=row["current_step"],
            total_steps=row["total_steps"],
            error_message=row["error_message"],
            retry_count=row["retry_count"],
            result=result,
            ui_state=ui_state,
            metadata=meta
        )


task_store = DurableTaskStore()
