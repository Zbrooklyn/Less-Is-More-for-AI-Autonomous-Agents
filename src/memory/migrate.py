"""Migrate existing markdown memory files into the SQLite memory store."""

import re
from pathlib import Path

from src.memory.store import MemoryStore

# Locations to scan — auto-detect workspace root
def _find_workspace_root() -> Path:
    """Walk up from CWD looking for shared/memory/ directory."""
    d = Path.cwd()
    while d != d.parent:
        if (d / "shared" / "memory").is_dir():
            return d
        d = d.parent
    # Fallback to known location
    known = Path("C:/Users/Owner/Downloads/AI_Projects")
    if known.exists():
        return known
    return Path.cwd()

_WS_ROOT = _find_workspace_root()
SHARED_MEMORY = _WS_ROOT / "shared" / "memory"
CLAUDE_MEMORY = Path.home() / ".claude" / "projects" / f"C--Users-Owner-Downloads-AI-Projects" / "memory"

# Map filenames to entry types and scopes
FILE_CONFIG = {
    "hot-memory.md": {"type": "rule", "source": "hot-memory", "confidence": 1.0},
    "MEMORY.md": {"type": "rule", "source": "claude-memory", "confidence": 1.0},
    "corrections-log.md": {"type": "correction", "source": "corrections-log", "confidence": 0.7},
    "decisions-log.md": {"type": "decision", "source": "decisions-log", "confidence": 0.9},
    "user-preferences.md": {"type": "preference", "source": "user-preferences", "confidence": 0.9},
    "environment.md": {"type": "fact", "source": "environment", "confidence": 1.0},
    "error-solutions.md": {"type": "pattern", "source": "error-solutions", "confidence": 1.0},
    "session-summaries.md": {"type": "fact", "source": "session-summaries", "confidence": 0.6},
    "patterns.md": {"type": "pattern", "source": "patterns", "confidence": 0.9},
    "business-context.md": {"type": "fact", "source": "business-context", "confidence": 0.9},
    "project-graph.md": {"type": "fact", "source": "project-graph", "confidence": 0.8},
    "memory-verification-probes.md": {"type": "fact", "source": "verification-probes", "confidence": 0.7},
    "bootstrap-receipts.md": {"type": "fact", "source": "bootstrap-receipts", "confidence": 1.0},
}

# Files to skip (empty placeholders or duplicates)
SKIP_FILES = {"context-memory.md", "archive.md"}


def parse_markdown_sections(text: str) -> list[dict]:
    """Parse a markdown file into sections with headers, bullet points, and table rows."""
    entries = []
    current_section = None
    current_bullets = []
    in_table = False
    table_headers = []

    for line in text.splitlines():
        line = line.rstrip()

        # Section header (## or ###)
        header_match = re.match(r"^#{1,4}\s+(.+)$", line)
        if header_match:
            # Save previous section
            if current_section and current_bullets:
                entries.append({
                    "section": current_section,
                    "bullets": list(current_bullets),
                })
            current_section = header_match.group(1).strip()
            current_bullets = []
            in_table = False
            table_headers = []
            continue

        # Table header row (| Col1 | Col2 | ...)
        if re.match(r"^\|.*\|.*\|", line) and not in_table:
            cells = [c.strip() for c in line.split("|") if c.strip()]
            # Check if next meaningful content is a separator row
            if cells and not re.match(r"^[-:| ]+$", line):
                table_headers = cells
                in_table = True
                continue

        # Table separator row (|---|---|)
        if in_table and re.match(r"^\|[-:| ]+\|$", line):
            continue

        # Table data row
        if in_table and re.match(r"^\|.*\|", line):
            cells = [c.strip() for c in line.split("|") if c.strip()]
            if cells and not re.match(r"^[-:| ]+$", line):
                # Combine header:value pairs into a readable string
                parts = []
                for i, cell in enumerate(cells):
                    if cell and cell != "---":
                        if i < len(table_headers):
                            parts.append(f"{table_headers[i]}: {cell}")
                        else:
                            parts.append(cell)
                if parts:
                    current_bullets.append(" | ".join(parts))
            continue

        # Non-table line while in table = end of table
        if in_table and line.strip() and not line.startswith("|"):
            in_table = False
            table_headers = []

        # Bullet point or numbered item
        bullet_match = re.match(r"^\s*[-*]\s+(.+)$", line)
        numbered_match = re.match(r"^\s*\d+\.\s+(.+)$", line)
        if bullet_match:
            current_bullets.append(bullet_match.group(1).strip())
        elif numbered_match:
            current_bullets.append(numbered_match.group(1).strip())

    # Save last section
    if current_section and current_bullets:
        entries.append({
            "section": current_section,
            "bullets": list(current_bullets),
        })

    return entries


