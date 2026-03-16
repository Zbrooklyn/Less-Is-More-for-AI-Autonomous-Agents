"""Daemon state — persistent state store and authority tier system."""

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import IntEnum
from pathlib import Path
from typing import Optional


class AuthorityTier(IntEnum):
    """Authority levels for daemon actions."""
    AUTONOMOUS = 1   # Run tests, clean artifacts, log events
    ACT_NOTIFY = 2   # Fix lint, update deps — do it, then tell user
    PROPOSE_WAIT = 3 # Code changes, PR creation — propose and wait for approval
    ALERT_ONLY = 4   # Production deploys, security — alert user, never act


@dataclass
class DaemonTask:
    """A task the daemon is tracking."""
    id: str
    title: str
    status: str  # "pending", "in_progress", "completed", "failed", "awaiting_approval"
    authority_tier: AuthorityTier
    created_at: str
    updated_at: str
    context: Optional[str] = None
    result: Optional[str] = None


STATE_SCHEMA = """
CREATE TABLE IF NOT EXISTS daemon_tasks (
    id              TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
    authority_tier  INTEGER NOT NULL,
    context         TEXT,
    result          TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS daemon_actions (
    id          TEXT PRIMARY KEY,
    task_id     TEXT,
    action      TEXT NOT NULL,
    authority   INTEGER NOT NULL,
    approved    INTEGER,
    timestamp   TEXT NOT NULL,
    details     TEXT,
    FOREIGN KEY (task_id) REFERENCES daemon_tasks(id)
);

CREATE TABLE IF NOT EXISTS daemon_config (
    key     TEXT PRIMARY KEY,
    value   TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uuid() -> str:
    return str(uuid.uuid4())


class DaemonState:
    """Persistent state for the daemon. Survives restarts."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or (Path.home() / ".claude" / "daemon" / "state.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(STATE_SCHEMA)

    # --- Task Management ---

    def create_task(
        self,
        title: str,
        authority_tier: AuthorityTier,
        context: Optional[str] = None,
    ) -> DaemonTask:
        """Create a new daemon task."""
        task_id = _uuid()
        now = _now()
        self.conn.execute(
            "INSERT INTO daemon_tasks (id, title, status, authority_tier, context, created_at, updated_at) "
            "VALUES (?, ?, 'pending', ?, ?, ?, ?)",
            (task_id, title, int(authority_tier), context, now, now),
        )
        self.conn.commit()
        return self.get_task(task_id)

    def get_task(self, task_id: str) -> Optional[DaemonTask]:
        """Get a task by ID."""
        row = self.conn.execute("SELECT * FROM daemon_tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            return None
        return DaemonTask(
            id=row["id"],
            title=row["title"],
            status=row["status"],
            authority_tier=AuthorityTier(row["authority_tier"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            context=row["context"],
            result=row["result"],
        )

    def update_task(self, task_id: str, status: Optional[str] = None, result: Optional[str] = None) -> Optional[DaemonTask]:
        """Update task status and/or result."""
        updates = {"updated_at": _now()}
        if status:
            updates["status"] = status
        if result:
            updates["result"] = result

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [task_id]
        self.conn.execute(f"UPDATE daemon_tasks SET {set_clause} WHERE id = ?", values)
        self.conn.commit()
        return self.get_task(task_id)

    def list_tasks(self, status: Optional[str] = None) -> list[DaemonTask]:
        """List tasks, optionally filtered by status."""
        if status:
            rows = self.conn.execute(
                "SELECT * FROM daemon_tasks WHERE status = ? ORDER BY updated_at DESC", (status,)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM daemon_tasks ORDER BY updated_at DESC"
            ).fetchall()

        return [
            DaemonTask(
                id=r["id"], title=r["title"], status=r["status"],
                authority_tier=AuthorityTier(r["authority_tier"]),
                created_at=r["created_at"], updated_at=r["updated_at"],
                context=r["context"], result=r["result"],
            )
            for r in rows
        ]

    # --- Authority Checks ---

    def check_authority(self, action: str, tier: AuthorityTier) -> dict:
        """
        Check if an action is authorized at the given tier.
        Returns {authorized: bool, action_required: str, reason: str}
        """
        if tier == AuthorityTier.AUTONOMOUS:
            return {
                "authorized": True,
                "action_required": "execute",
                "reason": "Tier 1: autonomous execution",
            }
        elif tier == AuthorityTier.ACT_NOTIFY:
            return {
                "authorized": True,
                "action_required": "execute_and_notify",
                "reason": "Tier 2: act then notify user",
            }
        elif tier == AuthorityTier.PROPOSE_WAIT:
            return {
                "authorized": False,
                "action_required": "propose",
                "reason": "Tier 3: create proposal and wait for approval",
            }
        else:  # ALERT_ONLY
            return {
                "authorized": False,
                "action_required": "alert",
                "reason": "Tier 4: alert user only, never execute",
            }

    # --- Action Audit Log ---

    def log_action(
        self,
        action: str,
        authority: AuthorityTier,
        task_id: Optional[str] = None,
        approved: Optional[bool] = None,
        details: Optional[str] = None,
    ) -> str:
        """Log a daemon action with full context."""
        action_id = _uuid()
        self.conn.execute(
            "INSERT INTO daemon_actions (id, task_id, action, authority, approved, timestamp, details) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (action_id, task_id, action, int(authority), approved, _now(), details),
        )
        self.conn.commit()
        return action_id

    def get_action_log(self, limit: int = 50) -> list[dict]:
        """Get recent action log entries."""
        rows = self.conn.execute(
            "SELECT * FROM daemon_actions ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    # --- Config ---

    def set_config(self, key: str, value: str):
        """Set a config value."""
        self.conn.execute(
            "INSERT OR REPLACE INTO daemon_config (key, value) VALUES (?, ?)",
            (key, value),
        )
        self.conn.commit()

    def get_config(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a config value."""
        row = self.conn.execute(
            "SELECT value FROM daemon_config WHERE key = ?", (key,)
        ).fetchone()
        return row[0] if row else default

    def close(self):
        self.conn.close()
