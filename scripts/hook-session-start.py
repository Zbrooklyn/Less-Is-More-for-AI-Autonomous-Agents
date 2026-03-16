#!/usr/bin/env python3
"""Claude Code SessionStart hook — injects relevant memories at session start.

Uses FAST injection (scope-based + keyword, no embeddings) to avoid the
~19s cold-start penalty from loading the sentence-transformers model.
Completes in <500ms.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.memory.store import MemoryStore


def fast_inject(store, project=None, task=None, max_entries=15):
    """Fast injection without embeddings — scope + keyword matching only."""
    results = []
    seen_ids = set()

    # 1. Always-inject global rules (confidence >= 0.9)
    global_rules = store.conn.execute(
        "SELECT * FROM memory_entries WHERE scope = 'global' AND type = 'rule' "
        "AND confidence >= 0.9 ORDER BY confidence DESC, use_count DESC LIMIT ?",
        (max_entries,),
    ).fetchall()
    for row in global_rules:
        entry = dict(row)
        entry["_source"] = "global_rule"
        results.append(entry)
        seen_ids.add(entry["id"])

    # 2. Project-scoped entries
    if project:
        project_slug = project.lower().replace(" ", "-")
        scope_variants = [f"project:{project_slug}"]
        if "whisperclick" in project_slug:
            scope_variants.append("project:whisperclick")

        for scope in scope_variants:
            rows = store.conn.execute(
                "SELECT * FROM memory_entries WHERE scope = ? "
                "ORDER BY confidence DESC, use_count DESC LIMIT ?",
                (scope, max_entries),
            ).fetchall()
            for row in rows:
                entry = dict(row)
                if entry["id"] not in seen_ids:
                    entry["_source"] = "project_scope"
                    results.append(entry)
                    seen_ids.add(entry["id"])

    # 3. Keyword match from task description (if provided)
    if task and len(results) < max_entries:
        keywords = [w for w in task.lower().split() if len(w) > 3]
        for kw in keywords[:5]:  # Limit keyword searches
            try:
                rows = store.conn.execute(
                    "SELECT * FROM memory_entries "
                    "WHERE content LIKE ? AND id NOT IN ({}) "
                    "ORDER BY confidence DESC LIMIT 3".format(
                        ",".join(f"'{i}'" for i in seen_ids) if seen_ids else "''"
                    ),
                    (f"%{kw}%",),
                ).fetchall()
                for row in rows:
                    entry = dict(row)
                    if entry["id"] not in seen_ids and len(results) < max_entries:
                        entry["_source"] = "keyword"
                        results.append(entry)
                        seen_ids.add(entry["id"])
            except Exception:
                continue

    return results


def format_results(entries):
    """Format injected entries for output."""
    if not entries:
        return ""

    lines = ["## Injected Memory Context", ""]

    rules = [e for e in entries if e.get("_source") == "global_rule"]
    project = [e for e in entries if e.get("_source") == "project_scope"]
    keyword = [e for e in entries if e.get("_source") == "keyword"]

    if rules:
        lines.append("### Global Rules")
        for e in rules:
            lines.append(f"- {e['content']}")
        lines.append("")

    if project:
        lines.append("### Project Context")
        for e in project:
            lines.append(f"- {e['content']}")
        lines.append("")

    if keyword:
        lines.append("### Related Context")
        for e in keyword:
            lines.append(f"- {e['content']}")
        lines.append("")

    return "\n".join(lines)


def main():
    store = MemoryStore()

    context_data = {}
    try:
        if not sys.stdin.isatty():
            raw = sys.stdin.read()
            if raw.strip():
                context_data = json.loads(raw)
    except (json.JSONDecodeError, OSError):
        pass

    project = context_data.get("project") or os.environ.get("CLAUDE_PROJECT")
    task = context_data.get("task")

    entries = fast_inject(store, project=project, task=task, max_entries=15)

    if entries:
        print(format_results(entries), file=sys.stderr)

    store.close()


if __name__ == "__main__":
    main()
