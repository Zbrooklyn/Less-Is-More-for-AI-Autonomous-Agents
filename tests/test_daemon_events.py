"""Tests for daemon event bus and triage engine."""

import time

import pytest

from src.daemon.events import EventBus, DaemonEvent, EventType, Priority
from src.daemon.triage import triage, batch_triage, TriageResult


# === Event Bus ===

class TestEventBus:
    def test_emit_and_process(self):
        bus = EventBus()
        event = DaemonEvent(event_type=EventType.MANUAL, source="test")
        assert bus.emit(event) is True
        assert bus.pending == 1

        processed = bus.process_one(timeout=1.0)
        assert processed is not None
        assert processed.id == event.id
        assert bus.pending == 0

    def test_empty_process_returns_none(self):
        bus = EventBus()
        result = bus.process_one(timeout=0.1)
        assert result is None

    def test_subscribe_and_handle(self):
        bus = EventBus()
        received = []

        def handler(event):
            received.append(event)

        bus.subscribe(EventType.FILE_CHANGE, handler)
        event = DaemonEvent(event_type=EventType.FILE_CHANGE, source="test")
        bus.emit(event)
        bus.process_one(timeout=1.0)

        assert len(received) == 1
        assert received[0].id == event.id

    def test_handler_for_wrong_type_not_called(self):
        bus = EventBus()
        received = []

        bus.subscribe(EventType.FILE_CHANGE, lambda e: received.append(e))
        event = DaemonEvent(event_type=EventType.TIMER, source="test")
        bus.emit(event)
        bus.process_one(timeout=1.0)

        assert len(received) == 0

    def test_multiple_handlers(self):
        bus = EventBus()
        counts = {"a": 0, "b": 0}

        bus.subscribe(EventType.MANUAL, lambda e: counts.update(a=counts["a"] + 1))
        bus.subscribe(EventType.MANUAL, lambda e: counts.update(b=counts["b"] + 1))

        bus.emit(DaemonEvent(event_type=EventType.MANUAL))
        bus.process_one(timeout=1.0)

        assert counts["a"] == 1
        assert counts["b"] == 1

    def test_deduplication(self):
        bus = EventBus()
        e1 = DaemonEvent(event_type=EventType.FILE_CHANGE, dedupe_key="file:test.py")
        e2 = DaemonEvent(event_type=EventType.FILE_CHANGE, dedupe_key="file:test.py")

        assert bus.emit(e1) is True
        assert bus.emit(e2) is False  # duplicate within window
        assert bus.pending == 1

    def test_deduplication_expires(self):
        bus = EventBus()
        bus._dedupe_window = 0.1  # 100ms for testing

        e1 = DaemonEvent(event_type=EventType.FILE_CHANGE, dedupe_key="file:test.py")
        assert bus.emit(e1) is True

        time.sleep(0.15)  # Wait for dedupe window to expire

        e2 = DaemonEvent(event_type=EventType.FILE_CHANGE, dedupe_key="file:test.py")
        assert bus.emit(e2) is True
        assert bus.pending == 2

    def test_stats(self):
        bus = EventBus()
        bus.emit(DaemonEvent(event_type=EventType.MANUAL))
        bus.process_one(timeout=1.0)

        stats = bus.stats
        assert stats["processed"] == 1
        assert stats["pending"] == 0

    def test_drain(self):
        bus = EventBus()
        for _ in range(5):
            bus.emit(DaemonEvent(event_type=EventType.MANUAL))

        events = bus.drain()
        assert len(events) == 5
        assert bus.pending == 0

    def test_start_stop(self):
        bus = EventBus()
        received = []

        bus.subscribe(EventType.MANUAL, lambda e: received.append(e))
        bus.start()

        bus.emit(DaemonEvent(event_type=EventType.MANUAL))
        time.sleep(1.0)  # Give worker time to process

        bus.stop()
        assert len(received) >= 1
        assert not bus._running

    def test_handler_exception_doesnt_crash(self):
        bus = EventBus()
        good_results = []

        def bad_handler(event):
            raise ValueError("boom")

        def good_handler(event):
            good_results.append(event)

        bus.subscribe(EventType.MANUAL, bad_handler)
        bus.subscribe(EventType.MANUAL, good_handler)

        bus.emit(DaemonEvent(event_type=EventType.MANUAL))
        bus.process_one(timeout=1.0)

        # Good handler should still run
        assert len(good_results) == 1


