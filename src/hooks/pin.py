"""Pinning — writes critical rules to CLAUDE.md so they survive context compression."""

import re
from pathlib import Path
from typing import Optional

from src.memory.store import MemoryStore

# Where pinned rules get written
DEFAULT_PIN_FILE = Path("CLAUDE.md")

# Max pinned entries to prevent bloat
MAX_PINNED = 20

# Markers in CLAUDE.md for the pinned section
PIN_SECTION_START = "<!-- PINNED_RULES_START -->"
PIN_SECTION_END = "<!-- PINNED_RULES_END -->"


def pin(
    store: MemoryStore,
    entry_id: str,
    pin_file: Optional[Path] = None,
) -> bool:
    """
    Pin a memory entry — marks it as pinned and writes it to CLAUDE.md.

    Returns True if successfully pinned.
    """
    entry = store.get(entry_id)
    if not entry:
        return False

    pin_file = pin_file or DEFAULT_PIN_FILE

    # Mark as pinned in the database
    store.conn.execute(
        "UPDATE memory_entries SET confidence = 1.0 WHERE id = ?",
        (entry_id,),
    )
    store.conn.commit()

    # LRU eviction: if we exceed MAX_PINNED, unpin the least-recently-used
    pinned_count = store.conn.execute(
        "SELECT COUNT(*) FROM memory_entries WHERE confidence = 1.0 AND type = 'rule'"
    ).fetchone()[0]
    if pinned_count > MAX_PINNED:
        excess = store.conn.execute(
            "SELECT id FROM memory_entries "
            "WHERE confidence = 1.0 AND type = 'rule' "
            "ORDER BY last_used ASC NULLS FIRST, use_count ASC "
            "LIMIT ?",
            (pinned_count - MAX_PINNED,),
        ).fetchall()
        for row in excess:
            if row[0] != entry_id:  # Don't evict the entry we just pinned
                store.conn.execute(
                    "UPDATE memory_entries SET confidence = 0.9 WHERE id = ?",
                    (row[0],),
                )
                store._audit("lru_evict", row[0], f"evicted to make room, max={MAX_PINNED}")
        store.conn.commit()

    # Write to pin file
    _write_pin_section(store, pin_file)

    store._audit("pin", entry_id, f"pinned to {pin_file}")
    return True


def unpin(
    store: MemoryStore,
    entry_id: str,
    pin_file: Optional[Path] = None,
) -> bool:
    """Remove a pin from an entry."""
    entry = store.get(entry_id)
    if not entry:
        return False

    pin_file = pin_file or DEFAULT_PIN_FILE

    # Lower confidence back to normal
    store.conn.execute(
        "UPDATE memory_entries SET confidence = 0.9 WHERE id = ? AND confidence = 1.0",
        (entry_id,),
    )
    store.conn.commit()

    # Rewrite pin section
    _write_pin_section(store, pin_file)

    store._audit("unpin", entry_id)
    return True


def get_pinned(store: MemoryStore, limit: int = MAX_PINNED) -> list[dict]:
    """Get all pinned entries (confidence = 1.0, type = rule)."""
    rows = store.conn.execute(
        "SELECT * FROM memory_entries "
        "WHERE confidence = 1.0 AND type = 'rule' "
        "ORDER BY use_count DESC, updated_at DESC "
        "LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def format_pinned_section(entries: list[dict]) -> str:
    """Format pinned entries as a CLAUDE.md section."""
    lines = [
        PIN_SECTION_START,
        "",
        "## Pinned Rules (auto-managed — do not edit manually)",
        "",
    ]

    if not entries:
        lines.append("_No pinned rules._")
    else:
        for entry in entries:
            content = entry["content"]
            scope = entry["scope"]
            scope_tag = f" [{scope}]" if scope != "global" else ""
            lines.append(f"- {content}{scope_tag}")

    lines.extend(["", PIN_SECTION_END])
    return "\n".join(lines)


def _write_pin_section(store: MemoryStore, pin_file: Path):
    """Write or update the pinned rules section in a file."""
    entries = get_pinned(store)
    section = format_pinned_section(entries)

    if not pin_file.exists():
        # Create file with just the pinned section
        pin_file.write_text(section + "\n", encoding="utf-8")
        return

    content = pin_file.read_text(encoding="utf-8")

    if PIN_SECTION_START in content:
        # Replace existing section
        pattern = re.escape(PIN_SECTION_START) + r".*?" + re.escape(PIN_SECTION_END)
        content = re.sub(pattern, section, content, flags=re.DOTALL)
    else:
        # Append section at the end
        content = content.rstrip() + "\n\n" + section + "\n"

    pin_file.write_text(content, encoding="utf-8")


def pre_compact_pin(store: MemoryStore, pin_file: Optional[Path] = None):
    """
    Called before context compression.
    Ensures all high-confidence rules are pinned to the file so they survive.
    """
    pin_file = pin_file or DEFAULT_PIN_FILE
    _write_pin_section(store, pin_file)
    store._audit("pre_compact_pin", None, f"refreshed pins in {pin_file}")
