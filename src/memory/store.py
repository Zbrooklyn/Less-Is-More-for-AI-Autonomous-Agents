"""Memory store — SQLite database for persistent agent memory."""

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Default database location
DEFAULT_DB_PATH = Path.home() / ".claude" / "memory" / "memory.db"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uuid() -> str:
    return str(uuid.uuid4())


SCHEMA = """
CREATE TABLE IF NOT EXISTS memory_entries (
    id              TEXT PRIMARY KEY,
    content         TEXT NOT NULL,
    type            TEXT NOT NULL,
    scope           TEXT NOT NULL DEFAULT 'global',
    source          TEXT NOT NULL,
    confidence      REAL NOT NULL DEFAULT 0.5,
    tags            TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    last_used       TEXT,
    use_count       INTEGER DEFAULT 0,
    violation_count INTEGER DEFAULT 0,
    superseded_by   TEXT,
    embedding       BLOB
);

CREATE INDEX IF NOT EXISTS idx_entries_type ON memory_entries(type);
CREATE INDEX IF NOT EXISTS idx_entries_scope ON memory_entries(scope);
CREATE INDEX IF NOT EXISTS idx_entries_confidence ON memory_entries(confidence DESC);

CREATE TABLE IF NOT EXISTS enforcement_rules (
    id              TEXT PRIMARY KEY,
    pattern         TEXT NOT NULL,
    pattern_type    TEXT NOT NULL,
    action          TEXT NOT NULL,
    severity        TEXT NOT NULL,
    alternative     TEXT,
    active          INTEGER DEFAULT 1,
    FOREIGN KEY (id) REFERENCES memory_entries(id)
);

CREATE TABLE IF NOT EXISTS corrections (
    id                TEXT PRIMARY KEY,
    session_id        TEXT,
    user_message      TEXT NOT NULL,
    what_was_wrong    TEXT NOT NULL,
    what_is_right     TEXT NOT NULL,
    context           TEXT,
    detected_at       TEXT NOT NULL,
    detection_type    TEXT NOT NULL,
    promoted_to       TEXT,
    occurrence_count  INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS memory_audit_log (
    id          TEXT PRIMARY KEY,
    timestamp   TEXT NOT NULL,
    action      TEXT NOT NULL,
    entry_id    TEXT,
    context     TEXT,
    result      TEXT,
    details     TEXT
);
"""


