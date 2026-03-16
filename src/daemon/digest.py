"""Daily digest — summarizes daemon activity over a time period."""

from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from src.daemon.state import DaemonState


def generate_digest(
    state: DaemonState,
    hours: int = 24,
    output_path: Optional[Path] = None,
) -> str:
    """
    Generate a digest of daemon activity for the last N hours.

    Returns the digest as a formatted string. Optionally writes to a file.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    # Get actions since cutoff
    all_actions = state.get_action_log(limit=500)
    recent_actions = [a for a in all_actions if a["timestamp"] >= cutoff]

    # Get tasks created/updated in the period
    all_tasks = state.list_tasks()
    recent_tasks = [t for t in all_tasks if t.updated_at >= cutoff]

    # Build digest
    lines = [
        f"# Daemon Digest - Last {hours} hours",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
    ]

    # Summary stats
    action_counts = {}
    for a in recent_actions:
        action_type = a["action"].split(":")[0]
        action_counts[action_type] = action_counts.get(action_type, 0) + 1

    lines.append(f"## Summary")
    lines.append(f"- **Actions:** {len(recent_actions)}")
    lines.append(f"- **Tasks:** {len(recent_tasks)}")

    if action_counts:
        lines.append(f"- **Breakdown:**")
        for action, count in sorted(action_counts.items(), key=lambda x: -x[1]):
            lines.append(f"  - {action}: {count}")
    lines.append("")

    # Tasks requiring attention
    awaiting = [t for t in recent_tasks if t.status == "awaiting_approval"]
    failed = [t for t in recent_tasks if t.status == "failed"]

    if awaiting:
        lines.append("## Awaiting Approval")
        for t in awaiting:
            lines.append(f"- **{t.title}** (Tier {t.authority_tier})")
            if t.context:
                lines.append(f"  Context: {t.context[:100]}")
        lines.append("")

    if failed:
        lines.append("## Failed Tasks")
        for t in failed:
            lines.append(f"- **{t.title}**")
            if t.result:
                lines.append(f"  Error: {t.result[:100]}")
        lines.append("")

    # Completed tasks
    completed = [t for t in recent_tasks if t.status == "completed"]
    if completed:
        lines.append("## Completed")
        for t in completed:
            lines.append(f"- {t.title}")
        lines.append("")

    # Enforcement highlights
    enforce_actions = [a for a in recent_actions if "enforce" in a["action"]]
    blocks = [a for a in enforce_actions if "block" in (a.get("details") or "")]
    if blocks:
        lines.append("## Blocked Actions")
        for a in blocks[:10]:  # Top 10
            lines.append(f"- {a['details'][:120]}")
        lines.append("")

    if not recent_actions and not recent_tasks:
        lines.append("_No daemon activity in the last {hours} hours._")
        lines.append("")

    digest = "\n".join(lines)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(digest, encoding="utf-8")

    return digest


def print_digest(state: DaemonState, hours: int = 24):
    """Print the digest to stdout."""
    print(generate_digest(state, hours=hours))
