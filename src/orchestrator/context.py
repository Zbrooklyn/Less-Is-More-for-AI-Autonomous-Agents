"""Shared context store — thread-safe state that workers and supervisors share."""

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uuid() -> str:
    return str(uuid.uuid4())


CONTEXT_SCHEMA = """
CREATE TABLE IF NOT EXISTS shared_context (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    owner       TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS file_locks (
    path        TEXT PRIMARY KEY,
    owner       TEXT NOT NULL,
    locked_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id          TEXT PRIMARY KEY,
    sender      TEXT NOT NULL,
    recipient   TEXT NOT NULL,
    content     TEXT NOT NULL,
    msg_type    TEXT NOT NULL DEFAULT 'info',
    timestamp   TEXT NOT NULL,
    read        INTEGER DEFAULT 0
);
"""


class SharedContext:
    """Thread-safe shared context for multi-agent coordination.

    Provides:
    - Key-value store for shared state
    - File-level locking to prevent conflicts
    - Message passing between agents
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or (Path.home() / ".claude" / "orchestrator" / "context.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(CONTEXT_SCHEMA)
        self._lock = Lock()

    # --- Key-Value Store ---

    def set(self, key: str, value: str, owner: str = "supervisor"):
        """Set a shared context value."""
        with self._lock:
            self.conn.execute(
                "INSERT OR REPLACE INTO shared_context (key, value, owner, updated_at) "
                "VALUES (?, ?, ?, ?)",
                (key, value, owner, _now()),
            )
            self.conn.commit()

    def get(self, key: str) -> Optional[str]:
        """Get a shared context value."""
        row = self.conn.execute(
            "SELECT value FROM shared_context WHERE key = ?", (key,)
        ).fetchone()
        return row[0] if row else None

    def get_all(self) -> dict[str, str]:
        """Get all shared context key-value pairs."""
        rows = self.conn.execute("SELECT key, value FROM shared_context").fetchall()
        return {r[0]: r[1] for r in rows}

    def delete(self, key: str):
        """Remove a shared context value."""
        with self._lock:
            self.conn.execute("DELETE FROM shared_context WHERE key = ?", (key,))
            self.conn.commit()

    # --- File Locking ---

    def lock_file(self, path: str, owner: str) -> bool:
        """Acquire a file lock. Returns True if locked, False if already locked by another."""
        with self._lock:
            existing = self.conn.execute(
                "SELECT owner FROM file_locks WHERE path = ?", (path,)
            ).fetchone()

            if existing and existing[0] != owner:
                return False  # Locked by someone else

            self.conn.execute(
                "INSERT OR REPLACE INTO file_locks (path, owner, locked_at) VALUES (?, ?, ?)",
                (path, owner, _now()),
            )
            self.conn.commit()
            return True

    def unlock_file(self, path: str, owner: str) -> bool:
        """Release a file lock. Only the owner can unlock."""
        with self._lock:
            existing = self.conn.execute(
                "SELECT owner FROM file_locks WHERE path = ?", (path,)
            ).fetchone()

            if not existing:
                return True  # Already unlocked
            if existing[0] != owner:
                return False  # Not the owner

            self.conn.execute("DELETE FROM file_locks WHERE path = ?", (path,))
            self.conn.commit()
            return True

    def get_locked_files(self) -> list[dict]:
        """Get all currently locked files."""
        rows = self.conn.execute("SELECT * FROM file_locks").fetchall()
        return [dict(r) for r in rows]

    def is_file_locked(self, path: str) -> Optional[str]:
        """Check if a file is locked. Returns the owner or None."""
        row = self.conn.execute(
            "SELECT owner FROM file_locks WHERE path = ?", (path,)
        ).fetchone()
        return row[0] if row else None

    # --- Message Passing ---

    def send_message(self, sender: str, recipient: str, content: str, msg_type: str = "info") -> str:
        """Send a message from one agent to another. Returns message ID."""
        msg_id = _uuid()
        with self._lock:
            self.conn.execute(
                "INSERT INTO messages (id, sender, recipient, content, msg_type, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (msg_id, sender, recipient, content, msg_type, _now()),
            )
            self.conn.commit()
        return msg_id

    def get_messages(self, recipient: str, unread_only: bool = True) -> list[dict]:
        """Get messages for a recipient."""
        if unread_only:
            rows = self.conn.execute(
                "SELECT * FROM messages WHERE recipient = ? AND read = 0 ORDER BY timestamp",
                (recipient,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM messages WHERE recipient = ? ORDER BY timestamp",
                (recipient,),
            ).fetchall()
        return [dict(r) for r in rows]

    def mark_read(self, message_id: str):
        """Mark a message as read."""
        with self._lock:
            self.conn.execute("UPDATE messages SET read = 1 WHERE id = ?", (message_id,))
            self.conn.commit()

    def broadcast(self, sender: str, content: str, msg_type: str = "info") -> list[str]:
        """Send a message to all agents. Returns list of message IDs."""
        # Get unique recipients from message history
        rows = self.conn.execute(
            "SELECT DISTINCT sender FROM messages UNION SELECT DISTINCT recipient FROM messages"
        ).fetchall()
        recipients = {r[0] for r in rows} - {sender}

        ids = []
        for recipient in recipients:
            ids.append(self.send_message(sender, recipient, content, msg_type))
        return ids

    def close(self):
        self.conn.close()
