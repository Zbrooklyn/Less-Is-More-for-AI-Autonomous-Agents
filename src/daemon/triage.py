"""Triage engine — filters, classifies, and prioritizes events."""

import re
from dataclasses import dataclass
from typing import Optional

from src.daemon.events import DaemonEvent, EventType, Priority


@dataclass
class TriageResult:
    """Result of triaging an event."""
    accepted: bool
    priority: Priority
    reason: str
    category: str = "unknown"
    estimated_cost: float = 0.0  # Rough cost estimate in dollars


# File patterns to ignore (noise)
IGNORE_PATTERNS = [
    r"\.pyc$",
    r"__pycache__",
    r"\.git/",
    r"\.pytest_cache",
    r"node_modules/",
    r"\.egg-info/",
    r"~$",
    r"\.swp$",
    r"\.tmp$",
    r"\.log$",
    r"\.db-journal$",
    r"\.db-wal$",
    r"\.db-shm$",
]

# File patterns that are important (specific patterns MUST come before generic ones)
IMPORTANT_PATTERNS = [
    # Critical — check these first
    (r"CLAUDE\.md$", "agent_config", Priority.CRITICAL),
    (r"hot-memory\.md$", "memory", Priority.CRITICAL),
    (r"\.env$", "secrets", Priority.CRITICAL),
    # Normal priority
    (r"HANDOFF\.md$", "handoff", Priority.NORMAL),
    (r"\.py$", "python_source", Priority.NORMAL),
    (r"\.ts$", "typescript_source", Priority.NORMAL),
    (r"\.js$", "javascript_source", Priority.NORMAL),
    (r"\.json$", "config", Priority.NORMAL),
    (r"\.toml$", "config", Priority.NORMAL),
    (r"\.yaml$", "config", Priority.NORMAL),
    (r"\.yml$", "config", Priority.NORMAL),
    # Low priority (generic patterns last)
    (r"\.md$", "documentation", Priority.LOW),
]

# Cost estimates per event type (rough, in dollars)
COST_ESTIMATES = {
    EventType.FILE_CHANGE: 0.01,
    EventType.GIT_PUSH: 0.05,
    EventType.WEBHOOK: 0.02,
    EventType.TIMER: 0.01,
    EventType.MANUAL: 0.05,
    EventType.SYSTEM: 0.00,
}


def triage(event: DaemonEvent) -> TriageResult:
    """
    Triage an event — decide whether to accept it, what priority, and why.
    All decisions are local (no API calls).
    """
    # File change events: filter noise, classify important files
    if event.event_type == EventType.FILE_CHANGE:
        return _triage_file_change(event)

    # Git events: always interesting
    if event.event_type == EventType.GIT_PUSH:
        return TriageResult(
            accepted=True,
            priority=Priority.NORMAL,
            reason="Git push detected",
            category="git",
            estimated_cost=COST_ESTIMATES[EventType.GIT_PUSH],
        )

    # Webhooks: accept all, normal priority
    if event.event_type == EventType.WEBHOOK:
        return TriageResult(
            accepted=True,
            priority=Priority.NORMAL,
            reason="Webhook received",
            category="webhook",
            estimated_cost=COST_ESTIMATES[EventType.WEBHOOK],
        )

    # Timer events: always accepted, low priority
    if event.event_type == EventType.TIMER:
        return TriageResult(
            accepted=True,
            priority=Priority.LOW,
            reason="Scheduled timer event",
            category="timer",
            estimated_cost=COST_ESTIMATES[EventType.TIMER],
        )

    # Manual: always critical
    if event.event_type == EventType.MANUAL:
        return TriageResult(
            accepted=True,
            priority=Priority.CRITICAL,
            reason="Manual trigger",
            category="manual",
            estimated_cost=COST_ESTIMATES[EventType.MANUAL],
        )

    # System events: always accepted, low priority
    return TriageResult(
        accepted=True,
        priority=Priority.LOW,
        reason="System event",
        category="system",
        estimated_cost=COST_ESTIMATES.get(event.event_type, 0.0),
    )


def _triage_file_change(event: DaemonEvent) -> TriageResult:
    """Triage a file change event."""
    path = event.payload.get("path", "")
    change_type = event.payload.get("change_type", "modified")

    # Check ignore patterns
    for pattern in IGNORE_PATTERNS:
        if re.search(pattern, path):
            return TriageResult(
                accepted=False,
                priority=Priority.LOW,
                reason=f"Ignored pattern: {pattern}",
                category="noise",
            )

    # Check important patterns
    for pattern, category, priority in IMPORTANT_PATTERNS:
        if re.search(pattern, path):
            return TriageResult(
                accepted=True,
                priority=priority,
                reason=f"Matched important pattern: {pattern}",
                category=category,
                estimated_cost=COST_ESTIMATES[EventType.FILE_CHANGE],
            )

    # Unknown file type: accept with low priority
    return TriageResult(
        accepted=True,
        priority=Priority.LOW,
        reason="Unknown file type, accepted at low priority",
        category="unknown",
        estimated_cost=COST_ESTIMATES[EventType.FILE_CHANGE],
    )


def batch_triage(events: list[DaemonEvent]) -> list[tuple[DaemonEvent, TriageResult]]:
    """Triage multiple events, sorted by priority."""
    results = [(e, triage(e)) for e in events]
    # Sort: accepted first, then by priority (lower enum value = higher priority)
    results.sort(key=lambda x: (not x[1].accepted, x[1].priority.value))
    return results
