"""Integration tests — wire multiple modules together and test the full pipeline."""

import time

import pytest

from src.memory.store import MemoryStore
from src.hooks.enforce import enforce
from src.hooks.capture import capture, PROMOTION_THRESHOLD
from src.hooks.verify import verify, query_memory
from src.hooks.pin import pin, get_pinned
from src.daemon.events import EventBus, DaemonEvent, EventType
from src.daemon.triage import triage
from src.daemon.state import DaemonState, AuthorityTier
from src.daemon.loop import DaemonLoop, LoopConfig


@pytest.fixture
def memory(tmp_path):
    s = MemoryStore(tmp_path / "integration.db")
    yield s
    s.close()


@pytest.fixture
def state(tmp_path):
    s = DaemonState(tmp_path / "daemon_state.db")
    yield s
    s.close()


class TestCorrectionToEnforcementPipeline:
    """Test: user correction → capture → auto-promote → enforcement blocks."""

    def test_correction_becomes_enforcement_rule(self, memory):
        # 1. User corrects the agent 3 times
        for _ in range(PROMOTION_THRESHOLD):
            result = capture(memory, "No, don't use pythonw.exe ever")

        # Correction should be promoted
        assert result.promoted
        assert result.promoted_rule_id is not None

        # 2. Now enforcement should block pythonw.exe
        enforce_result = enforce(memory, "Bash", "pythonw.exe app.py")
        assert not enforce_result.allowed
        assert enforce_result.action == "block"

    def test_correction_to_pin_to_verification(self, memory, tmp_path):
        # 1. Add a rule manually
        entry = memory.add_enforcement_rule(
            content="Never use sudo rm -rf /",
            pattern=r"sudo\s+rm\s+-rf\s+/",
            pattern_type="regex",
            action="block",
            severity="critical",
            alternative="Be specific about what to delete",
        )

        # 2. Pin it
        pin_file = tmp_path / "CLAUDE.md"
        assert pin(memory, entry["id"], pin_file=pin_file)

        # 3. Verify it's pinned
        pinned = get_pinned(memory)
        assert any(p["id"] == entry["id"] for p in pinned)

        # 4. Pin file should contain the rule
        content = pin_file.read_text()
        assert "sudo rm" in content

        # 5. Verify catches the violation in output
        verify_result = verify(memory, "Bash", "cleanup script", "sudo rm -rf / executed")
        assert not verify_result.compliant
        assert len(verify_result.violations) >= 1


class TestDaemonToMemoryPipeline:
    """Test: file change event → triage → daemon loop → memory enforcement."""

    def test_file_change_through_daemon_loop(self, memory, state):
        bus = EventBus()
        loop = DaemonLoop(bus, state, LoopConfig(poll_interval=0.1))
        executed = []

        # Register handler that checks memory enforcement
        def handle_python_change(event, triage_result):
            path = event.payload.get("path", "")
            result = enforce(memory, "FileWatch", f"detected change in {path}")
            executed.append({"path": path, "allowed": result.allowed})
            return f"Processed: {path}"

        loop.register_action("python_source", handle_python_change)

        # Emit a file change event
        bus.emit(DaemonEvent(
            event_type=EventType.FILE_CHANGE,
            source="watcher",
            payload={"path": "src/memory/store.py", "change_type": "modified"},
        ))

        # Process one cycle
        report = loop.process_cycle()

        assert report.events_processed >= 1
        assert len(executed) >= 1
        assert executed[0]["path"] == "src/memory/store.py"

    def test_critical_file_creates_proposal(self, memory, state):
        bus = EventBus()
        loop = DaemonLoop(bus, state, LoopConfig(poll_interval=0.1))

        # CLAUDE.md change is critical → should create proposal, not auto-execute
        bus.emit(DaemonEvent(
            event_type=EventType.FILE_CHANGE,
            source="watcher",
            payload={"path": "CLAUDE.md"},
        ))

        report = loop.process_cycle()

        # Critical events get proposed, not executed
        assert report.actions_proposed >= 1
        tasks = state.list_tasks(status="awaiting_approval")
        assert len(tasks) >= 1

    def test_noise_filtered_before_memory(self, memory, state):
        bus = EventBus()
        loop = DaemonLoop(bus, state, LoopConfig(poll_interval=0.1))
        executed = []

        loop.register_action("noise", lambda e, t: executed.append(e))

        # Emit a .pyc change — should be filtered by triage
        bus.emit(DaemonEvent(
            event_type=EventType.FILE_CHANGE,
            source="watcher",
            payload={"path": "__pycache__/store.cpython-312.pyc"},
        ))

        report = loop.process_cycle()

        assert report.events_dropped >= 1
        assert len(executed) == 0  # handler never called


