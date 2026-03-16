"""Verification engine — post-action compliance checking and semantic retrieval."""

import re
from dataclasses import dataclass
from typing import Optional

from src.memory.store import MemoryStore


@dataclass
class VerifyResult:
    """Result of a post-action verification check."""
    compliant: bool
    violations: list  # list of dicts with rule details
    warnings: list    # list of dicts with rule details


def verify(
    store: MemoryStore,
    tool: str,
    action_description: str,
    output: str,
) -> VerifyResult:
    """
    Post-action compliance check. Verifies tool output against active rules.

    Args:
        store: The memory store
        tool: Tool that was called (e.g., "Bash", "Write")
        action_description: What the tool was asked to do
        output: The tool's output/result
    """
    rules = store.get_active_rules()
    violations = []
    warnings = []

    # Check output against each rule
    combined = f"{action_description}\n{output}"

    for rule in rules:
        pattern = rule["pattern"]
        pattern_type = rule["pattern_type"]
        matched = False

        if pattern_type == "regex":
            try:
                matched = bool(re.search(pattern, combined, re.IGNORECASE))
            except re.error:
                continue
        elif pattern_type == "command":
            matched = pattern.lower() in combined.lower()

        if matched:
            detail = {
                "rule_id": rule["id"],
                "content": rule["content"],
                "severity": rule["severity"],
                "pattern": pattern,
                "alternative": rule.get("alternative"),
            }

            if rule["severity"] in ("critical", "high"):
                violations.append(detail)
            else:
                warnings.append(detail)

            # Increment violation count
            store.conn.execute(
                "UPDATE memory_entries SET violation_count = violation_count + 1 WHERE id = ?",
                (rule["id"],),
            )

    store.conn.commit()

    compliant = len(violations) == 0

    store._audit(
        "verify",
        None,
        f"tool={tool}, compliant={compliant}, violations={len(violations)}, warnings={len(warnings)}",
    )

    return VerifyResult(compliant=compliant, violations=violations, warnings=warnings)


def format_verification(result: VerifyResult) -> str:
    """Format verification result as human-readable text."""
    if result.compliant and not result.warnings:
        return ""

    lines = []

    if result.violations:
        lines.append("COMPLIANCE VIOLATIONS:")
        for v in result.violations:
            lines.append(f"  [{v['severity'].upper()}] {v['content']}")
            if v.get("alternative"):
                lines.append(f"    Fix: {v['alternative']}")

    if result.warnings:
        lines.append("WARNINGS:")
        for w in result.warnings:
            lines.append(f"  [{w['severity'].upper()}] {w['content']}")

    return "\n".join(lines)


# === Semantic Retrieval ===

def query_memory(
    store: MemoryStore,
    question: str,
    scope: Optional[str] = None,
    entry_type: Optional[str] = None,
    include_negative: bool = False,
    max_results: int = 10,
) -> list[dict]:
    """
    Semantic memory query — the agent can call this mid-session to ask
    "what do I know about X?"

    Ranking: similarity x recency x confidence.
    """
    try:
        from src.memory.embeddings import embed_text, cosine_similarity
        question_embedding = embed_text(question)
        use_embeddings = True
    except Exception:
        use_embeddings = False

    # Get candidate entries
    sql = "SELECT * FROM memory_entries WHERE 1=1 "
    params = []

    if scope:
        sql += "AND (scope = ? OR scope = 'global') "
        params.append(scope)
    if entry_type:
        sql += "AND type = ? "
        params.append(entry_type)

    rows = store.conn.execute(sql, params).fetchall()
    entries = [dict(r) for r in rows]

    # Score each entry
    scored = []
    for entry in entries:
        score = 0.0

        # Semantic similarity (if embeddings available)
        if use_embeddings and entry.get("embedding"):
            similarity = cosine_similarity(question_embedding, entry["embedding"])
            score += similarity * 0.6  # 60% weight on semantic match
        else:
            # Fallback: keyword overlap
            q_words = set(question.lower().split())
            c_words = set(entry["content"].lower().split())
            if q_words & c_words:
                overlap = len(q_words & c_words) / max(len(q_words), 1)
                score += overlap * 0.6

        # Confidence weight
        score += entry.get("confidence", 0.5) * 0.2

        # Recency weight (use_count as proxy)
        use_count = entry.get("use_count", 0)
        score += min(use_count / 100, 0.2)  # cap at 0.2

        entry["_score"] = score
        if score > 0.1:  # minimum threshold
            scored.append(entry)

    # Sort by score descending
    scored.sort(key=lambda x: x["_score"], reverse=True)

    # Handle negative retrieval (what was rejected before?)
    if include_negative:
        negative_entries = store.conn.execute(
            "SELECT m.*, r.pattern, r.action, r.alternative "
            "FROM memory_entries m "
            "JOIN enforcement_rules r ON m.id = r.id "
            "WHERE r.active = 1"
        ).fetchall()

        for row in negative_entries:
            entry = dict(row)
            # Check if this negative rule is relevant to the question
            if use_embeddings and entry.get("embedding"):
                similarity = cosine_similarity(question_embedding, entry["embedding"])
                if similarity > 0.3:
                    entry["_score"] = similarity
                    entry["_negative"] = True
                    scored.append(entry)

    # Limit results
    results = scored[:max_results]

    # Update use_count for returned entries
    for entry in results:
        if "id" in entry:
            store.conn.execute(
                "UPDATE memory_entries SET use_count = use_count + 1, last_used = datetime('now') WHERE id = ?",
                (entry["id"],),
            )
    store.conn.commit()

    store._audit("query_memory", None, f"question={question[:80]}, results={len(results)}")

    return results


def format_query_results(results: list[dict]) -> str:
    """Format query results for display."""
    if not results:
        return "No relevant memories found."

    lines = ["## Memory Query Results", ""]

    positive = [r for r in results if not r.get("_negative")]
    negative = [r for r in results if r.get("_negative")]

    if positive:
        for entry in positive:
            score = entry.get("_score", 0)
            scope = entry.get("scope", "global")
            lines.append(f"- [{score:.0%}] ({scope}) {entry['content']}")

    if negative:
        lines.append("")
        lines.append("### Previously Rejected")
        for entry in negative:
            lines.append(f"- {entry['content']}")
            if entry.get("alternative"):
                lines.append(f"  Use instead: {entry['alternative']}")

    return "\n".join(lines)
