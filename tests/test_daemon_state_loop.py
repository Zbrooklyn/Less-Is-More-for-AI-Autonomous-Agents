"""Tests for daemon state, authority, and full loop."""

import time

import pytest

from src.daemon.events import EventBus, DaemonEvent, EventType, Priority
from src.daemon.triage import triage
from src.daemon.state import DaemonState, AuthorityTier, DaemonTask
from src.daemon.loop import DaemonLoop, LoopConfig, CycleReport


@pytest.fixture
def state(tmp_path):
    db_path = tmp_path / "test_state.db"
    s = DaemonState(db_path)
    yield s
    s.close()


@pytest.fixture
def bus():
    return EventBus()


@pytest.fixture
def loop(bus, state):
    config = LoopConfig(poll_interval=0.1, batch_size=10)
    return DaemonLoop(bus, state, config)


# === State Management ===

class TestDaemonState:
    def test_create_task(self, state):
        task = state.create_task("Test task", AuthorityTier.AUTONOMOUS)
        assert task.title == "Test task"
        assert task.status == "pending"
        assert task.authority_tier == AuthorityTier.AUTONOMOUS

    def test_get_task(self, state):
        task = state.create_task("Test", AuthorityTier.AUTONOMOUS)
        retrieved = state.get_task(task.id)
        assert retrieved is not None
        assert retrieved.title == "Test"

    def test_get_nonexistent(self, state):
        assert state.get_task("fake-id") is None

    def test_update_task_status(self, state):
        task = state.create_task("Test", AuthorityTier.AUTONOMOUS)
        updated = state.update_task(task.id, status="completed", result="done")
        assert updated.status == "completed"
        assert updated.result == "done"

    def test_list_tasks(self, state):
        state.create_task("Task 1", AuthorityTier.AUTONOMOUS)
        state.create_task("Task 2", AuthorityTier.PROPOSE_WAIT)
        state.create_task("Task 3", AuthorityTier.AUTONOMOUS)

        all_tasks = state.list_tasks()
        assert len(all_tasks) == 3

    def test_list_tasks_filtered(self, state):
        t1 = state.create_task("Task 1", AuthorityTier.AUTONOMOUS)
        t2 = state.create_task("Task 2", AuthorityTier.AUTONOMOUS)
        state.update_task(t1.id, status="completed")

        pending = state.list_tasks(status="pending")
        assert len(pending) == 1
        assert pending[0].id == t2.id

    def test_state_persists(self, tmp_path):
        db_path = tmp_path / "persist.db"

        s1 = DaemonState(db_path)
        s1.create_task("Persistent", AuthorityTier.AUTONOMOUS)
        s1.close()

        s2 = DaemonState(db_path)
        tasks = s2.list_tasks()
        assert len(tasks) == 1
        assert tasks[0].title == "Persistent"
        s2.close()


# === Authority ===

class TestAuthority:
    def test_tier1_autonomous(self, state):
        result = state.check_authority("run_tests", AuthorityTier.AUTONOMOUS)
        assert result["authorized"]
        assert result["action_required"] == "execute"

    def test_tier2_act_notify(self, state):
        result = state.check_authority("fix_lint", AuthorityTier.ACT_NOTIFY)
        assert result["authorized"]
        assert result["action_required"] == "execute_and_notify"

    def test_tier3_propose_wait(self, state):
        result = state.check_authority("code_change", AuthorityTier.PROPOSE_WAIT)
        assert not result["authorized"]
        assert result["action_required"] == "propose"

    def test_tier4_alert_only(self, state):
        result = state.check_authority("deploy", AuthorityTier.ALERT_ONLY)
        assert not result["authorized"]
        assert result["action_required"] == "alert"


# === Action Log ===

class TestActionLog:
    def test_log_action(self, state):
        action_id = state.log_action(
            action="test_run",
            authority=AuthorityTier.AUTONOMOUS,
            details="All 109 tests pass",
        )
        assert action_id is not None

        log = state.get_action_log()
        assert len(log) >= 1
        assert log[0]["action"] == "test_run"

    def test_log_with_task(self, state):
        task = state.create_task("Test", AuthorityTier.AUTONOMOUS)
        state.log_action(
            action="execute",
            authority=AuthorityTier.AUTONOMOUS,
            task_id=task.id,
            approved=True,
        )

        log = state.get_action_log()
        assert log[0]["task_id"] == task.id


# === Config ===

