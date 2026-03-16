"""Tests for the enforcement engine — pre/post tool call gates."""

import pytest

from src.memory.store import MemoryStore
from src.hooks.enforce import enforce, enforce_output, format_enforcement, EnforceResult


@pytest.fixture
def store(tmp_path):
    """Create a fresh store with enforcement rules."""
    db_path = tmp_path / "test_enforce.db"
    s = MemoryStore(db_path)
    yield s
    s.close()


@pytest.fixture
def store_with_rules(store):
    """Store pre-loaded with common enforcement rules."""
    store.add_enforcement_rule(
        content="Never use pythonw.exe — crashes silently with Qt/PySide6",
        pattern=r"pythonw\.exe",
        pattern_type="regex",
        action="block",
        severity="critical",
        alternative="Use python.exe instead",
    )
    store.add_enforcement_rule(
        content="Never push directly to public repo — leaks private files",
        pattern=r"git\s+push\s+public",
        pattern_type="regex",
        action="block",
        severity="critical",
        alternative="Use git push origin <branch>, then run tools/sync_public.sh",
    )
    store.add_enforcement_rule(
        content="Never use easy_drag=True — broken on multi-monitor DPI",
        pattern="easy_drag=True",
        pattern_type="command",
        action="block",
        severity="high",
        alternative="Use WM_APP_DRAGSTART pattern instead",
    )
    store.add_enforcement_rule(
        content="Warn about force push — dangerous, can overwrite upstream",
        pattern=r"git\s+push\s+.*--force",
        pattern_type="regex",
        action="warn",
        severity="medium",
        alternative="Use --force-with-lease for safer force pushing",
    )
    return store


class TestEnforceBlocking:
    """Test that blocked patterns are caught."""

    def test_pythonw_blocked(self, store_with_rules):
        result = enforce(store_with_rules, "Bash", "pythonw.exe src/main.py")
        assert not result.allowed
        assert result.action == "block"
        assert result.severity == "critical"
        assert "pythonw" in result.pattern

    def test_pythonw_case_insensitive(self, store_with_rules):
        result = enforce(store_with_rules, "Bash", "PYTHONW.EXE app.py")
        assert not result.allowed

    def test_git_push_public_blocked(self, store_with_rules):
        result = enforce(store_with_rules, "Bash", "git push public main")
        assert not result.allowed
        assert result.action == "block"
        assert "sync_public" in result.alternative

    def test_easy_drag_blocked(self, store_with_rules):
        result = enforce(store_with_rules, "Write", "window = webview.create_window('App', easy_drag=True)")
        assert not result.allowed
        assert result.action == "block"

    def test_easy_drag_in_edit_blocked(self, store_with_rules):
        result = enforce(store_with_rules, "Edit", "    easy_drag=True,")
        assert not result.allowed


class TestEnforceAllowing:
    """Test that legitimate commands pass through."""

    def test_normal_python_allowed(self, store_with_rules):
        result = enforce(store_with_rules, "Bash", "python.exe src/main.py")
        assert result.allowed
        assert result.action == "allow"

    def test_git_push_origin_allowed(self, store_with_rules):
        result = enforce(store_with_rules, "Bash", "git push origin main")
        assert result.allowed

    def test_normal_write_allowed(self, store_with_rules):
        result = enforce(store_with_rules, "Write", "def hello():\n    print('world')")
        assert result.allowed

    def test_empty_input_allowed(self, store_with_rules):
        result = enforce(store_with_rules, "Bash", "")
        assert result.allowed

    def test_no_rules_allows_everything(self, store):
        result = enforce(store, "Bash", "rm -rf /")
        assert result.allowed


class TestEnforceWarning:
    """Test warn actions (allowed but flagged)."""

    def test_force_push_warns(self, store_with_rules):
        result = enforce(store_with_rules, "Bash", "git push origin main --force")
        assert result.allowed  # warn allows but flags
        assert result.action == "warn"
        assert result.severity == "medium"
        assert "force-with-lease" in result.alternative


class TestEnforceOutput:
    """Test post-action output checking."""

    def test_output_with_blocked_pattern(self, store_with_rules):
        result = enforce_output(store_with_rules, "Write", "launch pythonw.exe for the GUI")
        assert not result.allowed
        assert result.action == "violation"

    def test_clean_output_allowed(self, store_with_rules):
        result = enforce_output(store_with_rules, "Bash", "Tests passed: 109/109")
        assert result.allowed


class TestEnforceAudit:
    """Test that enforcement actions are audited."""

    def test_block_creates_audit_entry(self, store_with_rules):
        enforce(store_with_rules, "Bash", "pythonw.exe test.py")
        log = store_with_rules.get_audit_log()
        enforce_entries = [e for e in log if e["action"] == "enforce"]
        assert len(enforce_entries) >= 1
        assert "block" in enforce_entries[0]["context"]

    def test_allow_creates_audit_entry(self, store_with_rules):
        enforce(store_with_rules, "Bash", "echo hello")
        log = store_with_rules.get_audit_log()
        enforce_entries = [e for e in log if e["action"] == "enforce"]
        assert len(enforce_entries) >= 1
        assert "allow" in enforce_entries[0]["context"]

    def test_violation_count_increments(self, store_with_rules):
        rules_before = store_with_rules.get_active_rules()
        pythonw_rule = [r for r in rules_before if "pythonw" in r["content"]][0]
        count_before = store_with_rules.get(pythonw_rule["id"])["violation_count"]

        enforce(store_with_rules, "Bash", "pythonw.exe app.py")

        count_after = store_with_rules.get(pythonw_rule["id"])["violation_count"]
        assert count_after == count_before + 1


class TestEnforceResult:
    """Test the EnforceResult dataclass."""

    def test_default_result(self):
        result = EnforceResult(allowed=True, action="allow")
        assert result.allowed
        assert result.rule_id is None
        assert result.alternative is None

    def test_blocked_result(self):
        result = EnforceResult(
            allowed=False,
            action="block",
            rule_id="abc",
            rule_content="No pythonw",
            severity="critical",
        )
        assert not result.allowed
        assert result.severity == "critical"


class TestFormatEnforcement:
    """Test human-readable formatting."""

    def test_format_allow_returns_empty(self):
        result = EnforceResult(allowed=True, action="allow")
        assert format_enforcement(result) == ""

    def test_format_block_includes_severity(self):
        result = EnforceResult(
            allowed=False,
            action="block",
            rule_content="Never use pythonw.exe",
            severity="critical",
            reason="Matched regex pattern: pythonw\\.exe",
            alternative="Use python.exe instead",
        )
        text = format_enforcement(result)
        assert "BLOCKED" in text
        assert "pythonw" in text
        assert "python.exe instead" in text

    def test_format_warn_includes_warning(self):
        result = EnforceResult(
            allowed=True,
            action="warn",
            rule_content="Force push is dangerous",
            severity="medium",
            reason="Matched pattern",
        )
        text = format_enforcement(result)
        assert "WARNING" in text


class TestEnforcePerformance:
    """Test that enforcement is fast enough for real-time use."""

    def test_enforce_under_100ms(self, store_with_rules):
        import time
        start = time.perf_counter()
        for _ in range(100):
            enforce(store_with_rules, "Bash", "echo hello world")
        elapsed = time.perf_counter() - start
        per_call = (elapsed / 100) * 1000  # ms
        assert per_call < 100, f"Enforcement took {per_call:.1f}ms per call (limit: 100ms)"
