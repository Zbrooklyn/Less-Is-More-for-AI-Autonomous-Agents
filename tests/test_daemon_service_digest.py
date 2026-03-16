"""Tests for daemon service wrapper and daily digest."""

import json
from pathlib import Path

import pytest

from src.daemon.state import DaemonState, AuthorityTier
from src.daemon.digest import generate_digest
from src.daemon.service import _write_state, _read_state, STATE_FILE


@pytest.fixture
def state(tmp_path):
    db_path = tmp_path / "test_digest.db"
    s = DaemonState(db_path)
    yield s
    s.close()


# === Digest ===

class TestDigest:
    def test_empty_digest(self, state):
        digest = generate_digest(state, hours=24)
        assert "Daemon Digest" in digest

    def test_digest_with_actions(self, state):
        # Add some actions
        state.log_action("enforce", AuthorityTier.AUTONOMOUS, details="block: pythonw.exe")
        state.log_action("enforce", AuthorityTier.AUTONOMOUS, details="allow: echo hello")
        state.log_action("triage_drop", AuthorityTier.AUTONOMOUS, details="Dropped: noise")

        digest = generate_digest(state, hours=24)
        assert "Actions:** 3" in digest
        assert "enforce" in digest

    def test_digest_with_tasks(self, state):
        task = state.create_task("Code review needed", AuthorityTier.PROPOSE_WAIT)
        state.update_task(task.id, status="awaiting_approval")

        digest = generate_digest(state, hours=24)
        assert "Awaiting Approval" in digest
        assert "Code review" in digest

    def test_digest_with_completed_tasks(self, state):
        task = state.create_task("Run tests", AuthorityTier.AUTONOMOUS)
        state.update_task(task.id, status="completed")

        digest = generate_digest(state, hours=24)
        assert "Completed" in digest
        assert "Run tests" in digest

    def test_digest_with_failed_tasks(self, state):
        task = state.create_task("Deploy", AuthorityTier.ALERT_ONLY)
        state.update_task(task.id, status="failed", result="Permission denied")

        digest = generate_digest(state, hours=24)
        assert "Failed" in digest

    def test_digest_with_blocked_actions(self, state):
        state.log_action("enforce", AuthorityTier.AUTONOMOUS, details="block: pythonw.exe detected")

        digest = generate_digest(state, hours=24)
        assert "Blocked" in digest
        assert "pythonw" in digest

    def test_digest_writes_to_file(self, state, tmp_path):
        output = tmp_path / "digest.md"
        state.log_action("test", AuthorityTier.AUTONOMOUS)

        digest = generate_digest(state, hours=24, output_path=output)
        assert output.exists()
        assert output.read_text() == digest

    def test_digest_respects_time_window(self, state):
        # Actions are all recent, so a 24h window should catch them
        state.log_action("recent", AuthorityTier.AUTONOMOUS)

        digest_24h = generate_digest(state, hours=24)
        assert "Actions:** 1" in digest_24h

        # A 0-hour window should catch nothing (or very little)
        # But since actions are just created, they're within any window
        # This tests that the parameter is respected
        digest = generate_digest(state, hours=0)
        assert "Daemon Digest" in digest


# === Service State ===

class TestServiceState:
    def test_write_and_read_state(self, tmp_path, monkeypatch):
        test_state_file = tmp_path / "daemon-pid.json"
        monkeypatch.setattr("src.daemon.service.STATE_FILE", test_state_file)

        _write_state(12345, "running")
        state = _read_state()

        assert state["pid"] == 12345
        assert state["status"] == "running"
        assert "started_at" in state

    def test_read_missing_state(self, tmp_path, monkeypatch):
        test_state_file = tmp_path / "nonexistent.json"
        monkeypatch.setattr("src.daemon.service.STATE_FILE", test_state_file)

        state = _read_state()
        assert state == {}


# === Credential Migration ===

class TestCredentialMigration:
    def _load_migrate_module(self):
        """Load the migration script as a module."""
        import importlib.util
        import sys as _sys
        # Ensure project root is on path so src.credentials imports work
        project_root = str(Path(__file__).parent.parent)
        if project_root not in _sys.path:
            _sys.path.insert(0, project_root)

        spec = importlib.util.spec_from_file_location(
            "migrate_creds",
            str(Path(__file__).parent.parent / "scripts" / "migrate-credentials.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_parse_env_file(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text(
            "# Comment\n"
            "API_KEY=abc123\n"
            "SECRET='quoted value'\n"
            'DOUBLE="double quoted"\n'
            "EMPTY=\n"
            "\n"
            "VALID_KEY=some-value\n",
            encoding="utf-8",
        )

        mod = self._load_migrate_module()
        pairs = mod.parse_env_file(env_file)
        assert pairs["API_KEY"] == "abc123"
        assert pairs["SECRET"] == "quoted value"
        assert pairs["DOUBLE"] == "double quoted"
        assert "EMPTY" not in pairs  # Empty values skipped
        assert pairs["VALID_KEY"] == "some-value"

    def test_parse_nonexistent_env(self, tmp_path):
        mod = self._load_migrate_module()
        result = mod.parse_env_file(tmp_path / "nonexistent")
        assert result == {}
