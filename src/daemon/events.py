"""Event bus — collects events from file watchers, webhooks, timers, and manual triggers."""

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional
from queue import Queue, Empty
from threading import Thread, Event as ThreadEvent


class EventType(Enum):
    FILE_CHANGE = "file_change"
    GIT_PUSH = "git_push"
    WEBHOOK = "webhook"
    TIMER = "timer"
    MANUAL = "manual"
    SYSTEM = "system"


class Priority(Enum):
    CRITICAL = 0   # Wake agent now
    NORMAL = 1     # Batch processing
    LOW = 2        # Log only


@dataclass
class DaemonEvent:
    """A single event in the event bus."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType = EventType.MANUAL
    source: str = ""
    payload: dict = field(default_factory=dict)
    priority: Priority = Priority.NORMAL
    timestamp: float = field(default_factory=time.time)
    dedupe_key: Optional[str] = None  # For deduplication


class EventBus:
    """
    Central event bus. Producers emit events, consumers process them.
    Thread-safe via Queue.
    """

    def __init__(self, max_size: int = 1000):
        self._queue: Queue[DaemonEvent] = Queue(maxsize=max_size)
        self._handlers: dict[EventType, list[Callable]] = {}
        self._recent_dedupe_keys: dict[str, float] = {}
        self._dedupe_window: float = 5.0  # seconds
        self._running = False
        self._stop_event = ThreadEvent()
        self._worker: Optional[Thread] = None
        self._processed_count = 0
        self._dropped_count = 0

    def emit(self, event: DaemonEvent) -> bool:
        """
        Emit an event to the bus. Returns True if accepted, False if deduplicated/dropped.
        """
        # Deduplication check
        if event.dedupe_key:
            now = time.time()
            last_seen = self._recent_dedupe_keys.get(event.dedupe_key, 0)
            if now - last_seen < self._dedupe_window:
                self._dropped_count += 1
                return False
            self._recent_dedupe_keys[event.dedupe_key] = now

        try:
            self._queue.put_nowait(event)
            return True
        except Exception:
            self._dropped_count += 1
            return False

    def subscribe(self, event_type: EventType, handler: Callable[[DaemonEvent], None]):
        """Register a handler for an event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def process_one(self, timeout: float = 1.0) -> Optional[DaemonEvent]:
        """Process a single event from the queue. Returns the event or None."""
        try:
            event = self._queue.get(timeout=timeout)
        except Empty:
            return None

        handlers = self._handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                pass  # Handlers should not crash the bus

        self._processed_count += 1
        return event

    def start(self):
        """Start background processing thread."""
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._worker = Thread(target=self._run_loop, daemon=True)
        self._worker.start()

    def stop(self, timeout: float = 5.0):
        """Stop background processing."""
        self._running = False
        self._stop_event.set()
        if self._worker and self._worker.is_alive():
            self._worker.join(timeout=timeout)
        self._worker = None

    def _run_loop(self):
        """Main processing loop."""
        while not self._stop_event.is_set():
            self.process_one(timeout=0.5)

    @property
    def pending(self) -> int:
        return self._queue.qsize()

    @property
    def stats(self) -> dict:
        return {
            "pending": self.pending,
            "processed": self._processed_count,
            "dropped": self._dropped_count,
            "running": self._running,
            "handlers": {k.value: len(v) for k, v in self._handlers.items()},
        }

    def drain(self) -> list[DaemonEvent]:
        """Drain all pending events without processing. For testing."""
        events = []
        while not self._queue.empty():
            try:
                events.append(self._queue.get_nowait())
            except Empty:
                break
        return events
