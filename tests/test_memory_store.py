"""Tests for the memory store — CRUD, search, rules, corrections, audit."""

import tempfile
from pathlib import Path

import pytest

from src.memory.store import MemoryStore


@pytest.fixture
def store(tmp_path):
    """Create a fresh in-memory store for each test."""
    db_path = tmp_path / "test_memory.db"
    s = MemoryStore(db_path)
    yield s
    s.close()


class TestCRUD:
    """Basic create, read, update, delete operations."""

    def test_add_entry(self, store):
        entry = store.add("Never use pythonw.exe", "rule", source="test")
        assert entry["content"] == "Never use pythonw.exe"
        assert entry["type"] == "rule"
        assert entry["scope"] == "global"
        assert entry["id"] is not None

    def test_get_entry(self, store):
        entry = store.add("Test entry", "fact", source="test")
        retrieved = store.get(entry["id"])
        assert retrieved is not None
        assert retrieved["content"] == "Test entry"

    def test_get_nonexistent(self, store):
        assert store.get("nonexistent-id") is None

    def test_update_entry(self, store):
        entry = store.add("Original content", "fact", source="test")
        updated = store.update(entry["id"], content="Updated content", confidence=0.9)
        assert updated["content"] == "Updated content"
        assert updated["confidence"] == 0.9

    def test_update_ignores_invalid_fields(self, store):
        entry = store.add("Test", "fact", source="test")
        updated = store.update(entry["id"], invalid_field="bad")
        assert updated["content"] == "Test"  # unchanged

    def test_delete_entry(self, store):
        entry = store.add("To be deleted", "fact", source="test")
        assert store.delete(entry["id"]) is True
        assert store.get(entry["id"]) is None

    def test_delete_nonexistent(self, store):
        assert store.delete("nonexistent-id") is False

    def test_add_with_all_fields(self, store):
        entry = store.add(
            content="Full entry",
            entry_type="decision",
            scope="project:whisperclick",
            source="user",
            confidence=0.95,
            tags='["architecture", "pywebview"]',
        )
        assert entry["type"] == "decision"
        assert entry["scope"] == "project:whisperclick"
        assert entry["confidence"] == 0.95
        assert "architecture" in entry["tags"]


class TestQuery:
    """Full-text search functionality."""

    def test_query_finds_match(self, store):
        store.add("Never use pythonw.exe for GUI processes", "rule", source="test")
        store.add("Use python.exe instead of pythonw.exe", "rule", source="test")
        store.add("Unrelated entry about databases", "fact", source="test")

        results = store.query("pythonw")
        assert len(results) >= 1
        assert any("pythonw" in r["content"] for r in results)

    def test_query_no_results(self, store):
        store.add("Test entry", "fact", source="test")
        results = store.query("nonexistent_term_xyz")
        assert len(results) == 0

    def test_query_with_scope_filter(self, store):
        store.add("WhisperClick rule", "rule", scope="project:whisperclick", source="test")
        store.add("Global rule about pythonw", "rule", scope="global", source="test")

        results = store.query("rule", scope="project:whisperclick")
        assert all(r["scope"] == "project:whisperclick" for r in results)

    def test_query_with_type_filter(self, store):
        store.add("A rule about testing", "rule", source="test")
        store.add("A fact about testing", "fact", source="test")

        results = store.query("testing", entry_type="rule")
        assert all(r["type"] == "rule" for r in results)

    def test_query_respects_limit(self, store):
        for i in range(20):
            store.add(f"Entry number {i} about memory", "fact", source="test")

        results = store.query("memory", limit=5)
        assert len(results) <= 5


