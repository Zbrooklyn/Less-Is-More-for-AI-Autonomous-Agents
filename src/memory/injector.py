"""Context injector — loads relevant memories based on session context."""

from dataclasses import dataclass
from typing import Optional

from src.memory.embeddings import cosine_similarity, embed_text
from src.memory.store import MemoryStore

# Injection config defaults
DEFAULT_MAX_ENTRIES = 15
DEFAULT_SIMILARITY_THRESHOLD = 0.3
DEFAULT_MAX_TOKENS = 2000

# Rough token estimate: 1 token ≈ 4 chars
CHARS_PER_TOKEN = 4


@dataclass
class SessionContext:
    """What the agent is currently working on."""
    project: Optional[str] = None
    file_path: Optional[str] = None
    task: Optional[str] = None

    def to_query_text(self) -> str:
        """Build a text string for semantic search from the context."""
        parts = []
        if self.project:
            parts.append(self.project)
        if self.file_path:
            parts.append(self.file_path)
        if self.task:
            parts.append(self.task)
        return " ".join(parts) if parts else ""


def inject(
    store: MemoryStore,
    context: SessionContext,
    max_entries: int = DEFAULT_MAX_ENTRIES,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> list[dict]:
    """
    Given the current session context, return the most relevant memories
    to inject into the agent's context window.

    Strategy:
    1. Always include global rules with high confidence
    2. Include project-scoped entries if working in a project
    3. Rank by semantic similarity to the context
    4. Enforce token budget
    """
    results = []
    seen_ids = set()

    # Step 1: Always-inject global rules (confidence >= 0.9)
    global_rules = store.conn.execute(
        "SELECT * FROM memory_entries WHERE scope = 'global' AND type = 'rule' "
        "AND confidence >= 0.9 ORDER BY confidence DESC, use_count DESC"
    ).fetchall()
    for row in global_rules:
        entry = dict(row)
        entry["_relevance"] = 1.0  # Global rules always relevant
        entry["_source"] = "global_rule"
        results.append(entry)
        seen_ids.add(entry["id"])

    # Step 2: Project-scoped entries (if working in a project)
    if context.project:
        project_scope = f"project:{context.project.lower().replace(' ', '-').replace('whisperclick-v3', 'whisperclick').replace('whisperclick v3', 'whisperclick')}"
        # Normalize common project name variations
        scope_variants = [project_scope]
        if "whisperclick" in project_scope:
            scope_variants.append("project:whisperclick")

        for scope in scope_variants:
            project_entries = store.conn.execute(
                "SELECT * FROM memory_entries WHERE scope = ? ORDER BY confidence DESC, use_count DESC",
                (scope,),
            ).fetchall()
            for row in project_entries:
                entry = dict(row)
                if entry["id"] not in seen_ids:
                    entry["_relevance"] = 0.9  # Project entries highly relevant
                    entry["_source"] = "project_scope"
                    results.append(entry)
                    seen_ids.add(entry["id"])

    # Step 3: Semantic search for additional relevant entries
    query_text = context.to_query_text()
    if query_text:
        query_embedding = embed_text(query_text)

        # Get all entries with embeddings that aren't already included
        all_entries = store.conn.execute(
            "SELECT * FROM memory_entries WHERE embedding IS NOT NULL"
        ).fetchall()

        scored = []
        for row in all_entries:
            entry = dict(row)
            if entry["id"] in seen_ids:
                continue
            similarity = cosine_similarity(query_embedding, entry["embedding"])
            if similarity >= similarity_threshold:
                entry["_relevance"] = similarity
                entry["_source"] = "semantic"
                scored.append(entry)

        # Sort by similarity descending
        scored.sort(key=lambda x: x["_relevance"], reverse=True)
        results.extend(scored)

    # Step 4: Deduplicate and enforce limits
    final = []
    total_chars = 0
    max_chars = max_tokens * CHARS_PER_TOKEN

    # Sort all results: global rules first, then by relevance
    results.sort(key=lambda x: (
        0 if x["_source"] == "global_rule" else 1,
        -x["_relevance"],
        -x.get("confidence", 0),
    ))

    for entry in results:
        if len(final) >= max_entries:
            break
        content_len = len(entry["content"])
        if total_chars + content_len > max_chars:
            continue  # Skip entries that would bust the token budget
        final.append(entry)
        total_chars += content_len

        # Update use_count
        store.conn.execute(
            "UPDATE memory_entries SET use_count = use_count + 1, last_used = datetime('now') WHERE id = ?",
            (entry["id"],),
        )

    store.conn.commit()
    store._audit("inject", None, f"context={query_text}, results={len(final)}")

    return final


def format_injection(entries: list[dict]) -> str:
    """Format injected memories as a readable block for the agent's context."""
    if not entries:
        return ""

    lines = ["## Injected Memory Context", ""]

    # Group by source type
    rules = [e for e in entries if e.get("_source") == "global_rule"]
    project = [e for e in entries if e.get("_source") == "project_scope"]
    semantic = [e for e in entries if e.get("_source") == "semantic"]

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

    if semantic:
        lines.append("### Related Context")
        for e in semantic:
            sim = e.get("_relevance", 0)
            lines.append(f"- [{sim:.0%}] {e['content']}")
        lines.append("")

    return "\n".join(lines)


def embed_all_entries(store: MemoryStore, batch_size: int = 64) -> int:
    """Add embeddings to all entries that don't have them yet."""
    rows = store.conn.execute(
        "SELECT id, content FROM memory_entries WHERE embedding IS NULL"
    ).fetchall()

    if not rows:
        return 0

    from src.memory.embeddings import embed_texts

    count = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        texts = [r["content"] for r in batch]
        embeddings = embed_texts(texts)

        for row, emb in zip(batch, embeddings):
            store.conn.execute(
                "UPDATE memory_entries SET embedding = ? WHERE id = ?",
                (emb, row["id"]),
            )
        count += len(batch)

    store.conn.commit()
    store._audit("embed_batch", None, f"embedded={count}")
    return count
