"""Tests for daemon event sources: FileWatcher, WebhookListener, Scheduler."""

import json
import os
import socket
import time
import urllib.request
import urllib.error

import pytest

from src.daemon.events import EventBus, EventType, DaemonEvent
from src.daemon.watcher import FileWatcher
from src.daemon.webhook import WebhookListener
from src.daemon.scheduler import Scheduler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _free_port() -> int:
    """Find a random available TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _collect_events(bus: EventBus, timeout: float = 2.0, min_count: int = 1) -> list[DaemonEvent]:
    """Drain events from a bus, waiting up to *timeout* seconds for *min_count* events."""
    events: list[DaemonEvent] = []
    deadline = time.time() + timeout
    while time.time() < deadline:
        ev = bus.process_one(timeout=0.1)
        if ev:
            events.append(ev)
        if len(events) >= min_count:
            break
    return events


# ===========================================================================
# FileWatcher tests
# ===========================================================================

class TestFileWatcher:

    def test_create_file_emits_event(self, tmp_path):
        """Creating a file in a watched directory should emit a FILE_CHANGE event."""
        bus = EventBus()
        watcher = FileWatcher(bus, paths=[str(tmp_path)])
        watcher.start()
        try:
            # Give the observer time to spin up
            time.sleep(0.3)
            # Create a file
            test_file = tmp_path / "hello.txt"
            test_file.write_text("world")
            events = _collect_events(bus, timeout=3.0, min_count=1)
            assert len(events) >= 1
            ev = events[0]
            assert ev.event_type == EventType.FILE_CHANGE
            assert ev.source == "file_watcher"
            assert ev.payload["change_type"] in ("created", "modified")
            assert "hello.txt" in ev.payload["path"]
        finally:
            watcher.stop()

    def test_pyc_files_still_emit(self, tmp_path):
        """.pyc files should still emit — triage handles filtering, not the watcher."""
        bus = EventBus()
        # Use a longer dedupe window bypass by using a fresh bus
        bus._dedupe_window = 0.0  # disable dedupe for this test
        watcher = FileWatcher(bus, paths=[str(tmp_path)])
        watcher.start()
        try:
            time.sleep(0.3)
            pyc_file = tmp_path / "module.pyc"
            pyc_file.write_bytes(b"\x00\x00\x00\x00")
            events = _collect_events(bus, timeout=3.0, min_count=1)
            assert len(events) >= 1
            assert any("module.pyc" in e.payload.get("path", "") for e in events)
        finally:
            watcher.stop()

    def test_start_stop(self, tmp_path):
        """Watcher should start and stop without errors."""
        bus = EventBus()
        watcher = FileWatcher(bus, paths=[str(tmp_path)])
        watcher.start()
        time.sleep(0.2)
        watcher.stop()
        # After stop, creating a file should NOT produce events
        (tmp_path / "after_stop.txt").write_text("nope")
        time.sleep(0.5)
        events = bus.drain()
        # Should be empty or at most contain events from before stop
        file_events = [e for e in events if "after_stop.txt" in e.payload.get("path", "")]
        assert len(file_events) == 0


# ===========================================================================
# WebhookListener tests
# ===========================================================================

class TestWebhookListener:

    def test_post_webhook_emits_event(self):
        """POST to /webhook with JSON should emit a WEBHOOK event."""
        bus = EventBus()
        port = _free_port()
        listener = WebhookListener(bus, port=port)
        listener.start()
        try:
            time.sleep(0.3)
            payload = json.dumps({"source": "github", "action": "push"}).encode()
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/webhook",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            resp = urllib.request.urlopen(req, timeout=5)
            assert resp.status == 200

            events = _collect_events(bus, timeout=2.0, min_count=1)
            assert len(events) >= 1
            ev = events[0]
            assert ev.event_type == EventType.WEBHOOK
            assert ev.source == "github"
            assert ev.payload["action"] == "push"
        finally:
            listener.stop()

    def test_get_health_returns_200(self):
        """GET /health should return 200."""
        bus = EventBus()
        port = _free_port()
        listener = WebhookListener(bus, port=port)
        listener.start()
        try:
            time.sleep(0.3)
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/health",
                method="GET",
            )
            resp = urllib.request.urlopen(req, timeout=5)
            assert resp.status == 200
            body = json.loads(resp.read())
            assert body["status"] == "ok"
        finally:
            listener.stop()

    def test_start_stop(self):
        """Listener should start and stop cleanly."""
        bus = EventBus()
        port = _free_port()
        listener = WebhookListener(bus, port=port)
        listener.start()
        time.sleep(0.2)
        listener.stop()

        # After stop, the port should be unreachable
        with pytest.raises((urllib.error.URLError, ConnectionError, OSError)):
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/health",
                method="GET",
            )
            urllib.request.urlopen(req, timeout=2)


# ===========================================================================
# Scheduler tests
# ===========================================================================

class TestScheduler:

    def test_timer_fires_after_interval(self):
        """A timer should fire after its interval elapses."""
        bus = EventBus()
        scheduler = Scheduler(bus)
        scheduler.add("heartbeat", interval_seconds=0.2, payload={"msg": "ping"})
        scheduler.start()
        try:
            events = _collect_events(bus, timeout=2.0, min_count=1)
            assert len(events) >= 1
            ev = events[0]
            assert ev.event_type == EventType.TIMER
            assert ev.source == "scheduler:heartbeat"
            assert ev.payload["msg"] == "ping"
        finally:
            scheduler.stop()

    def test_remove_timer_stops_firing(self):
        """After removing a timer, it should stop emitting events."""
        bus = EventBus()
        scheduler = Scheduler(bus)
        scheduler.add("temp", interval_seconds=0.15)
        scheduler.start()
        try:
            # Wait for at least one fire
            events = _collect_events(bus, timeout=2.0, min_count=1)
            assert len(events) >= 1

            # Remove the timer and drain any pending events
            scheduler.remove("temp")
            time.sleep(0.1)
            bus.drain()

            # Now wait a bit and confirm no new events
            time.sleep(0.5)
            remaining = bus.drain()
            timer_events = [e for e in remaining if e.source == "scheduler:temp"]
            assert len(timer_events) == 0
        finally:
            scheduler.stop()

    def test_list_timers(self):
        """list_timers() should return info about all registered timers."""
        bus = EventBus()
        scheduler = Scheduler(bus)
        scheduler.add("alpha", interval_seconds=10)
        scheduler.add("beta", interval_seconds=30, payload={"x": 1})

        timers = scheduler.list_timers()
        names = {t["name"] for t in timers}
        assert names == {"alpha", "beta"}

        for t in timers:
            assert "interval" in t
            assert "next_fire" in t

        # Remove one
        scheduler.remove("alpha")
        timers = scheduler.list_timers()
        assert len(timers) == 1
        assert timers[0]["name"] == "beta"