class TestDaemonConfig:
    def test_set_get(self, state):
        state.set_config("poll_interval", "5.0")
        assert state.get_config("poll_interval") == "5.0"

    def test_get_default(self, state):
        assert state.get_config("nonexistent", "default") == "default"

    def test_get_none(self, state):
        assert state.get_config("nonexistent") is None

    def test_overwrite(self, state):
        state.set_config("key", "old")
        state.set_config("key", "new")
        assert state.get_config("key") == "new"


# === Full Daemon Loop ===

class TestDaemonLoop:
    def test_process_empty_cycle(self, loop):
        report = loop.process_cycle()
        assert report.events_processed == 0

    def test_process_low_priority_event(self, loop, bus):
        """Low priority events (timer) → Tier 1 (autonomous) → execute directly."""
        executed = []
        loop.register_action("timer", lambda e, t: executed.append(e) or "ok")

        bus.emit(DaemonEvent(event_type=EventType.TIMER, source="test"))
        report = loop.process_cycle()

        assert report.events_triaged == 1
        assert report.actions_executed == 1
        assert len(executed) == 1

    def test_process_normal_priority_event(self, loop, bus):
        """Normal events → Tier 2 (act + notify) → execute and log."""
        bus.emit(DaemonEvent(
            event_type=EventType.FILE_CHANGE,
            payload={"path": "src/test.py"},
        ))
        report = loop.process_cycle()

        assert report.events_triaged == 1
        assert report.actions_executed == 1

    def test_process_critical_event_creates_proposal(self, loop, bus, state):
        """Critical events → Tier 3 (propose) → create task, don't execute."""
        bus.emit(DaemonEvent(event_type=EventType.MANUAL, source="user"))
        report = loop.process_cycle()

        assert report.events_triaged == 1
        assert report.actions_proposed == 1
        assert report.actions_executed == 0

        # Should have created a task
        tasks = state.list_tasks(status="awaiting_approval")
        assert len(tasks) >= 1

    def test_noise_events_dropped(self, loop, bus):
        """Noise events (pyc files) are triaged and dropped."""
        bus.emit(DaemonEvent(
            event_type=EventType.FILE_CHANGE,
            payload={"path": "__pycache__/mod.cpython-312.pyc"},
        ))
        report = loop.process_cycle()

        assert report.events_triaged == 1
        assert report.events_dropped == 1
        assert report.events_processed == 0

    def test_cost_budget_limits_processing(self, loop, bus):
        """Events exceeding the cost budget are dropped."""
        loop.config.max_cost_per_cycle = 0.02  # Very low budget

        # Add many events
        for _ in range(10):
            bus.emit(DaemonEvent(event_type=EventType.GIT_PUSH, source="test"))

        report = loop.process_cycle()
        # Not all events should be processed due to budget
        assert report.events_dropped > 0

    def test_notification_callback(self, loop, bus):
        """Tier 2 events trigger notification callback."""
        notifications = []
        loop.config.notification_callback = lambda msg: notifications.append(msg)

        loop.register_action("python_source", lambda e, t: "fixed")
        bus.emit(DaemonEvent(
            event_type=EventType.FILE_CHANGE,
            payload={"path": "src/test.py"},
        ))
        report = loop.process_cycle()

        assert len(notifications) >= 1
        assert "fixed" in notifications[0]

    def test_action_handler_error_logged(self, loop, bus):
        """Errors in action handlers are caught and logged."""
        def bad_handler(e, t):
            raise ValueError("handler error")

        loop.register_action("timer", bad_handler)
        bus.emit(DaemonEvent(event_type=EventType.TIMER, source="test"))

        report = loop.process_cycle()
        assert len(report.errors) >= 1
        assert "handler error" in report.errors[0]

    def test_full_loop_start_stop(self, loop, bus):
        """Test the background loop starts and stops cleanly."""
        loop.start()
        assert loop._running

        bus.emit(DaemonEvent(event_type=EventType.TIMER, source="test"))
        time.sleep(0.5)

        loop.stop()
        assert not loop._running
        assert loop._cycle_count >= 1

    def test_stats(self, loop, bus):
        bus.emit(DaemonEvent(event_type=EventType.TIMER))
        loop.process_cycle()

        stats = loop.stats
        assert stats["cycles"] >= 1
        assert stats["total_processed"] >= 1

    def test_batch_processing(self, loop, bus):
        """Multiple events processed in one cycle."""
        for i in range(5):
            bus.emit(DaemonEvent(event_type=EventType.TIMER, source=f"test-{i}"))

        report = loop.process_cycle()
        assert report.events_triaged == 5

    def test_audit_trail(self, loop, bus, state):
        """Every action creates an audit entry."""
        bus.emit(DaemonEvent(event_type=EventType.TIMER, source="test"))
        loop.process_cycle()

        log = state.get_action_log()
        assert len(log) >= 1