def classify_entry(text: str, file_type: str) -> str:
    """Refine entry type based on content patterns."""
    lower = text.lower()

    # Strong rule indicators
    if any(kw in lower for kw in ["never ", "always ", "must ", "don't ", "do not "]):
        return "rule"

    # Decision indicators
    if any(kw in lower for kw in ["chose ", "rejected ", "decided ", " over ", "why not"]):
        return "decision"

    # Error/fix indicators
    if any(kw in lower for kw in ["error:", "fix:", "solution:", "verified:", "workaround"]):
        return "pattern"

    # Preference indicators
    if any(kw in lower for kw in ["prefer", "style", "rate:", "$", "pricing"]):
        return "preference"

    # Correction indicators
    if any(kw in lower for kw in ["correction", "wrong", "should be", "instead"]):
        return "correction"

    return file_type


def determine_scope(text: str, section: str) -> str:
    """Determine the scope of an entry based on content."""
    lower = (text + " " + section).lower()

    if "whisperclick" in lower or "whisper-stt" in lower:
        return "project:whisperclick"
    if "mission control" in lower or "mission-control" in lower:
        return "project:mission-control"
    if "html recorder" in lower:
        return "project:html-recorder"
    if "auto-trading" in lower or "auto trading" in lower:
        return "project:auto-trading"
    if "battery" in lower or "brooklyn battery" in lower:
        return "project:battery-hybrid"
    if "ecommerce" in lower or "easy ecommerce" in lower:
        return "project:easy-ecommerce"
    if "temple run" in lower:
        return "project:temple-run"

    return "global"


def migrate_file(store: MemoryStore, filepath: Path, config: dict) -> int:
    """Migrate a single markdown file. Returns number of entries created."""
    if not filepath.exists():
        return 0

    text = filepath.read_text(encoding="utf-8")
    if len(text.strip()) < 20:
        return 0

    sections = parse_markdown_sections(text)
    count = 0

    for section in sections:
        section_name = section["section"]

        # Skip meta sections (headers, indexes, table of contents)
        skip_sections = {"Bootstrap Phrase", "Memory System Index", "Index", "How to Read"}
        if any(skip in section_name for skip in skip_sections):
            continue

        for bullet in section["bullets"]:
            # Skip very short or meta bullets
            if len(bullet) < 10:
                continue
            if bullet.startswith("**") and bullet.endswith("**") and len(bullet) < 30:
                continue

            # Build content with section context
            content = f"[{section_name}] {bullet}"

            # Classify and scope
            entry_type = classify_entry(bullet, config["type"])
            scope = determine_scope(bullet, section_name)

            # Add tags from section name
            tags_list = [section_name.lower().replace(" ", "-")]
            if scope != "global":
                tags_list.append(scope.split(":")[1] if ":" in scope else scope)

            store.add(
                content=content,
                entry_type=entry_type,
                scope=scope,
                source=config["source"],
                confidence=config["confidence"],
                tags=str(tags_list),
            )
            count += 1

    return count


def run_migration(store: MemoryStore) -> dict:
    """Run full migration from all markdown files. Returns summary."""
    results = {}

    # Shared memory files
    for filename, config in FILE_CONFIG.items():
        if filename in SKIP_FILES:
            continue
        filepath = SHARED_MEMORY / filename
        count = migrate_file(store, filepath, config)
        if count > 0:
            results[f"shared/{filename}"] = count

    # Claude-only memory files
    for filename, config in FILE_CONFIG.items():
        if filename in SKIP_FILES:
            continue
        filepath = CLAUDE_MEMORY / filename
        if filepath.exists():
            count = migrate_file(store, filepath, config)
            if count > 0:
                results[f"claude/{filename}"] = count

    return results


if __name__ == "__main__":
    import sys

    db_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    store = MemoryStore(db_path)
    results = run_migration(store)

    total = sum(results.values())
    print(f"\nMigration complete: {total} entries from {len(results)} files\n")
    for source, count in sorted(results.items()):
        print(f"  {source}: {count} entries")

    print(f"\nDatabase: {store.db_path}")
    stats = store.stats()
    print(f"Total entries: {stats['total']}")
    print(f"By type: {stats['by_type']}")
    print(f"By scope: {stats['by_scope']}")
    store.close()