class TestStats:
    """Statistics and counts."""

    def test_empty_stats(self, store):
        stats = store.stats()
        assert stats["total"] == 0
        assert stats["by_type"] == {}

    def test_stats_counts(self, store):
        store.add("Rule 1", "rule", source="test")
        store.add("Rule 2", "rule", source="test")
        store.add("Fact 1", "fact", source="test")
        store.add("Decision 1", "decision", scope="project:test", source="test")

        stats = store.stats()
        assert stats["total"] == 4
        assert stats["by_type"]["rule"] == 2
        assert stats["by_type"]["fact"] == 1
        assert stats["by_type"]["decision"] == 1
        assert stats["by_scope"]["global"] == 3
        assert stats["by_scope"]["project:test"] == 1


class TestEnforcementRules:
    """Enforcement rule creation and retrieval."""

    def test_add_rule(self, store):
        entry = store.add_enforcement_rule(
            content="Never use pythonw.exe",
            pattern=r"pythonw\.exe",
            pattern_type="regex",
            action="block",
            severity="critical",
            alternative="Use python.exe instead",
        )
        assert entry["type"] == "rule"
        assert entry["confidence"] == 1.0

    def test_get_active_rules(self, store):
        store.add_enforcement_rule(
            content="Block pythonw",
            pattern=r"pythonw\.exe",
            action="block",
            severity="critical",
        )
        store.add_enforcement_rule(
            content="Warn about push",
            pattern=r"git\s+push\s+public",
            action="block",
            severity="high",
        )

        rules = store.get_active_rules()
        assert len(rules) == 2
        assert rules[0]["severity"] == "critical"  # ordered by severity

    def test_rule_has_all_fields(self, store):
        store.add_enforcement_rule(
            content="Test rule",
            pattern="test_pattern",
            pattern_type="command",
            action="warn",
            severity="medium",
            alternative="Do something else",
        )
        rules = store.get_active_rules()
        assert len(rules) == 1
        rule = rules[0]
        assert rule["pattern"] == "test_pattern"
        assert rule["pattern_type"] == "command"
        assert rule["action"] == "warn"
        assert rule["alternative"] == "Do something else"


class TestCorrections:
    """Correction logging."""

    def test_add_correction(self, store):
        correction = store.add_correction(
            user_message="No, never use pythonw.exe",
            what_was_wrong="Used pythonw.exe to launch GUI",
            what_is_right="Use python.exe instead",
            context="Launching WhisperClick",
        )
        assert correction["what_was_wrong"] == "Used pythonw.exe to launch GUI"
        assert correction["what_is_right"] == "Use python.exe instead"


class TestAuditLog:
    """Audit trail for all operations."""

    def test_add_creates_audit_entry(self, store):
        store.add("Test", "fact", source="test")
        log = store.get_audit_log()
        assert len(log) >= 1
        assert any(e["action"] == "add" for e in log)

    def test_query_creates_audit_entry(self, store):
        store.add("Test", "fact", source="test")
        store.query("test")
        log = store.get_audit_log()
        assert any(e["action"] == "query" for e in log)

    def test_delete_creates_audit_entry(self, store):
        entry = store.add("To delete", "fact", source="test")
        store.delete(entry["id"])
        log = store.get_audit_log()
        assert any(e["action"] == "delete" for e in log)

    def test_audit_log_ordered_by_timestamp(self, store):
        store.add("First", "fact", source="test")
        store.add("Second", "fact", source="test")
        store.add("Third", "fact", source="test")
        log = store.get_audit_log()
        # Most recent first
        assert log[0]["timestamp"] >= log[-1]["timestamp"]


class TestDatabaseIntegrity:
    """Database file management and schema."""

    def test_creates_db_file(self, tmp_path):
        db_path = tmp_path / "subdir" / "test.db"
        store = MemoryStore(db_path)
        assert db_path.exists()
        store.close()

    def test_persists_across_connections(self, tmp_path):
        db_path = tmp_path / "persist.db"

        store1 = MemoryStore(db_path)
        store1.add("Persistent entry", "fact", source="test")
        store1.close()

        store2 = MemoryStore(db_path)
        results = store2.query("Persistent")
        assert len(results) >= 1
        store2.close()

    def test_wal_mode_enabled(self, store):
        mode = store.conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"
