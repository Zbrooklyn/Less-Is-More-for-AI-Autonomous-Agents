"""Scheduler — emits recurring TIMER events at configurable intervals."""

import time
from dataclasses import dataclass, field
from threading import Thread, Event as ThreadEvent, Lock
from typing import Optional

from src.daemon.events import EventBus, DaemonEvent, EventType


@dataclass
class _TimerEntry:
    name: str
    interval: float  # seconds
    payload: dict = field(default_factory=dict)
    next_fire: float = 0.0  # epoch time


class Scheduler:
    """Schedule recurring timer events on the event bus."""

    def __init__(self, event_bus: EventBus):
        self._bus = event_bus
        self._timers: dict[str, _TimerEntry] = {}
        self._lock = Lock()
        self._stop_event = ThreadEvent()
        self._thread: Optional[Thread] = None

    def add(self, name: str, interval_seconds: float, payload: dict | None = None):
        """Add or replace a recurring timer."""
        with self._lock:
            self._timers[name] = _TimerEntry(
                name=name,
                interval=interval_seconds,
                payload=payload or {},
                next_fire=time.time() + interval_seconds,
            )

    def remove(self, name: str):
        """Remove a timer by name."""
        with self._lock:
            self._timers.pop(name, None)

    def list_timers(self) -> list[dict]:
        """Return info about all active timers."""
        with self._lock:
            return [
                {
                    "name": t.name,
                    "interval": t.interval,
                    "next_fire": t.next_fire,
                }
                for t in self._timers.values()
            ]

    def start(self):
        """Start the scheduler check loop in a background thread."""
        self._stop_event.clear()
        self._thread = Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the scheduler."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        self._thread = None

    def _run(self):
        while not self._stop_event.is_set():
            now = time.time()
            with self._lock:
                ready = [
                    t for t in self._timers.values() if now >= t.next_fire
                ]
            for entry in ready:
                self._bus.emit(
                    DaemonEvent(
                        event_type=EventType.TIMER,
                        source=f"scheduler:{entry.name}",
                        payload=entry.payload,
                    )
                )
                with self._lock:
                    # Only reschedule if the timer is still registered
                    if entry.name in self._timers:
                        self._timers[entry.name].next_fire = now + entry.interval

            # Short sleep to avoid busy-wait but stay responsive
            self._stop_event.wait(timeout=0.05)
