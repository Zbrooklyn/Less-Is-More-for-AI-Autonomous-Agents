"""File watcher — emits FILE_CHANGE events via watchdog."""

import os
from threading import Thread
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from src.daemon.events import EventBus, DaemonEvent, EventType


class _Handler(FileSystemEventHandler):
    """Translates watchdog events into DaemonEvents on the bus."""

    _CHANGE_MAP = {
        "created": "created",
        "modified": "modified",
        "deleted": "deleted",
        "moved": "moved",
    }

    def __init__(self, event_bus: EventBus, base_paths: list[str]):
        super().__init__()
        self._bus = event_bus
        # Normalise base paths so we can compute relative paths later
        self._base_paths = [os.path.normpath(p) for p in base_paths]

    def _relative(self, abs_path: str) -> str:
        """Return a path relative to the closest watched root, or the abs path."""
        norm = os.path.normpath(abs_path)
        for base in self._base_paths:
            if norm.startswith(base):
                rel = os.path.relpath(norm, base)
                return rel
        return abs_path

    def _emit(self, event: FileSystemEvent, change_type: str):
        rel = self._relative(event.src_path)
        self._bus.emit(
            DaemonEvent(
                event_type=EventType.FILE_CHANGE,
                source="file_watcher",
                payload={"path": rel, "change_type": change_type},
                dedupe_key=f"file:{rel}",
            )
        )

    def on_created(self, event: FileSystemEvent):
        if not event.is_directory:
            self._emit(event, "created")

    def on_modified(self, event: FileSystemEvent):
        if not event.is_directory:
            self._emit(event, "modified")

    def on_deleted(self, event: FileSystemEvent):
        if not event.is_directory:
            self._emit(event, "deleted")

    def on_moved(self, event: FileSystemEvent):
        if not event.is_directory:
            self._emit(event, "moved")


class FileWatcher:
    """Watch filesystem paths and emit FILE_CHANGE events."""

    def __init__(self, event_bus: EventBus, paths: list[str]):
        self._bus = event_bus
        self._paths = paths
        self._observer = Observer()
        self._handler = _Handler(event_bus, paths)

    def start(self):
        """Start watching in a background thread."""
        for path in self._paths:
            self._observer.schedule(self._handler, path, recursive=True)
        self._observer.start()

    def stop(self):
        """Stop the observer."""
        self._observer.stop()
        self._observer.join(timeout=5)
