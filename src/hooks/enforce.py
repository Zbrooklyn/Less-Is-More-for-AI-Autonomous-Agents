"""Enforcement engine — checks tool calls against active rules and blocks/warns."""

import re
from dataclasses import dataclass, field
from typing import Optional

from src.memory.store import MemoryStore


@dataclass
class EnforceResult:
    """Result of an enforcement check."""
    allowed: bool
    action: str  # "allow", "block", "warn", "suggest"
    rule_id: Optional[str] = None
    rule_content: Optional[str] = None
    pattern: Optional[str] = None
    severity: Optional[str] = None
    alternative: Optional[str] = None
    reason: Optional[str] = None


def _match_regex(pattern: str, text: str) -> bool:
    """Check if text matches a regex pattern (case-insensitive)."""
    try:
        return bool(re.search(pattern, text, re.IGNORECASE))
    except re.error:
        return False


def _match_command(pattern: str, text: str) -> bool:
    """Check if text contains a command pattern (simple substring, case-insensitive)."""
    return pattern.lower() in text.lower()


def _match_semantic(pattern: str, text: str, store: MemoryStore) -> bool:
    """Check if text is semantically similar to a pattern using embeddings."""
    try:
        from src.memory.embeddings import embed_text, cosine_similarity
        pattern_emb = embed_text(pattern)
        text_emb = embed_text(text)
        similarity = cosine_similarity(pattern_emb, text_emb)
        return similarity >= 0.75  # High threshold for enforcement
    except Exception:
        # Fall back to substring match if embeddings unavailable
        return _match_command(pattern, text)


MATCHERS = {
    "regex": _match_regex,
    "command": _match_command,
}

# Auto-escalation thresholds: after N violations, escalate severity/action
ESCALATION_RULES = [
    (5, "warn", "block"),     # 5+ violations: warn → block
    (10, "medium", "high"),   # 10+ violations: medium severity → high
    (20, "high", "critical"), # 20+ violations: high severity → critical
]


def _auto_escalate(store: MemoryStore, rule_id: str, current_severity: str, current_action: str, violation_count: int):
    """Escalate rule severity/action based on violation count."""
    for threshold, from_val, to_val in ESCALATION_RULES:
        if violation_count >= threshold:
            # Escalate action (warn → block)
            if current_action == from_val and to_val in ("block", "warn"):
                store.conn.execute(
                    "UPDATE enforcement_rules SET action = ? WHERE id = ? AND action = ?",
                    (to_val, rule_id, from_val),
                )
                store._audit("auto_escalate", rule_id,
                             f"action {from_val}→{to_val} after {violation_count} violations")
            # Escalate severity
            if current_severity == from_val and to_val in ("critical", "high", "medium"):
                store.conn.execute(
                    "UPDATE enforcement_rules SET severity = ? WHERE id = ? AND severity = ?",
                    (to_val, rule_id, from_val),
                )
                store._audit("auto_escalate", rule_id,
                             f"severity {from_val}→{to_val} after {violation_count} violations")
    store.conn.commit()


def enforce(
    store: MemoryStore,
    tool: str,
    tool_input: str,
    use_semantic: bool = False,
) -> EnforceResult:
    """
    Check a tool call against all active enforcement rules.

    Args:
        store: The memory store containing enforcement rules
        tool: The tool name (e.g., "Bash", "Write", "Edit")
        tool_input: The tool input/command to check
        use_semantic: Whether to use semantic matching (slower, needs model)

    Returns:
        EnforceResult with allowed=True if no rules match, or details of the blocking rule
    """
    rules = store.get_active_rules()

    # Combine tool name and input for matching
    full_text = f"{tool}: {tool_input}"

    for rule in rules:
        pattern = rule["pattern"]
        pattern_type = rule["pattern_type"]

        matched = False
        if pattern_type == "semantic" and use_semantic:
            matched = _match_semantic(pattern, full_text, store)
        elif pattern_type in MATCHERS:
            matched = MATCHERS[pattern_type](pattern, full_text)
        elif pattern_type == "semantic" and not use_semantic:
            # Fall back to command matching when semantic is disabled
            matched = _match_command(pattern, full_text)

        if matched:
            action = rule["action"]
            result = EnforceResult(
                allowed=(action not in ("block",)),
                action=action,
                rule_id=rule["id"],
                rule_content=rule["content"],
                pattern=pattern,
                severity=rule["severity"],
                alternative=rule.get("alternative"),
                reason=f"Matched {pattern_type} pattern: {pattern}",
            )

            # Audit the enforcement action
            store._audit(
                "enforce",
                rule["id"],
                f"tool={tool}, action={action}, pattern={pattern}, input={tool_input[:100]}",
            )

            # Increment violation count on the memory entry
            store.conn.execute(
                "UPDATE memory_entries SET violation_count = violation_count + 1 WHERE id = ?",
                (rule["id"],),
            )
            store.conn.commit()

            # Auto-escalate severity based on violation count
            entry = store.get(rule["id"])
            if entry:
                v_count = entry.get("violation_count", 0)
                _auto_escalate(store, rule["id"], rule["severity"], rule["action"], v_count)

            return result

    # No rules matched — allowed
    store._audit("enforce", None, f"tool={tool}, action=allow, input={tool_input[:100]}")
    return EnforceResult(allowed=True, action="allow")


def enforce_output(
    store: MemoryStore,
    tool: str,
    output: str,
) -> EnforceResult:
    """
    Check tool output against enforcement rules (post-action check).
    Uses the same rules but checks the output instead of input.
    """
    rules = store.get_active_rules()

    for rule in rules:
        pattern = rule["pattern"]
        pattern_type = rule["pattern_type"]

        matched = False
        if pattern_type in MATCHERS:
            matched = MATCHERS[pattern_type](pattern, output)

        if matched:
            result = EnforceResult(
                allowed=False,
                action="violation",
                rule_id=rule["id"],
                rule_content=rule["content"],
                pattern=pattern,
                severity=rule["severity"],
                alternative=rule.get("alternative"),
                reason=f"Output contains blocked pattern: {pattern}",
            )

            store._audit(
                "enforce_output",
                rule["id"],
                f"tool={tool}, violation detected, pattern={pattern}",
            )

            return result

    return EnforceResult(allowed=True, action="allow")


def format_enforcement(result: EnforceResult) -> str:
    """Format an enforcement result as a human-readable message."""
    if result.allowed and result.action == "allow":
        return ""

    lines = []
    severity_icons = {
        "critical": "BLOCKED",
        "high": "BLOCKED",
        "medium": "WARNING",
        "low": "INFO",
    }
    icon = severity_icons.get(result.severity, "NOTICE")

    lines.append(f"[{icon}] {result.rule_content}")
    if result.reason:
        lines.append(f"  Reason: {result.reason}")
    if result.alternative:
        lines.append(f"  Instead: {result.alternative}")

    return "\n".join(lines)
