"""memory-cli — Command-line interface for the memory store."""

import argparse
import json
import os
import sys
from pathlib import Path

# Fix Windows terminal encoding for Unicode
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from src.memory.store import MemoryStore


def cmd_query(store: MemoryStore, args):
    """Search memory entries by text."""
    results = store.query(
        text=args.text,
        scope=args.scope,
        entry_type=args.type,
        limit=args.limit,
    )
    if not results:
        print("No results found.")
        return

    for i, entry in enumerate(results, 1):
        print(f"\n--- Result {i} ---")
        print(f"  Content:    {entry['content']}")
        print(f"  Type:       {entry['type']}")
        print(f"  Scope:      {entry['scope']}")
        print(f"  Confidence: {entry['confidence']}")
        print(f"  Source:     {entry['source']}")
        if entry.get("tags"):
            print(f"  Tags:       {entry['tags']}")


def cmd_add(store: MemoryStore, args):
    """Add a new memory entry."""
    entry = store.add(
        content=args.content,
        entry_type=args.type,
        scope=args.scope or "global",
        source=args.source or "manual",
        confidence=args.confidence or 0.5,
        tags=args.tags,
    )
    print(f"Added entry {entry['id'][:8]}...")
    print(f"  Content:    {entry['content']}")
    print(f"  Type:       {entry['type']}")
    print(f"  Scope:      {entry['scope']}")


def cmd_stats(store: MemoryStore, _args):
    """Show memory statistics."""
    stats = store.stats()
    print(f"\nTotal entries: {stats['total']}\n")

    print("By type:")
    for t, count in sorted(stats["by_type"].items(), key=lambda x: -x[1]):
        print(f"  {t:15s} {count:4d}")

    print("\nBy scope:")
    for s, count in sorted(stats["by_scope"].items(), key=lambda x: -x[1]):
        print(f"  {s:30s} {count:4d}")

    print("\nBy source:")
    for s, count in sorted(stats["by_source"].items(), key=lambda x: -x[1]):
        print(f"  {s:25s} {count:4d}")


def cmd_migrate(store: MemoryStore, _args):
    """Migrate existing markdown memory files into the database."""
    from src.memory.migrate import run_migration

    results = run_migration(store)
    total = sum(results.values())
    print(f"\nMigration complete: {total} entries from {len(results)} files\n")
    for source, count in sorted(results.items()):
        print(f"  {source}: {count} entries")
    print(f"\nDatabase: {store.db_path}")


def cmd_audit(store: MemoryStore, args):
    """Show recent audit log entries."""
    entries = store.get_audit_log(limit=args.limit)
    if not entries:
        print("No audit log entries.")
        return

    for entry in entries:
        ts = entry["timestamp"][:19]
        action = entry["action"]
        ctx = entry.get("context") or ""
        eid = (entry.get("entry_id") or "")[:8]
        print(f"  {ts}  {action:12s}  {eid:10s}  {ctx}")


def cmd_rules(store: MemoryStore, _args):
    """List active enforcement rules."""
    rules = store.get_active_rules()
    if not rules:
        print("No active enforcement rules.")
        return

    for rule in rules:
        print(f"\n  [{rule['severity'].upper()}] {rule['content']}")
        print(f"    Pattern:     {rule['pattern']}")
        print(f"    Type:        {rule['pattern_type']}")
        print(f"    Action:      {rule['action']}")
        if rule.get("alternative"):
            print(f"    Alternative: {rule['alternative']}")


def cmd_inject(store: MemoryStore, args):
    """Inject relevant memories for a session context."""
    from src.memory.injector import SessionContext, format_injection, inject

    context = SessionContext(
        project=args.project,
        file_path=args.file,
        task=args.task,
    )
    entries = inject(
        store, context,
        max_entries=args.max_entries,
        similarity_threshold=args.threshold,
    )
    if not entries:
        print("No relevant memories found for this context.")
        return

    print(format_injection(entries))
    print(f"--- {len(entries)} entries injected ---")


def cmd_embed(store: MemoryStore, _args):
    """Add embeddings to all entries that don't have them."""
    from src.memory.injector import embed_all_entries

    print("Embedding entries (this may take a moment on first run)...")
    count = embed_all_entries(store)
    if count == 0:
        print("All entries already have embeddings.")
    else:
        print(f"Embedded {count} entries.")


def cmd_enforce(store: MemoryStore, args):
    """Check a tool call against enforcement rules."""
    from src.hooks.enforce import enforce, format_enforcement

    result = enforce(store, args.tool, args.input)
    if result.allowed and result.action == "allow":
        print(f"ALLOWED: {args.tool}: {args.input}")
    else:
        print(format_enforcement(result))
    return 0 if result.allowed else 1


def cmd_capture(store: MemoryStore, args):
    """Check a user message for corrections and capture them."""
    from src.hooks.capture import capture, get_correction_stats

    if args.stats:
        stats = get_correction_stats(store)
        print(f"\nCorrections: {stats['total']} total, {stats['promoted']} promoted\n")
        if stats["by_type"]:
            print("By type:")
            for t, count in stats["by_type"].items():
                print(f"  {t:20s} {count:4d}")
        if stats["top_repeated"]:
            print("\nTop repeated:")
            for c in stats["top_repeated"]:
                print(f"  [{c['occurrence_count']}x] {c['what_was_wrong']} → {c['what_is_right']}")
        return

    result = capture(store, args.message, context=args.context, session_id=args.session)
    if not result.is_correction:
        print("Not detected as a correction.")
        return

    print(f"Correction detected ({result.detection_type}):")
    print(f"  Wrong: {result.what_was_wrong}")
    print(f"  Right: {result.what_is_right}")
    print(f"  Count: {result.occurrence_count}")
    if result.promoted:
        print(f"  AUTO-PROMOTED to enforcement rule: {result.promoted_rule_id[:8]}...")


