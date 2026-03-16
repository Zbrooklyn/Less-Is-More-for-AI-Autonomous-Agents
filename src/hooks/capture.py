"""Correction capture — detects corrections in user messages and auto-promotes repeat offenders."""

import re
from dataclasses import dataclass
from typing import Optional

from src.memory.store import MemoryStore


# Patterns that indicate a user correction
CORRECTION_PATTERNS = [
    (r"\bno[,.]?\s+(not\s+that|don'?t|never|stop)\b", "explicit_negative"),
    (r"\binstead[\s,]+(?:do|use|try)\b", "redirect"),
    (r"\bi (?:already |just )?told you\b", "repetition"),
    (r"\bthat'?s (?:wrong|incorrect|not right|not what)\b", "wrong"),
    (r"\bdon'?t (?:do|use|add|create|make|write|include)\b", "prohibition"),
    (r"\bnever (?:do|use|add|create|make|write|include)\b", "prohibition"),
    (r"\balways (?:do|use|make|check|run|verify)\b", "mandate"),
    (r"\bstop (?:doing|using|adding|creating)\b", "stop"),
    (r"\bwhy (?:did you|are you|would you)\b", "question_correction"),
    (r"\bplease (?:don'?t|stop|never)\b", "polite_correction"),
]

# Auto-promotion threshold
PROMOTION_THRESHOLD = 3


@dataclass
class CaptureResult:
    """Result of correction capture."""
    is_correction: bool
    detection_type: str
    what_was_wrong: Optional[str] = None
    what_is_right: Optional[str] = None
    correction_id: Optional[str] = None
    occurrence_count: int = 0
    promoted: bool = False
    promoted_rule_id: Optional[str] = None


def detect_correction(message: str) -> tuple[bool, str]:
    """Check if a message contains a correction pattern."""
    lower = message.lower()
    for pattern, detection_type in CORRECTION_PATTERNS:
        if re.search(pattern, lower):
            return True, detection_type
    return False, "none"


def extract_correction_content(message: str) -> tuple[str, str]:
    """
    Extract what was wrong and what is right from a correction message.
    Returns (what_was_wrong, what_is_right).
    """
    lower = message.lower()

    # "Don't X, use Y instead" pattern
    match = re.search(
        r"(?:don'?t|never|stop)\s+(?:use|do|add)\s+(.+?)(?:[,;.]|\s+(?:instead|use|do))\s*(.+?)(?:[.]|$)",
        lower,
    )
    if match:
        return match.group(1).strip(), match.group(2).strip()

    # "No, X. Instead, Y" pattern
    match = re.search(r"no[,.]?\s+(.+?)(?:[.]|instead)\s*[,.]?\s*(.+?)(?:[.]|$)", lower)
    if match:
        return match.group(1).strip(), match.group(2).strip()

    # "Use X instead of Y" pattern
    match = re.search(r"use\s+(.+?)\s+instead\s+of\s+(.+?)(?:[.]|$)", lower)
    if match:
        return match.group(2).strip(), match.group(1).strip()

    # "Always X" pattern (what was wrong is implicit)
    match = re.search(r"always\s+(.+?)(?:[.]|$)", lower)
    if match:
        return "not doing: " + match.group(1).strip(), match.group(1).strip()

    # Fallback: the whole message is the correction
    return "previous behavior", message.strip()


def find_similar_correction(store: MemoryStore, what_was_wrong: str) -> Optional[dict]:
    """Find an existing correction that matches this one (deduplication)."""
    corrections = store.conn.execute(
        "SELECT * FROM corrections ORDER BY detected_at DESC"
    ).fetchall()

    wrong_lower = what_was_wrong.lower()
    for row in corrections:
        existing = dict(row)
        if _text_similarity(wrong_lower, existing["what_was_wrong"].lower()) > 0.7:
            return existing

    return None


