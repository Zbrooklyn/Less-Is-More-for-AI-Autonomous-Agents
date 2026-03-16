"""Daemon loop — the full event → triage → reason → act → verify → log pipeline."""

import time
from dataclasses import dataclass, field
from threading import Thread, Event as ThreadEvent
from typing import Callable, Optional

from src.daemon.events import EventBus, DaemonEvent, EventType, Priority
from src.daemon.triage import triage, TriageResult
from src.daemon.state import DaemonState, AuthorityTier


@dataclass
class LoopConfig:
    """Configuration for the daemon loop."""
    poll_interval: float = 1.0        # seconds between queue checks
    batch_size: int = 10              # max events to process per cycle
    max_cost_per_cycle: float = 0.50  # max $ to spend per cycle
    notification_callback: Optional[Callable] = None
    digest_interval: float = 86400.0  # seconds between digest generation (24h)
    digest_path: Optional[str] = None # path to write digest file


@dataclass
class CycleReport:
    """Report from a single processing cycle."""
    events_processed: int = 0
    events_triaged: int = 0
    events_dropped: int = 0
    actions_executed: int = 0
    actions_proposed: int = 0
    cost_estimate: float = 0.0
    errors: list = field(default_factory=list)


class DaemonLoop:
    """
    The main daemon loop. Connects:
    EventBus → Triage → State/Authority → Action → Audit
    """

    def __init__(
        self,
        event_bus: EventBus,
        state: DaemonState,
        config: Optional[LoopConfig] = None,
    ):
        self.bus = event_bus
        self.state = state
        self.config = config or LoopConfig()
        self._running = False
        self._stop_event = ThreadEvent()
        self._worker: Optional[Thread] = None
        self._action_handlers: dict[str, Callable] = {}
        self._cycle_count = 0
        self._total_processed = 0
        self._last_digest_time = time.time()
        self._pending_notifications: list[str] = []

    def register_action(self, category: str, handler: Callable[[DaemonEvent, TriageResult], Optional[str]]):
        """Register a handler for a triage category. Handler returns result string or None."""
        self._action_handlers[category] = handler

    def process_cycle(self) -> CycleReport:
        """Process one cycle: drain events → triage → execute within authority."""
        report = CycleReport()
        events = []

        # Drain up to batch_size events
        for _ in range(self.config.batch_size):
            event = self.bus.process_one(timeout=0.1)
            if event is None:
                break
            events.append(event)

        if not events:
            return report

        # Triage all events
        for event in events:
            result = triage(event)
            report.events_triaged += 1

            if not result.accepted:
                report.events_dropped += 1
                self.state.log_action(
                    action="triage_drop",
                    authority=AuthorityTier.AUTONOMOUS,
                    details=f"Dropped: {result.reason}",
                )
                continue

            # Check cost budget
            if report.cost_estimate + result.estimated_cost > self.config.max_cost_per_cycle:
                report.events_dropped += 1
                continue

            report.cost_estimate += result.estimated_cost

            # Determine authority tier based on priority
            tier = self._priority_to_tier(result.priority)
            auth = self.state.check_authority(result.category, tier)

            if auth["authorized"]:
                # Execute
                try:
                    action_result = self._execute_action(event, result)
                    report.actions_executed += 1
                    report.events_processed += 1

                    self.state.log_action(
                        action=f"execute:{result.category}",
                        authority=tier,
                        approved=True,
                        details=action_result or "completed",
                    )

                    # Notification routing by priority
                    self._route_notification(result.priority, result.category, action_result)

                except Exception as e:
                    report.errors.append(str(e))
                    self.state.log_action(
                        action=f"error:{result.category}",
                        authority=tier,
                        details=str(e),
                    )
            else:
                # Propose or alert
                task = self.state.create_task(
                    title=f"{result.category}: {event.source}",
                    authority_tier=tier,
                    context=f"Event: {event.event_type.value}, Priority: {result.priority.value}, "
                            f"Reason: {result.reason}",
                )
                self.state.update_task(task.id, status="awaiting_approval")
                report.actions_proposed += 1
                report.events_processed += 1

                self.state.log_action(
                    action=f"propose:{result.category}",
                    authority=tier,
                    task_id=task.id,
                    approved=False,
                    details=auth["reason"],
                )

        self._cycle_count += 1
        self._total_processed += report.events_processed
        return report

    def _execute_action(self, event: DaemonEvent, triage_result: TriageResult) -> Optional[str]:
        """Execute an action using registered handlers."""
        handler = self._action_handlers.get(triage_result.category)
        if handler:
            return handler(event, triage_result)
        return f"No handler for category: {triage_result.category}"

    def _route_notification(self, priority: Priority, category: str, detail: Optional[str]):
        """Route notifications: critical → immediate, normal → batch for digest, low → log only."""
        msg = f"{category}: {detail or 'completed'}"

        if priority == Priority.CRITICAL:
            # Immediate notification
            if self.config.notification_callback:
                self.config.notification_callback(f"[CRITICAL] {msg}")
        elif priority == Priority.NORMAL:
            # Batch for digest
            self._pending_notifications.append(msg)
            if self.config.notification_callback:
                self.config.notification_callback(f"[INFO] {msg}")
        # LOW = log only (already in audit log)

    def _check_digest(self):
        """Generate digest if interval has elapsed."""
        now = time.time()
        if now - self._last_digest_time >= self.config.digest_interval:
            self._last_digest_time = now
            try:
                from src.daemon.digest import generate_digest
                from pathlib import Path
                output_path = Path(self.config.digest_path) if self.config.digest_path else None
                digest = generate_digest(self.state, hours=24, output_path=output_path)
                if self.config.notification_callback:
                    self.config.notification_callback(f"[DIGEST] Daily summary generated ({len(self._pending_notifications)} events)")
                self._pending_notifications.clear()
            except Exception:
                pass

    def _priority_to_tier(self, priority: Priority) -> AuthorityTier:
        """Map event priority to authority tier."""
        mapping = {
            Priority.CRITICAL: AuthorityTier.PROPOSE_WAIT,  # Critical events need human approval
            Priority.NORMAL: AuthorityTier.ACT_NOTIFY,
            Priority.LOW: AuthorityTier.AUTONOMOUS,
        }
        return mapping.get(priority, AuthorityTier.PROPOSE_WAIT)

    def start(self):
        """Start the daemon loop in a background thread."""
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._worker = Thread(target=self._run_loop, daemon=True)
        self._worker.start()

    def stop(self, timeout: float = 5.0):
        """Stop the daemon loop."""
        self._running = False
        self._stop_event.set()
        if self._worker and self._worker.is_alive():
            self._worker.join(timeout=timeout)
        self._worker = None

    def _run_loop(self):
        """Main loop: process cycles at configured interval."""
        while not self._stop_event.is_set():
            self.process_cycle()
            self._check_digest()
            self._stop_event.wait(timeout=self.config.poll_interval)

    @property
    def stats(self) -> dict:
        return {
            "running": self._running,
            "cycles": self._cycle_count,
            "total_processed": self._total_processed,
            "bus_stats": self.bus.stats,
        }