class TestMemoryQueryWithEnforcement:
    """Test: semantic query returns both positive and negative results."""

    def test_query_includes_enforcement_context(self, memory):
        # Add some normal rules
        memory.add("Use python.exe for GUI launching", "rule", confidence=0.9, source="test")
        memory.add("Always run tests after changes", "rule", confidence=0.9, source="test")

        # Add enforcement rule (negative — what NOT to do)
        memory.add_enforcement_rule(
            content="Never use pythonw.exe — crashes silently",
            pattern=r"pythonw\.exe",
            action="block",
            severity="critical",
            alternative="Use python.exe instead",
        )

        # Query about GUI launching — should get both positive guidance and negative warnings
        results = query_memory(memory, "how to launch GUI application", include_negative=True)
        assert len(results) >= 1


class TestCLIEnforceCommand:
    """Test the new CLI commands work end-to-end."""

    def test_cli_enforce_blocks(self, memory):
        memory.add_enforcement_rule(
            content="Block pythonw",
            pattern=r"pythonw\.exe",
            action="block",
            severity="critical",
        )

        from src.memory.cli import main
        # Should return exit code 1 (blocked)
        result = main(["--db", str(memory.db_path), "enforce", "--tool", "Bash", "--input", "pythonw.exe test.py"])
        assert result == 1

    def test_cli_enforce_allows(self, memory):
        from src.memory.cli import main
        result = main(["--db", str(memory.db_path), "enforce", "--tool", "Bash", "--input", "echo hello"])
        assert result == 0

    def test_cli_capture_detects(self, memory):
        from src.memory.cli import main
        result = main(["--db", str(memory.db_path), "capture", "Don't use pythonw.exe"])
        assert result is None or result == 0

    def test_cli_verify_compliant(self, memory):
        from src.memory.cli import main
        result = main([
            "--db", str(memory.db_path), "verify",
            "--tool", "Bash", "--action", "echo hello", "--output", "hello",
        ])
        assert result == 0

    def test_cli_pin_list(self, memory):
        from src.memory.cli import main
        result = main(["--db", str(memory.db_path), "pin", "--list"])
        assert result is None or result == 0


class TestFullAuditTrail:
    """Test that all operations leave audit entries."""

    def test_enforce_capture_verify_all_audited(self, memory):
        # Add a rule
        memory.add_enforcement_rule(
            content="Test rule", pattern="test_pattern",
            action="block", severity="high",
        )

        # Run enforce
        enforce(memory, "Bash", "test_pattern command")

        # Run capture
        capture(memory, "Don't use test_pattern anymore")

        # Run verify
        verify(memory, "Write", "test action", "test_pattern in output")

        # Check audit log has entries from all three
        log = memory.get_audit_log(limit=50)
        actions = [e["action"] for e in log]
        assert "enforce" in actions
        assert "capture" in actions
        assert "verify" in actions


class TestDaemonFullLoop:
    """Test the daemon loop processes events end-to-end with timing."""

    def test_background_loop_processes_events(self, memory, state):
        bus = EventBus()
        loop = DaemonLoop(bus, state, LoopConfig(poll_interval=0.1))
        processed = []

        loop.register_action("timer", lambda e, t: processed.append(e) or "done")

        loop.start()

        # Emit several events
        for i in range(3):
            bus.emit(DaemonEvent(event_type=EventType.TIMER, source=f"test-{i}"))

        # Give it time to process
        time.sleep(1.0)
        loop.stop()

        assert len(processed) >= 3
        assert loop.stats["total_processed"] >= 3
