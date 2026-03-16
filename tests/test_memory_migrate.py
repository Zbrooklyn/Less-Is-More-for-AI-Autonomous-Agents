"""Tests for the memory migration — parsing markdown and importing entries."""

import tempfile
from pathlib import Path

import pytest

from src.memory.migrate import (
    classify_entry,
    determine_scope,
    migrate_file,
    parse_markdown_sections,
)
from src.memory.store import MemoryStore


@pytest.fixture
def store(tmp_path):
    db_path = tmp_path / "test_migrate.db"
    s = MemoryStore(db_path)
    yield s
    s.close()


class TestMarkdownParsing:
    """Test markdown section and bullet extraction."""

    def test_parse_simple_sections(self):
        text = """## Section One
- First bullet
- Second bullet

## Section Two
- Third bullet
"""
        sections = parse_markdown_sections(text)
        assert len(sections) == 2
        assert sections[0]["section"] == "Section One"
        assert len(sections[0]["bullets"]) == 2
        assert sections[1]["section"] == "Section Two"

    def test_parse_nested_headers(self):
        text = """## Main Section
- Bullet one

### Sub Section
- Sub bullet
"""
        sections = parse_markdown_sections(text)
        assert len(sections) == 2

    def test_parse_numbered_items(self):
        text = """## Steps
1. First step
2. Second step
3. Third step
"""
        sections = parse_markdown_sections(text)
        assert len(sections) == 1
        assert len(sections[0]["bullets"]) == 3

    def test_parse_bold_bullets(self):
        text = """## Rules
- **NEVER use pythonw.exe** — silently crashes with Qt/PySide6
- **ALWAYS run tests** after changes
"""
        sections = parse_markdown_sections(text)
        assert len(sections[0]["bullets"]) == 2

    def test_ignores_empty_sections(self):
        text = """## Empty Section

## Section With Content
- Has a bullet
"""
        sections = parse_markdown_sections(text)
        assert len(sections) == 1
        assert sections[0]["section"] == "Section With Content"

    def test_ignores_non_bullet_text(self):
        text = """## Section
Some paragraph text that is not a bullet.
- Actual bullet point
More paragraph text.
"""
        sections = parse_markdown_sections(text)
        assert len(sections) == 1
        assert len(sections[0]["bullets"]) == 1


class TestClassifyEntry:
    """Test entry type classification."""

    def test_rule_indicators(self):
        assert classify_entry("NEVER use pythonw.exe", "fact") == "rule"
        assert classify_entry("Always run tests first", "fact") == "rule"
        assert classify_entry("Must check error-solutions.md", "fact") == "rule"
        assert classify_entry("Don't push to public", "fact") == "rule"

    def test_decision_indicators(self):
        assert classify_entry("Chose pywebview over Electron", "fact") == "decision"
        assert classify_entry("Rejected Docker for simplicity", "fact") == "decision"

    def test_pattern_indicators(self):
        assert classify_entry("Error: module not found — Fix: pip install", "fact") == "pattern"
        assert classify_entry("Verified: Yes — use ReleaseCapture", "fact") == "pattern"

    def test_preference_indicators(self):
        assert classify_entry("Rate: $65/hr, $400 floor", "fact") == "preference"

    def test_default_type_preserved(self):
        assert classify_entry("Some generic content", "fact") == "fact"
        assert classify_entry("Another generic thing", "rule") == "rule"


class TestDetermineScope:
    """Test scope detection from content."""

    def test_whisperclick_scope(self):
        assert determine_scope("WhisperClick V3 uses pywebview", "") == "project:whisperclick"

    def test_mission_control_scope(self):
        assert determine_scope("Mission Control port 8100", "") == "project:mission-control"

    def test_global_scope_default(self):
        assert determine_scope("Generic Python rule", "") == "global"

    def test_scope_from_section(self):
        assert determine_scope("some rule", "WhisperClick Settings") == "project:whisperclick"


class TestMigrateFile:
    """Test migrating actual files."""

    def test_migrate_simple_file(self, store, tmp_path):
        md_file = tmp_path / "test.md"
        md_file.write_text("""## Testing Rules
- Never skip end-to-end tests after changes
- Always restore settings after test mutations
- Use snapshot/restore pattern for test isolation
""")
        config = {"type": "rule", "source": "test-file", "confidence": 0.9}
        count = migrate_file(store, md_file, config)
        assert count == 3
        assert store.stats()["total"] == 3

    def test_migrate_empty_file(self, store, tmp_path):
        md_file = tmp_path / "empty.md"
        md_file.write_text("# Empty\n\n")
        config = {"type": "fact", "source": "test", "confidence": 0.5}
        count = migrate_file(store, md_file, config)
        assert count == 0

    def test_migrate_nonexistent_file(self, store, tmp_path):
        config = {"type": "fact", "source": "test", "confidence": 0.5}
        count = migrate_file(store, tmp_path / "nonexistent.md", config)
        assert count == 0

    def test_migrated_entries_are_searchable(self, store, tmp_path):
        md_file = tmp_path / "test.md"
        md_file.write_text("""## GUI Rules
- Never use pythonw.exe for launching GUI processes
- Use run_in_background true for persistent processes
""")
        config = {"type": "rule", "source": "test", "confidence": 1.0}
        migrate_file(store, md_file, config)

        results = store.query("pythonw")
        assert len(results) >= 1
        assert any("pythonw" in r["content"] for r in results)

    def test_scope_assigned_correctly(self, store, tmp_path):
        md_file = tmp_path / "test.md"
        md_file.write_text("""## WhisperClick Rules
- WhisperClick V3 must use python.exe not pythonw.exe

## General Rules
- Generic rule that applies everywhere
""")
        config = {"type": "rule", "source": "test", "confidence": 1.0}
        migrate_file(store, md_file, config)

        stats = store.stats()
        assert "project:whisperclick" in stats["by_scope"]
        assert "global" in stats["by_scope"]


class TestMigrateRealFiles:
    """Test migration against the actual memory files on this system."""

    @pytest.fixture
    def shared_memory_path(self):
        path = Path("C:/Users/Owner/Downloads/AI_Projects/shared/memory")
        if not path.exists():
            pytest.skip("Shared memory directory not found")
        return path

    def test_hot_memory_exists_and_parses(self, shared_memory_path):
        hot = shared_memory_path / "hot-memory.md"
        assert hot.exists()
        sections = parse_markdown_sections(hot.read_text(encoding="utf-8"))
        assert len(sections) > 0

    def test_full_migration_produces_entries(self, store, shared_memory_path):
        config = {"type": "rule", "source": "hot-memory", "confidence": 1.0}
        count = migrate_file(store, shared_memory_path / "hot-memory.md", config)
        assert count > 10  # hot-memory has many rules

    def test_error_solutions_migrates(self, store, shared_memory_path):
        config = {"type": "pattern", "source": "error-solutions", "confidence": 1.0}
        count = migrate_file(store, shared_memory_path / "error-solutions.md", config)
        assert count > 5  # has many known errors

    def test_decisions_log_migrates(self, store, shared_memory_path):
        config = {"type": "decision", "source": "decisions-log", "confidence": 0.9}
        count = migrate_file(store, shared_memory_path / "decisions-log.md", config)
        assert count > 5
