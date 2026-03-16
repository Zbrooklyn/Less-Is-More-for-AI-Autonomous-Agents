"""Tests for context injection — embedding, similarity search, and memory injection."""

from pathlib import Path

import pytest

from src.memory.store import MemoryStore


@pytest.fixture
def store(tmp_path):
    db_path = tmp_path / "test_inject.db"
    s = MemoryStore(db_path)
    yield s
    s.close()


@pytest.fixture
def populated_store(store):
    """Store with diverse entries for injection testing."""
    # Global rules (high confidence)
    store.add("Never use pythonw.exe for GUI processes", "rule", scope="global", source="test", confidence=1.0)
    store.add("Always run tests after code changes", "rule", scope="global", source="test", confidence=1.0)
    store.add("Never push directly to public remote", "rule", scope="global", source="test", confidence=0.95)

    # WhisperClick entries
    store.add("WhisperClick uses pywebview with WM_APP_DRAGSTART for window drag", "fact",
              scope="project:whisperclick", source="test", confidence=0.9)
    store.add("WhisperClick lock file at ~/.config/whisperclick/whisperclick.lock", "fact",
              scope="project:whisperclick", source="test", confidence=0.8)
    store.add("WhisperClick error: easy_drag broken on multi-monitor DPI", "pattern",
              scope="project:whisperclick", source="test", confidence=1.0)

    # Mission Control entries
    store.add("Mission Control runs on port 8100", "fact",
              scope="project:mission-control", source="test", confidence=0.9)
    store.add("Mission Control has no hot-reload, always restart server", "rule",
              scope="project:mission-control", source="test", confidence=1.0)

    # Low confidence entries (should be filtered)
    store.add("Maybe use Docker for isolation", "fact", scope="global", source="test", confidence=0.3)

    return store


class TestEmbeddings:
    """Test embedding generation."""

    def test_embed_text_returns_bytes(self):
        from src.memory.embeddings import embed_text
        result = embed_text("test string")
        assert isinstance(result, bytes)
        assert len(result) == 384 * 4  # 384 dims * 4 bytes per float32

    def test_embed_texts_batch(self):
        from src.memory.embeddings import embed_texts
        results = embed_texts(["hello", "world", "test"])
        assert len(results) == 3
        assert all(isinstance(r, bytes) for r in results)

    def test_embed_texts_empty(self):
        from src.memory.embeddings import embed_texts
        assert embed_texts([]) == []

    def test_similar_texts_have_high_similarity(self):
        from src.memory.embeddings import cosine_similarity, embed_text
        a = embed_text("Never use pythonw.exe for GUI processes")
        b = embed_text("Don't use pythonw.exe when launching GUI apps")
        sim = cosine_similarity(a, b)
        assert sim > 0.7  # Similar texts should have high similarity

    def test_different_texts_have_lower_similarity(self):
        from src.memory.embeddings import cosine_similarity, embed_text
        a = embed_text("Never use pythonw.exe for GUI processes")
        b = embed_text("The weather is nice today in Brooklyn")
        sim = cosine_similarity(a, b)
        assert sim < 0.5  # Different topics should have lower similarity


class TestEmbedAllEntries:
    """Test batch embedding of store entries."""

    def test_embed_all(self, populated_store):
        from src.memory.injector import embed_all_entries
        count = embed_all_entries(populated_store)
        assert count == 9  # All entries should be embedded

    def test_embed_idempotent(self, populated_store):
        from src.memory.injector import embed_all_entries
        embed_all_entries(populated_store)
        count = embed_all_entries(populated_store)
        assert count == 0  # Already embedded, nothing new


class TestSessionContext:
    """Test session context construction."""

    def test_context_to_query(self):
        from src.memory.injector import SessionContext
        ctx = SessionContext(project="WhisperClick V3", file_path="src/main.py", task="fix drag bug")
        text = ctx.to_query_text()
        assert "WhisperClick" in text
        assert "main.py" in text
        assert "drag bug" in text

    def test_empty_context(self):
        from src.memory.injector import SessionContext
        ctx = SessionContext()
        assert ctx.to_query_text() == ""


class TestInjection:
    """Test the full injection pipeline."""

    def test_inject_global_rules_always_included(self, populated_store):
        from src.memory.injector import SessionContext, inject
        context = SessionContext()  # No specific project
        entries = inject(populated_store, context)

        # Should include high-confidence global rules
        contents = [e["content"] for e in entries]
        assert any("pythonw" in c for c in contents)
        assert any("tests" in c.lower() for c in contents)

    def test_inject_project_scoped(self, populated_store):
        from src.memory.injector import SessionContext, inject
        context = SessionContext(project="whisperclick")
        entries = inject(populated_store, context)

        # Should include whisperclick-specific entries
        contents = [e["content"] for e in entries]
        assert any("pywebview" in c for c in contents)
        assert any("lock file" in c for c in contents)

    def test_inject_different_project_excludes_other(self, populated_store):
        from src.memory.injector import SessionContext, inject
        context = SessionContext(project="mission-control")
        entries = inject(populated_store, context)

        # Should include mission-control entries
        contents = [e["content"] for e in entries]
        assert any("port 8100" in c for c in contents)
        # Should NOT include whisperclick-specific entries via project scope
        project_sources = [e.get("_source") for e in entries]
        project_entries = [e for e in entries if e.get("_source") == "project_scope"]
        assert all("whisperclick" not in e.get("scope", "") for e in project_entries)

    def test_inject_with_semantic_search(self, populated_store):
        from src.memory.injector import SessionContext, embed_all_entries, inject
        embed_all_entries(populated_store)

        context = SessionContext(task="fix window dragging issue in pywebview")
        entries = inject(populated_store, context)

        # Semantic search should find drag-related entries
        contents = [e["content"] for e in entries]
        assert any("drag" in c.lower() or "pywebview" in c.lower() for c in contents)

    def test_inject_respects_max_entries(self, populated_store):
        from src.memory.injector import SessionContext, inject
        context = SessionContext(project="whisperclick")
        entries = inject(populated_store, context, max_entries=3)
        assert len(entries) <= 3

    def test_inject_updates_use_count(self, populated_store):
        from src.memory.injector import SessionContext, inject
        context = SessionContext()
        entries = inject(populated_store, context)

        # Check that use_count was incremented
        for entry in entries:
            refreshed = populated_store.get(entry["id"])
            assert refreshed["use_count"] >= 1


class TestFormatInjection:
    """Test formatting injected entries for the agent."""

    def test_format_empty(self):
        from src.memory.injector import format_injection
        assert format_injection([]) == ""

    def test_format_groups_by_source(self):
        from src.memory.injector import format_injection
        entries = [
            {"content": "Global rule", "_source": "global_rule", "_relevance": 1.0},
            {"content": "Project fact", "_source": "project_scope", "_relevance": 0.9},
            {"content": "Semantic match", "_source": "semantic", "_relevance": 0.75},
        ]
        output = format_injection(entries)
        assert "Global Rules" in output
        assert "Project Context" in output
        assert "Related Context" in output
        assert "Global rule" in output
        assert "75%" in output  # Similarity score
