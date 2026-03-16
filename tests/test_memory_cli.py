"""Tests for memory-cli — command-line interface."""

from pathlib import Path

import pytest

from src.memory.cli import main
from src.memory.store import MemoryStore


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test_cli.db")


@pytest.fixture
def populated_db(db_path):
    """Create a database with some test data."""
    store = MemoryStore(Path(db_path))
    store.add("Never use pythonw.exe for GUI", "rule", scope="global", source="test", confidence=1.0)
    store.add("WhisperClick uses pywebview", "fact", scope="project:whisperclick", source="test")
    store.add("Rate is $65/hr with $400 floor", "preference", scope="global", source="test")
    store.add("Chose pywebview over Electron", "decision", scope="project:whisperclick", source="test")
    store.add("Error fix: delete lock file if stale", "pattern", scope="project:whisperclick", source="test")
    store.close()
    return db_path


class TestCLIQuery:
    def test_query_finds_results(self, populated_db, capsys):
        main(["--db", populated_db, "query", "pythonw"])
        out = capsys.readouterr().out
        assert "pythonw" in out

    def test_query_no_results(self, populated_db, capsys):
        main(["--db", populated_db, "query", "nonexistent_xyz"])
        out = capsys.readouterr().out
        assert "No results" in out

    def test_query_with_scope(self, populated_db, capsys):
        main(["--db", populated_db, "query", "pywebview", "--scope", "project:whisperclick"])
        out = capsys.readouterr().out
        assert "pywebview" in out

    def test_query_with_type(self, populated_db, capsys):
        main(["--db", populated_db, "query", "pythonw", "--type", "rule"])
        out = capsys.readouterr().out
        assert "rule" in out.lower()


class TestCLIAdd:
    def test_add_entry(self, db_path, capsys):
        main(["--db", db_path, "add", "--content", "Test rule", "--type", "rule"])
        out = capsys.readouterr().out
        assert "Added entry" in out

    def test_add_with_scope(self, db_path, capsys):
        main(["--db", db_path, "add", "--content", "Project rule", "--type", "rule", "--scope", "project:test"])
        out = capsys.readouterr().out
        assert "project:test" in out


class TestCLIStats:
    def test_stats_empty(self, db_path, capsys):
        main(["--db", db_path, "stats"])
        out = capsys.readouterr().out
        assert "Total entries: 0" in out

    def test_stats_with_data(self, populated_db, capsys):
        main(["--db", populated_db, "stats"])
        out = capsys.readouterr().out
        assert "Total entries: 5" in out
        assert "rule" in out
        assert "fact" in out
        assert "preference" in out


class TestCLIAudit:
    def test_audit_shows_entries(self, populated_db, capsys):
        main(["--db", populated_db, "audit"])
        out = capsys.readouterr().out
        assert "add" in out  # should show add actions from populating

    def test_audit_empty(self, db_path, capsys):
        main(["--db", db_path, "audit"])
        out = capsys.readouterr().out
        assert "No audit log" in out


class TestCLIRules:
    def test_rules_empty(self, db_path, capsys):
        main(["--db", db_path, "rules"])
        out = capsys.readouterr().out
        assert "No active" in out

    def test_rules_with_data(self, db_path, capsys):
        store = MemoryStore(Path(db_path))
        store.add_enforcement_rule(
            content="Block pythonw.exe",
            pattern=r"pythonw\.exe",
            action="block",
            severity="critical",
            alternative="Use python.exe",
        )
        store.close()

        main(["--db", db_path, "rules"])
        out = capsys.readouterr().out
        assert "CRITICAL" in out
        assert "pythonw" in out


class TestCLIHelp:
    def test_no_command_shows_help(self, capsys):
        result = main([])
        out = capsys.readouterr().out
        assert "usage" in out.lower() or "memory-cli" in out.lower()