def cmd_verify(store: MemoryStore, args):
    """Post-action compliance check."""
    from src.hooks.verify import verify, format_verification

    result = verify(store, args.tool, args.action, args.output)
    if result.compliant and not result.warnings:
        print(f"COMPLIANT: no violations or warnings.")
    else:
        print(format_verification(result))
    return 0 if result.compliant else 1


def cmd_pin(store: MemoryStore, args):
    """Pin or unpin a memory entry."""
    from src.hooks.pin import pin, unpin, get_pinned

    if args.list:
        pinned = get_pinned(store)
        if not pinned:
            print("No pinned entries.")
            return
        for entry in pinned:
            scope = f" [{entry['scope']}]" if entry["scope"] != "global" else ""
            print(f"  {entry['id'][:8]}  {entry['content']}{scope}")
        return

    if args.unpin:
        ok = unpin(store, args.entry_id)
        print("Unpinned." if ok else "Entry not found.")
        return

    ok = pin(store, args.entry_id)
    print("Pinned." if ok else "Entry not found.")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="memory-cli", description="LimClaw Memory Store")
    parser.add_argument("--db", type=str, help="Database path (default: ~/.claude/memory/memory.db)")

    sub = parser.add_subparsers(dest="command")

    # query
    p_query = sub.add_parser("query", help="Search memory entries")
    p_query.add_argument("text", help="Search text")
    p_query.add_argument("--scope", help="Filter by scope")
    p_query.add_argument("--type", help="Filter by entry type")
    p_query.add_argument("--limit", type=int, default=10, help="Max results")

    # add
    p_add = sub.add_parser("add", help="Add a memory entry")
    p_add.add_argument("--content", required=True, help="Entry content")
    p_add.add_argument("--type", required=True, help="Entry type (rule/fact/decision/preference/pattern/correction)")
    p_add.add_argument("--scope", help="Scope (default: global)")
    p_add.add_argument("--source", help="Source (default: manual)")
    p_add.add_argument("--confidence", type=float, help="Confidence 0.0-1.0")
    p_add.add_argument("--tags", help="Tags as JSON array string")

    # stats
    sub.add_parser("stats", help="Show memory statistics")

    # migrate
    sub.add_parser("migrate", help="Migrate markdown memory files into database")

    # audit
    p_audit = sub.add_parser("audit", help="Show audit log")
    p_audit.add_argument("--limit", type=int, default=20, help="Max entries")

    # rules
    sub.add_parser("rules", help="List active enforcement rules")

    # inject
    p_inject = sub.add_parser("inject", help="Inject relevant memories for a session")
    p_inject.add_argument("--project", help="Project name (e.g., 'WhisperClick V3')")
    p_inject.add_argument("--file", help="Current file path")
    p_inject.add_argument("--task", help="Current task description")
    p_inject.add_argument("--max-entries", type=int, default=15, help="Max entries to inject")
    p_inject.add_argument("--threshold", type=float, default=0.3, help="Similarity threshold")

    # embed
    sub.add_parser("embed", help="Add embeddings to all entries")

    # enforce
    p_enforce = sub.add_parser("enforce", help="Check a tool call against enforcement rules")
    p_enforce.add_argument("--tool", required=True, help="Tool name (e.g., Bash, Write, Edit)")
    p_enforce.add_argument("--input", required=True, help="Tool input to check")

    # capture
    p_capture = sub.add_parser("capture", help="Detect and capture corrections from a message")
    p_capture.add_argument("message", nargs="?", help="User message to analyze")
    p_capture.add_argument("--context", help="Additional context")
    p_capture.add_argument("--session", help="Session ID")
    p_capture.add_argument("--stats", action="store_true", help="Show correction statistics")

    # verify
    p_verify = sub.add_parser("verify", help="Post-action compliance check")
    p_verify.add_argument("--tool", required=True, help="Tool that was called")
    p_verify.add_argument("--action", required=True, help="What the tool was asked to do")
    p_verify.add_argument("--output", required=True, help="The tool's output")

    # pin
    p_pin = sub.add_parser("pin", help="Pin/unpin a memory entry")
    p_pin.add_argument("entry_id", nargs="?", help="Entry ID to pin")
    p_pin.add_argument("--unpin", action="store_true", help="Unpin instead of pin")
    p_pin.add_argument("--list", action="store_true", help="List all pinned entries")

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1

    db_path = Path(args.db) if args.db else None
    store = MemoryStore(db_path)

    try:
        commands = {
            "query": cmd_query,
            "add": cmd_add,
            "stats": cmd_stats,
            "migrate": cmd_migrate,
            "audit": cmd_audit,
            "rules": cmd_rules,
            "inject": cmd_inject,
            "embed": cmd_embed,
            "enforce": cmd_enforce,
            "capture": cmd_capture,
            "verify": cmd_verify,
            "pin": cmd_pin,
        }
        result = commands[args.command](store, args)
        return result or 0
    finally:
        store.close()


if __name__ == "__main__":
    sys.exit(main() or 0)
