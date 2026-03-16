#!/usr/bin/env python3
"""Seed the memory database with default enforcement rules.

Run after migration to populate the rules that power the enforcement engine.

Usage:
  python scripts/seed-rules.py              # Seed into default DB (~/.claude/memory/memory.db)
  python scripts/seed-rules.py --db demo.db # Seed into a specific DB
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.memory.store import MemoryStore

# Default enforcement rules — the core "never do this" list
DEFAULT_RULES = [
    {
        "content": "Never use pythonw.exe — silently crashes with Qt/PySide6 on this system",
        "pattern": r"pythonw\.exe",
        "pattern_type": "regex",
        "action": "block",
        "severity": "critical",
        "alternative": "Use python.exe instead (e.g., ./venv/Scripts/python.exe)",
    },
    {
        "content": "Never push directly to public repo — leaks private files (CLAUDE.md, HANDOFF.md, etc.)",
        "pattern": r"git\s+push\s+public",
        "pattern_type": "regex",
        "action": "block",
        "severity": "critical",
        "alternative": "Use git push origin <branch>, then run tools/sync_public.sh",
    },
    {
        "content": "Never use easy_drag=True in pywebview — broken on multi-monitor DPI setups",
        "pattern": "easy_drag=True",
        "pattern_type": "command",
        "action": "block",
        "severity": "high",
        "alternative": "Use WM_APP_DRAGSTART pattern (PostMessageW from JS → ReleaseCapture + SendMessageW on UI thread)",
    },
    {
        "content": "Never use -webkit-app-region: drag — not supported by WebView2 backend",
        "pattern": "-webkit-app-region",
        "pattern_type": "command",
        "action": "block",
        "severity": "high",
        "alternative": "Use WM_APP_DRAGSTART pattern instead",
    },
    {
        "content": "Never use SendMessageW for drag from JS bridge thread — deadlocks",
        "pattern": "SendMessageW.*WM_NCLBUTTONDOWN",
        "pattern_type": "regex",
        "action": "block",
        "severity": "high",
        "alternative": "Use PostMessageW to post WM_APP_DRAGSTART, then handle on UI thread",
    },
    {
        "content": "Warn about git force push — dangerous, can overwrite upstream changes",
        "pattern": r"git\s+push\s+.*--force\b",
        "pattern_type": "regex",
        "action": "warn",
        "severity": "medium",
        "alternative": "Use --force-with-lease for safer force pushing",
    },
    {
        "content": "Never push directly to main on Easy Ecommerce Group — auto-deploys to production",
        "pattern": r"git\s+push\s+.*\s+main",
        "pattern_type": "regex",
        "action": "warn",
        "severity": "high",
        "alternative": "Use feature branches → dev → main workflow",
        "scope": "project:easy-ecommerce",
    },
    {
        "content": "Never skip git hooks with --no-verify unless user explicitly requests it",
        "pattern": "--no-verify",
        "pattern_type": "command",
        "action": "warn",
        "severity": "medium",
        "alternative": "Fix the hook issue instead of bypassing it",
    },
    {
        "content": "Never store API keys in localStorage — security risk",
        "pattern": "localStorage.*api.?key",
        "pattern_type": "regex",
        "action": "block",
        "severity": "critical",
        "alternative": "Use the credential broker (cred-cli) or environment variables",
    },
    {
        "content": "Never use CDN for external dependencies — supply-chain risk",
        "pattern": r"cdn\.jsdelivr|cdnjs\.cloudflare|unpkg\.com",
        "pattern_type": "regex",
        "action": "warn",
        "severity": "medium",
        "alternative": "Bundle dependencies locally via npm/pip",
    },
]


def seed_rules(store: MemoryStore) -> int:
    """Seed enforcement rules into the database. Skips rules that already exist."""
    existing = store.get_active_rules()
    existing_patterns = {r["pattern"] for r in existing}

    added = 0
    for rule in DEFAULT_RULES:
        if rule["pattern"] in existing_patterns:
            continue

        store.add_enforcement_rule(
            content=rule["content"],
            pattern=rule["pattern"],
            pattern_type=rule["pattern_type"],
            action=rule["action"],
            severity=rule["severity"],
            alternative=rule.get("alternative"),
            scope=rule.get("scope", "global"),
        )
        added += 1

    return added


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Seed enforcement rules into memory DB")
    parser.add_argument("--db", type=str, help="Database path (default: ~/.claude/memory/memory.db)")
    args = parser.parse_args()

    db_path = Path(args.db) if args.db else None
    store = MemoryStore(db_path)

    # Check if migration has been run
    stats = store.stats()
    if stats["total"] == 0:
        print("Database is empty. Run 'memory-cli migrate' first to import memory entries.")
        print("Then re-run this script to seed enforcement rules.")
        store.close()
        return

    added = seed_rules(store)
    total_rules = len(store.get_active_rules())

    print(f"\nSeeded {added} new enforcement rules ({total_rules} total active).\n")

    # Show all rules
    for rule in store.get_active_rules():
        print(f"  [{rule['severity'].upper():8s}] {rule['action']:5s}  {rule['content']}")

    store.close()


if __name__ == "__main__":
    main()
