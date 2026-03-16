"""Webhook listener — lightweight HTTP server that converts POSTs into WEBHOOK events."""

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from typing import Optional

from src.daemon.events import EventBus, DaemonEvent, EventType


class _WebhookHandler(BaseHTTPRequestHandler):
    """HTTP request handler wired to an EventBus (set via server attribute)."""

    def do_POST(self):
        if self.path == "/webhook":
            try:
                length = int(self.headers.get("Content-Length", 0))
                raw = self.rfile.read(length)
                data = json.loads(raw) if raw else {}
            except (json.JSONDecodeError, ValueError):
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'{"error": "invalid json"}')
                return

            self.server.event_bus.emit(  # type: ignore[attr-defined]
                DaemonEvent(
                    event_type=EventType.WEBHOOK,
                    source=data.get("source", "webhook"),
                    payload=data,
                )
            )
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')
        else:
            self.send_response(404)
            self.end_headers()

    # Suppress default stderr logging so tests are quiet
    def log_message(self, format, *args):  # noqa: A002
        pass


class _BusHTTPServer(HTTPServer):
    """HTTPServer subclass that carries an event_bus reference."""

    event_bus: EventBus


class WebhookListener:
    """Start/stop an HTTP webhook listener that emits events to the bus."""

    def __init__(self, event_bus: EventBus, port: int = 9876):
        self._bus = event_bus
        self._port = port
        self._server: Optional[_BusHTTPServer] = None
        self._thread: Optional[Thread] = None

    def start(self):
        """Start the HTTP server in a background thread."""
        self._server = _BusHTTPServer(("127.0.0.1", self._port), _WebhookHandler)
        self._server.event_bus = self._bus
        self._thread = Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self):
        """Shutdown the HTTP server."""
        if self._server:
            self._server.shutdown()
        if self._thread:
            self._thread.join(timeout=5)
        self._server = None
        self._thread = None

    @property
    def port(self) -> int:
        return self._port