def _text_similarity(a: str, b: str) -> float:
    """Simple Jaccard similarity between two strings (word-level)."""
    words_a = set(a.split())
    words_b = set(b.split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def capture(
    store: MemoryStore,
    user_message: str,
    context: Optional[str] = None,
    session_id: Optional[str] = None,
) -> CaptureResult:
    """
    Analyze a user message for corrections. If found:
    1. Log the correction
    2. Deduplicate against existing corrections
    3. Auto-promote to enforcement rule after PROMOTION_THRESHOLD occurrences
    """
    is_correction, detection_type = detect_correction(user_message)

    if not is_correction:
        return CaptureResult(is_correction=False, detection_type="none")

    what_was_wrong, what_is_right = extract_correction_content(user_message)

    # Check for existing similar correction
    existing = find_similar_correction(store, what_was_wrong)

    if existing:
        # Increment count
        new_count = existing["occurrence_count"] + 1
        store.conn.execute(
            "UPDATE corrections SET occurrence_count = ? WHERE id = ?",
            (new_count, existing["id"]),
        )
        store.conn.commit()

        correction_id = existing["id"]
        occurrence_count = new_count
    else:
        # Create new correction
        correction = store.add_correction(
            user_message=user_message,
            what_was_wrong=what_was_wrong,
            what_is_right=what_is_right,
            context=context,
            session_id=session_id,
            detection_type=detection_type,
        )
        correction_id = correction["id"]
        occurrence_count = 1

    # Auto-promote if threshold reached
    promoted = False
    promoted_rule_id = None

    if occurrence_count >= PROMOTION_THRESHOLD:
        # Check if already promoted
        row = store.conn.execute(
            "SELECT promoted_to FROM corrections WHERE id = ?", (correction_id,)
        ).fetchone()

        if row and not row[0]:
            # Promote to enforcement rule
            entry = store.add_enforcement_rule(
                content=f"Auto-promoted: {what_is_right}",
                pattern=re.escape(what_was_wrong) if len(what_was_wrong) < 50 else what_was_wrong[:50],
                pattern_type="command",
                action="block",
                severity="high",
                alternative=what_is_right,
            )
            promoted_rule_id = entry["id"]
            promoted = True

            # Mark correction as promoted
            store.conn.execute(
                "UPDATE corrections SET promoted_to = ? WHERE id = ?",
                (promoted_rule_id, correction_id),
            )
            store.conn.commit()

            store._audit(
                "auto_promote",
                promoted_rule_id,
                f"correction={correction_id}, count={occurrence_count}, threshold={PROMOTION_THRESHOLD}",
            )

    store._audit(
        "capture",
        correction_id,
        f"detection={detection_type}, count={occurrence_count}, promoted={promoted}",
    )

    return CaptureResult(
        is_correction=True,
        detection_type=detection_type,
        what_was_wrong=what_was_wrong,
        what_is_right=what_is_right,
        correction_id=correction_id,
        occurrence_count=occurrence_count,
        promoted=promoted,
        promoted_rule_id=promoted_rule_id,
    )


def get_correction_stats(store: MemoryStore) -> dict:
    """Get correction statistics."""
    total = store.conn.execute("SELECT COUNT(*) FROM corrections").fetchone()[0]
    promoted = store.conn.execute(
        "SELECT COUNT(*) FROM corrections WHERE promoted_to IS NOT NULL"
    ).fetchone()[0]
    by_type = dict(
        store.conn.execute(
            "SELECT detection_type, COUNT(*) FROM corrections GROUP BY detection_type"
        ).fetchall()
    )
    top_repeated = [
        dict(r) for r in store.conn.execute(
            "SELECT what_was_wrong, what_is_right, occurrence_count "
            "FROM corrections WHERE occurrence_count > 1 "
            "ORDER BY occurrence_count DESC LIMIT 10"
        ).fetchall()
    ]

    return {
        "total": total,
        "promoted": promoted,
        "by_type": by_type,
        "top_repeated": top_repeated,
    }
