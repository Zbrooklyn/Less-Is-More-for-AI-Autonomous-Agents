"""Tests for seed-rules script and reasoning backend."""

import pytest

from src.memory.store import MemoryStore
from src.daemon.reasoning import ReasoningBackend, _local_reasoning, ReasoningResult


@pytest.fixture
def store(tmp_path):
    db_path = tmp_path / "test_seed.db"
    s = MemoryStore(db_path)
    yield s
    s.close()


# === Seed Rules ===

class TestSeedRules:
    def _load_seed_module(self):
        import importlib.util
        import sys as _sys
        from pathlib import Path
        project_root = str(Path(__file__).parent.parent)
        if project_root not in _sys.path:
            _sys.path.insert(0, project_root)

        spec = importlib.util.spec_from_file_location(
            "seed_rules",
            str(Path(__file__).parent.parent / "scripts" / "seed-rules.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_seed_adds_rules(self, store):
        mod = self._load_seed_module()
        added = mod.seed_rules(store)
        assert added == 10  # 10 default rules

        rules = store.get_active_rules()
        assert len(rules) == 10

    def test_seed_idempotent(self, store):
        mod = self._load_seed_module()
        mod.seed_rules(store)
        added_again = mod.seed_rules(store)
        assert added_again == 0  # No duplicates

    def test_seed_includes_pythonw(self, store):
        mod = self._load_seed_module()
        mod.seed_rules(store)

        rules = store.get_active_rules()
        pythonw_rules = [r for r in rules if "pythonw" in r["content"]]
        assert len(pythonw_rules) == 1
        assert pythonw_rules[0]["action"] == "block"
        assert pythonw_rules[0]["severity"] == "critical"

    def test_seed_includes_git_push_public(self, store):
        mod = self._load_seed_module()
        mod.seed_rules(store)

        rules = store.get_active_rules()
        push_rules = [r for r in rules if "public repo" in r["content"]]
        assert len(push_rules) == 1
        assert push_rules[0]["action"] == "block"

    def test_seeded_rules_enforce_correctly(self, store):
        """Integration: seed → enforce should actually block."""
        mod = self._load_seed_module()
        mod.seed_rules(store)

        from src.hooks.enforce import enforce
        result = enforce(store, "Bash", "pythonw.exe test.py")
        assert not result.allowed
        assert result.action == "block"

        result2 = enforce(store, "Bash", "python.exe test.py")
        assert result2.allowed


# === Reasoning Backend ===

class TestLocalReasoning:
    def test_test_related_returns_run_tests(self):
        result = _local_reasoning("should we run the tests?", {})
        assert result.decision == "run_tests"
        assert result.model == "local-rules"

    def test_deploy_returns_alert(self):
        result = _local_reasoning("deploy to production", {})
        assert result.decision == "alert_user"

    def test_delete_returns_propose(self):
        result = _local_reasoning("delete old log files", {})
        assert result.decision == "propose"

    def test_update_returns_execute(self):
        result = _local_reasoning("update the dependency versions", {})
        assert result.decision == "execute"

    def test_unknown_defaults_to_propose(self):
        result = _local_reasoning("something completely unrelated", {})
        assert result.decision == "propose"
        assert result.confidence < 0.5


class TestReasoningBackend:
    def test_local_backend_available(self):
        backend = ReasoningBackend()
        assert "local" in backend.available_backends

    def test_local_reason(self):
        backend = ReasoningBackend()
        result = backend.reason("run tests please", {}, backend="local")
        assert result.decision == "run_tests"

    def test_unknown_backend(self):
        backend = ReasoningBackend()
        result = backend.reason("test", {}, backend="nonexistent")
        assert result.confidence == 0.0
        assert "not registered" in result.reasoning

    def test_register_custom_backend(self):
        backend = ReasoningBackend()

        def custom(question, context):
            return ReasoningResult(
                decision="custom_action",
                confidence=1.0,
                reasoning="custom logic",
                model="custom",
            )

        backend.register("custom", custom)
        result = backend.reason("anything", {}, backend="custom")
        assert result.decision == "custom_action"
        assert result.model == "custom"