class MemoryStore:
    """SQLite-backed memory store with full CRUD and search."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript(SCHEMA)
        # Add FTS5 virtual table for full-text search
        try:
            self.conn.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts "
                "USING fts5(content, type, scope, tags, content=memory_entries, content_rowid=rowid)"
            )
        except sqlite3.OperationalError:
            pass  # FTS5 table may already exist with different schema

    def add(
        self,
        content: str,
        entry_type: str,
        scope: str = "global",
        source: str = "manual",
        confidence: float = 0.5,
        tags: Optional[str] = None,
    ) -> dict:
        """Add a new memory entry. Returns the created entry."""
        entry_id = _uuid()
        now = _now()
        self.conn.execute(
            "INSERT INTO memory_entries (id, content, type, scope, source, confidence, tags, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (entry_id, content, entry_type, scope, source, confidence, tags, now, now),
        )
        # Update FTS index
        try:
            self.conn.execute(
                "INSERT INTO memory_fts (rowid, content, type, scope, tags) "
                "SELECT rowid, content, type, scope, tags FROM memory_entries WHERE id = ?",
                (entry_id,),
            )
        except sqlite3.OperationalError:
            pass
        self.conn.commit()
        self._audit("add", entry_id, f"type={entry_type}, scope={scope}")
        return self.get(entry_id)

    def get(self, entry_id: str) -> Optional[dict]:
        """Get a single entry by ID."""
        row = self.conn.execute(
            "SELECT * FROM memory_entries WHERE id = ?", (entry_id,)
        ).fetchone()
        return dict(row) if row else None

    def query(
        self,
        text: str,
        scope: Optional[str] = None,
        entry_type: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict]:
        """Full-text search over memory entries."""
        try:
            sql = (
                "SELECT m.* FROM memory_entries m "
                "JOIN memory_fts f ON m.rowid = f.rowid "
                "WHERE memory_fts MATCH ? "
            )
            params: list = [text]
            if scope:
                sql += "AND m.scope = ? "
                params.append(scope)
            if entry_type:
                sql += "AND m.type = ? "
                params.append(entry_type)
            sql += "ORDER BY rank LIMIT ?"
            params.append(limit)
            rows = self.conn.execute(sql, params).fetchall()
        except sqlite3.OperationalError:
            # Fallback to LIKE search if FTS fails
            sql = "SELECT * FROM memory_entries WHERE content LIKE ? "
            params = [f"%{text}%"]
            if scope:
                sql += "AND scope = ? "
                params.append(scope)
            if entry_type:
                sql += "AND type = ? "
                params.append(entry_type)
            sql += "ORDER BY confidence DESC, updated_at DESC LIMIT ?"
            params.append(limit)
            rows = self.conn.execute(sql, params).fetchall()
        self._audit("query", None, f"text={text}, results={len(rows)}")
        return [dict(r) for r in rows]

    def update(self, entry_id: str, **changes) -> Optional[dict]:
        """Update fields on an existing entry."""
        allowed = {"content", "type", "scope", "confidence", "tags", "superseded_by"}
        updates = {k: v for k, v in changes.items() if k in allowed}
        if not updates:
            return self.get(entry_id)
        updates["updated_at"] = _now()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [entry_id]
        self.conn.execute(
            f"UPDATE memory_entries SET {set_clause} WHERE id = ?", values
        )
        self.conn.commit()
        self._audit("update", entry_id, f"fields={list(updates.keys())}")
        return self.get(entry_id)

    def delete(self, entry_id: str) -> bool:
        """Delete an entry by ID."""
        cursor = self.conn.execute(
            "DELETE FROM memory_entries WHERE id = ?", (entry_id,)
        )
        self.conn.commit()
        if cursor.rowcount > 0:
            self._audit("delete", entry_id)
            return True
        return False

    def stats(self) -> dict:
        """Return counts by type and scope."""
        total = self.conn.execute("SELECT COUNT(*) FROM memory_entries").fetchone()[0]
        by_type = dict(
            self.conn.execute(
                "SELECT type, COUNT(*) FROM memory_entries GROUP BY type ORDER BY COUNT(*) DESC"
            ).fetchall()
        )
        by_scope = dict(
            self.conn.execute(
                "SELECT scope, COUNT(*) FROM memory_entries GROUP BY scope ORDER BY COUNT(*) DESC"
            ).fetchall()
        )
        by_source = dict(
            self.conn.execute(
                "SELECT source, COUNT(*) FROM memory_entries GROUP BY source ORDER BY COUNT(*) DESC"
            ).fetchall()
        )
        return {
            "total": total,
            "by_type": by_type,
            "by_scope": by_scope,
            "by_source": by_source,
        }

    def add_enforcement_rule(
        self,
        content: str,
        pattern: str,
        pattern_type: str = "regex",
        action: str = "block",
        severity: str = "high",
        alternative: Optional[str] = None,
        scope: str = "global",
    ) -> dict:
        """Add a memory entry with an associated enforcement rule."""
        entry = self.add(
            content=content,
            entry_type="rule",
            scope=scope,
            source="manual",
            confidence=1.0,
            tags='["enforcement"]',
        )
        self.conn.execute(
            "INSERT INTO enforcement_rules (id, pattern, pattern_type, action, severity, alternative) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (entry["id"], pattern, pattern_type, action, severity, alternative),
        )
        self.conn.commit()
        self._audit("add_rule", entry["id"], f"pattern={pattern}, action={action}")
        return entry

    def get_active_rules(self) -> list[dict]:
        """Get all active enforcement rules with their memory entries."""
        rows = self.conn.execute(
            "SELECT m.*, r.pattern, r.pattern_type, r.action, r.severity, r.alternative "
            "FROM memory_entries m "
            "JOIN enforcement_rules r ON m.id = r.id "
            "WHERE r.active = 1 "
            "ORDER BY CASE r.severity "
            "  WHEN 'critical' THEN 0 "
            "  WHEN 'high' THEN 1 "
            "  WHEN 'medium' THEN 2 "
            "  WHEN 'low' THEN 3 "
            "  ELSE 4 END"
        ).fetchall()
        return [dict(r) for r in rows]

    def add_correction(
        self,
        user_message: str,
        what_was_wrong: str,
        what_is_right: str,
        context: Optional[str] = None,
        session_id: Optional[str] = None,
        detection_type: str = "explicit",
    ) -> dict:
        """Log a correction."""
        correction_id = _uuid()
        self.conn.execute(
            "INSERT INTO corrections (id, session_id, user_message, what_was_wrong, what_is_right, "
            "context, detected_at, detection_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (correction_id, session_id, user_message, what_was_wrong, what_is_right,
             context, _now(), detection_type),
        )
        self.conn.commit()
        self._audit("capture", None, f"correction={correction_id}")
        return {"id": correction_id, "what_was_wrong": what_was_wrong, "what_is_right": what_is_right}

    def get_audit_log(self, limit: int = 50) -> list[dict]:
        """Get recent audit log entries."""
        rows = self.conn.execute(
            "SELECT * FROM memory_audit_log ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def _audit(self, action: str, entry_id: Optional[str] = None, context: Optional[str] = None):
        self.conn.execute(
            "INSERT INTO memory_audit_log (id, timestamp, action, entry_id, context) "
            "VALUES (?, ?, ?, ?, ?)",
            (_uuid(), _now(), action, entry_id, context),
        )
        self.conn.commit()

    def close(self):
        self.conn.close()