# === Triage ===

class TestTriageFileChanges:
    def test_pyc_ignored(self):
        event = DaemonEvent(
            event_type=EventType.FILE_CHANGE,
            payload={"path": "src/__pycache__/module.cpython-312.pyc"},
        )
        result = triage(event)
        assert not result.accepted
        assert result.category == "noise"

    def test_python_file_accepted(self):
        event = DaemonEvent(
            event_type=EventType.FILE_CHANGE,
            payload={"path": "src/memory/store.py"},
        )
        result = triage(event)
        assert result.accepted
        assert result.category == "python_source"
        assert result.priority == Priority.NORMAL

    def test_claude_md_is_critical(self):
        event = DaemonEvent(
            event_type=EventType.FILE_CHANGE,
            payload={"path": "CLAUDE.md"},
        )
        result = triage(event)
        assert result.accepted
        assert result.priority == Priority.CRITICAL
        assert result.category == "agent_config"

    def test_hot_memory_is_critical(self):
        event = DaemonEvent(
            event_type=EventType.FILE_CHANGE,
            payload={"path": "shared/memory/hot-memory.md"},
        )
        result = triage(event)
        assert result.accepted
        assert result.priority == Priority.CRITICAL

    def test_env_file_is_critical(self):
        event = DaemonEvent(
            event_type=EventType.FILE_CHANGE,
            payload={"path": ".env"},
        )
        result = triage(event)
        assert result.accepted
        assert result.priority == Priority.CRITICAL
        assert result.category == "secrets"

    def test_node_modules_ignored(self):
        event = DaemonEvent(
            event_type=EventType.FILE_CHANGE,
            payload={"path": "node_modules/foo/bar.js"},
        )
        result = triage(event)
        assert not result.accepted

    def test_unknown_file_low_priority(self):
        event = DaemonEvent(
            event_type=EventType.FILE_CHANGE,
            payload={"path": "data/some_random_file.xyz"},
        )
        result = triage(event)
        assert result.accepted
        assert result.priority == Priority.LOW

    def test_git_internal_ignored(self):
        event = DaemonEvent(
            event_type=EventType.FILE_CHANGE,
            payload={"path": ".git/objects/ab/cdef123"},
        )
        result = triage(event)
        assert not result.accepted


class TestTriageOtherEvents:
    def test_git_push_accepted(self):
        event = DaemonEvent(event_type=EventType.GIT_PUSH, source="test")
        result = triage(event)
        assert result.accepted
        assert result.priority == Priority.NORMAL

    def test_manual_is_critical(self):
        event = DaemonEvent(event_type=EventType.MANUAL, source="user")
        result = triage(event)
        assert result.accepted
        assert result.priority == Priority.CRITICAL

    def test_timer_is_low(self):
        event = DaemonEvent(event_type=EventType.TIMER, source="scheduler")
        result = triage(event)
        assert result.accepted
        assert result.priority == Priority.LOW

    def test_webhook_accepted(self):
        event = DaemonEvent(event_type=EventType.WEBHOOK, source="github")
        result = triage(event)
        assert result.accepted
        assert result.priority == Priority.NORMAL


class TestBatchTriage:
    def test_batch_sorts_by_priority(self):
        events = [
            DaemonEvent(event_type=EventType.TIMER, source="low"),
            DaemonEvent(event_type=EventType.MANUAL, source="critical"),
            DaemonEvent(event_type=EventType.GIT_PUSH, source="normal"),
        ]
        results = batch_triage(events)

        # Critical should come first
        priorities = [r[1].priority for r in results]
        assert priorities[0] == Priority.CRITICAL

    def test_batch_noise_last(self):
        events = [
            DaemonEvent(event_type=EventType.FILE_CHANGE, payload={"path": "test.pyc"}),
            DaemonEvent(event_type=EventType.MANUAL, source="user"),
        ]
        results = batch_triage(events)

        # Accepted events before rejected
        assert results[0][1].accepted
        assert not results[-1][1].accepted


class TestTriageResult:
    def test_has_cost_estimate(self):
        event = DaemonEvent(event_type=EventType.FILE_CHANGE, payload={"path": "test.py"})
        result = triage(event)
        assert result.estimated_cost >= 0
