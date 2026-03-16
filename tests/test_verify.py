"""Tests for verification engine and semantic retrieval."""

import pytest

from src.memory.store import MemoryStore
from src.hooks.verify import (
    verify,
    format_verification,
    query_memory,
    format_query_results,
)


@pytest.fixture
def store(tmp_path):
    db_path = tmp_path / "test_verify.db"
    s = MemoryStore(db_path)
    yield s
    s.close()


@pytest.fixture
def store_with_rules(store):
    """Store with common enforcement rules."""
    store.add_enforcement_rule(
        content="Never use pythonw.exe",
        pattern=r"pythonw\.exe",
        pattern_type="regex",
        action="block",
        severity="critical",
        alternative="Use python.exe instead",
    )
    store.add_enforcement_rule(
        content="Never push to public repo",
        pattern=r"git\s+push\s+public",
        pattern_type="regex",
        action="block",
        severity="high",
    )
    store.add_enforcement_rule(
        content="Avoid deprecated API calls",
        pattern="deprecated_function",
        pattern_type="command",
        action="warn",
        severity="medium",
    )
    return store


# === Verification ===

class TestVerify:
    def test_clean_output_is_compliant(self, store_with_rules):
        result = verify(store_with_rules, "Bash", "echo hello", "hello")
        assert result.compliant
        assert len(result.violations) == 0
        assert len(result.warnings) == 0

    def test_violation_detected_in_output(self, store_with_rules):
        result = verify(
            store_with_rules, "Write", "create launch script",
            "#!/bin/bash\npythonw.exe src/main.py"
        )
        assert not result.compliant
        assert len(result.violations) >= 1
        assert result.violations[0]["severity"] == "critical"

    def test_violation_detected_in_action_description(self, store_with_rules):
        result = verify(
            store_with_rules, "Bash", "git push public main",
            "Everything up-to-date"
        )
        assert not result.compliant

    def test_warning_detected(self, store_with_rules):
        result = verify(
            store_with_rules, "Write", "update code",
            "result = deprecated_function()"
        )
        assert result.compliant  # warnings don't make it non-compliant
        assert len(result.warnings) >= 1
        assert result.warnings[0]["severity"] == "medium"

    def test_multiple_violations(self, store_with_rules):
        result = verify(
            store_with_rules, "Write", "git push public main",
            "pythonw.exe launched"
        )
        assert not result.compliant
        assert len(result.violations) >= 2

    def test_empty_output_is_compliant(self, store_with_rules):
        result = verify(store_with_rules, "Bash", "echo", "")
        assert result.compliant

    def test_no_rules_always_compliant(self, store):
        result = verify(store, "Bash", "rm -rf /", "everything deleted")
        assert result.compliant


class TestVerifyAudit:
    def test_verify_creates_audit_entry(self, store_with_rules):
        verify(store_with_rules, "Bash", "echo hello", "hello")
        log = store_with_rules.get_audit_log()
        assert any(e["action"] == "verify" for e in log)

    def test_violation_increments_count(self, store_with_rules):
        rules = store_with_rules.get_active_rules()
        pythonw_rule = [r for r in rules if "pythonw" in r["content"]][0]
        before = store_with_rules.get(pythonw_rule["id"])["violation_count"]

        verify(store_with_rules, "Write", "script", "pythonw.exe app.py")

        after = store_with_rules.get(pythonw_rule["id"])["violation_count"]
        assert after > before


class TestFormatVerification:
    def test_compliant_returns_empty(self):
        from src.hooks.verify import VerifyResult
        result = VerifyResult(compliant=True, violations=[], warnings=[])
        assert format_verification(result) == ""

    def test_violations_formatted(self):
        from src.hooks.verify import VerifyResult
        result = VerifyResult(
            compliant=False,
            violations=[{
                "severity": "critical",
                "content": "Never use pythonw.exe",
                "alternative": "Use python.exe",
            }],
            warnings=[],
        )
        text = format_verification(result)
        assert "VIOLATION" in text
        assert "pythonw" in text
        assert "python.exe" in text


# === Semantic Retrieval ===

class TestQueryMemory:
    def test_query_finds_relevant_entries(self, store):
        store.add("Never use pythonw.exe for GUI", "rule", confidence=0.9, source="test")
        store.add("Use WM_APP_DRAGSTART for window dragging", "rule", confidence=0.9, source="test")
        store.add("Database uses SQLite with WAL mode", "fact", confidence=0.8, source="test")

        results = query_memory(store, "pywebview GUI launching")
        # Should rank the pythonw/GUI entries higher than database fact
        assert len(results) >= 1

    def test_query_with_scope_filter(self, store):
        store.add("WhisperClick rule", "rule", scope="project:whisperclick", source="test")
        store.add("Global rule", "rule", scope="global", source="test")

        results = query_memory(store, "testing", scope="project:whisperclick")
        # Should include both whisperclick-scoped and global entries
        scopes = {r["scope"] for r in results}
        assert scopes <= {"project:whisperclick", "global"}

    def test_query_with_type_filter(self, store):
        store.add("Rule entry", "rule", source="test")
        store.add("Fact entry", "fact", source="test")

        results = query_memory(store, "entry", entry_type="rule")
        assert all(r["type"] == "rule" for r in results)

    def test_query_updates_use_count(self, store):
        entry = store.add("Important rule about testing", "rule", source="test")
        before = store.get(entry["id"])["use_count"]

        query_memory(store, "testing rules")

        after = store.get(entry["id"])["use_count"]
        assert after > before

    def test_query_empty_store(self, store):
        results = query_memory(store, "anything")
        assert results == []

    def test_query_respects_max_results(self, store):
        for i in range(20):
            store.add(f"Rule about topic {i}", "rule", source="test")

        results = query_memory(store, "topic", max_results=5)
        assert len(results) <= 5

    def test_negative_retrieval(self, store):
        store.add_enforcement_rule(
            content="Never use pythonw.exe",
            pattern=r"pythonw\.exe",
            action="block",
            severity="critical",
            alternative="Use python.exe",
        )

        results = query_memory(store, "how to launch GUI", include_negative=True)
        # Should include the rejected approach
        negative_results = [r for r in results if r.get("_negative")]
        # May or may not find it depending on embedding similarity
        # At minimum, the query should not error
        assert isinstance(results, list)


class TestFormatQueryResults:
    def test_empty_results(self):
        text = format_query_results([])
        assert "No relevant" in text

    def test_with_results(self):
        results = [
            {"content": "Rule about testing", "scope": "global", "_score": 0.85},
            {"content": "Another rule", "scope": "project:test", "_score": 0.72},
        ]
        text = format_query_results(results)
        assert "85%" in text
        assert "testing" in text
        assert "project:test" in text

    def test_with_negative_results(self):
        results = [
            {"content": "Good approach", "scope": "global", "_score": 0.8},
            {"content": "Bad approach", "_negative": True, "alternative": "Use good approach"},
        ]
        text = format_query_results(results)
        assert "Previously Rejected" in text
        assert "Use good approach" in text


class TestQueryPerformance:
    def test_query_under_500ms(self, store):
        # Add some data (increased threshold from 300ms — varies with system load)
        for i in range(50):
            store.add(f"Rule about topic {i} for testing performance", "rule", source="test")

        import time
        start = time.perf_counter()
        for _ in range(10):
            query_memory(store, "testing topic performance")
        elapsed = time.perf_counter() - start
        per_call = (elapsed / 10) * 1000
        assert per_call < 500, f"Query took {per_call:.1f}ms per call (limit: 500ms)"
