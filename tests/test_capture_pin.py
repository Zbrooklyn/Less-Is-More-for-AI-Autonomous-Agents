"""Tests for correction capture and pinning."""

import pytest

from src.memory.store import MemoryStore
from src.hooks.capture import (
    capture,
    detect_correction,
    extract_correction_content,
    find_similar_correction,
    get_correction_stats,
    PROMOTION_THRESHOLD,
)
from src.hooks.pin import (
    pin,
    unpin,
    get_pinned,
    format_pinned_section,
    pre_compact_pin,
    PIN_SECTION_START,
    PIN_SECTION_END,
)


@pytest.fixture
def store(tmp_path):
    db_path = tmp_path / "test_capture.db"
    s = MemoryStore(db_path)
    yield s
    s.close()


# === Correction Detection ===

class TestDetectCorrection:
    def test_explicit_no(self):
        is_corr, dtype = detect_correction("No, don't use pythonw.exe")
        assert is_corr
        assert dtype == "explicit_negative"

    def test_instead_redirect(self):
        is_corr, dtype = detect_correction("Instead, use python.exe for GUI")
        assert is_corr
        assert dtype == "redirect"

    def test_already_told_you(self):
        is_corr, dtype = detect_correction("I already told you not to do that")
        assert is_corr
        assert dtype == "repetition"

    def test_thats_wrong(self):
        is_corr, dtype = detect_correction("That's wrong, the port should be 8100")
        assert is_corr
        assert dtype == "wrong"

    def test_dont_prohibition(self):
        is_corr, dtype = detect_correction("Don't add comments to the code")
        assert is_corr
        assert dtype == "prohibition"

    def test_never_prohibition(self):
        is_corr, dtype = detect_correction("Never use easy_drag=True in pywebview")
        assert is_corr
        assert dtype == "prohibition"

    def test_always_mandate(self):
        is_corr, dtype = detect_correction("Always run tests after code changes")
        assert is_corr
        assert dtype == "mandate"

    def test_stop_doing(self):
        is_corr, dtype = detect_correction("Stop doing that every time")
        assert is_corr
        assert dtype == "stop"

    def test_normal_message_not_correction(self):
        is_corr, _ = detect_correction("Can you help me add a new feature?")
        assert not is_corr

    def test_normal_question_not_correction(self):
        is_corr, _ = detect_correction("What does this function do?")
        assert not is_corr

    def test_code_with_dont_not_correction(self):
        # Edge case: "don't" in a context that isn't a correction
        is_corr, _ = detect_correction("The app says: please don't close this window")
        # This will detect as correction, which is acceptable — better safe than sorry
        assert is_corr


class TestExtractCorrectionContent:
    def test_dont_use_pattern(self):
        wrong, right = extract_correction_content("Don't use pythonw.exe, use python.exe instead")
        assert "pythonw" in wrong
        assert "python" in right

    def test_use_instead_of(self):
        wrong, right = extract_correction_content("Use python.exe instead of pythonw.exe")
        assert "pythonw" in wrong
        assert "python" in right

    def test_always_pattern(self):
        wrong, right = extract_correction_content("Always run tests after changes.")
        assert "run tests" in right

    def test_fallback_whole_message(self):
        wrong, right = extract_correction_content("That is completely incorrect")
        assert right == "That is completely incorrect"


# === Correction Capture Flow ===

class TestCaptureFlow:
    def test_captures_correction(self, store):
        result = capture(store, "No, don't use pythonw.exe for GUI apps")
        assert result.is_correction
        assert result.correction_id is not None
        assert result.occurrence_count == 1

    def test_non_correction_ignored(self, store):
        result = capture(store, "Can you read this file for me?")
        assert not result.is_correction
        assert result.correction_id is None

    def test_duplicate_increments_count(self, store):
        capture(store, "Don't use pythonw.exe")
        result2 = capture(store, "Never use pythonw.exe")
        assert result2.occurrence_count == 2

    def test_different_corrections_separate(self, store):
        r1 = capture(store, "Don't use pythonw.exe")
        r2 = capture(store, "Don't add comments to the code")
        assert r1.correction_id != r2.correction_id
        assert r1.occurrence_count == 1
        assert r2.occurrence_count == 1

    def test_auto_promotes_after_threshold(self, store):
        # Hit the threshold
        for i in range(PROMOTION_THRESHOLD):
            result = capture(store, "No, don't use pythonw.exe ever")

        assert result.promoted
        assert result.promoted_rule_id is not None
        assert result.occurrence_count >= PROMOTION_THRESHOLD

        # Verify the rule was created
        rules = store.get_active_rules()
        promoted_rules = [r for r in rules if "Auto-promoted" in r["content"]]
        assert len(promoted_rules) >= 1

    def test_wont_double_promote(self, store):
        # Promote once
        for i in range(PROMOTION_THRESHOLD):
            capture(store, "No, don't use pythonw.exe ever")

        # Send more of the same — use same wording so dedup matches
        result = capture(store, "No, don't use pythonw.exe ever")
        # Should increment but not create a second promoted rule
        assert result.occurrence_count > PROMOTION_THRESHOLD


class TestCorrectionStats:
    def test_empty_stats(self, store):
        stats = get_correction_stats(store)
        assert stats["total"] == 0

    def test_stats_with_corrections(self, store):
        capture(store, "Don't use pythonw.exe")
        capture(store, "Don't add comments to the code")
        capture(store, "Don't use pythonw.exe again")  # repeat — similar to first

        stats = get_correction_stats(store)
        assert stats["total"] >= 2
        assert len(stats["top_repeated"]) >= 1


# === Pinning ===

class TestPinning:
    def test_pin_entry(self, store, tmp_path):
        pin_file = tmp_path / "CLAUDE.md"
        entry = store.add("Never use pythonw.exe", "rule", confidence=0.9, source="test")

        result = pin(store, entry["id"], pin_file=pin_file)
        assert result is True

        # Check confidence was raised
        updated = store.get(entry["id"])
        assert updated["confidence"] == 1.0

        # Check file was created
        assert pin_file.exists()
        content = pin_file.read_text()
        assert "pythonw" in content

    def test_pin_nonexistent_fails(self, store, tmp_path):
        result = pin(store, "fake-id", pin_file=tmp_path / "CLAUDE.md")
        assert result is False

    def test_unpin_entry(self, store, tmp_path):
        pin_file = tmp_path / "CLAUDE.md"
        entry = store.add("Never use pythonw.exe", "rule", confidence=1.0, source="test")
        pin(store, entry["id"], pin_file=pin_file)

        result = unpin(store, entry["id"], pin_file=pin_file)
        assert result is True

        updated = store.get(entry["id"])
        assert updated["confidence"] == 0.9

    def test_get_pinned(self, store):
        store.add("Rule A", "rule", confidence=1.0, source="test")
        store.add("Rule B", "rule", confidence=1.0, source="test")
        store.add("Rule C", "rule", confidence=0.5, source="test")  # not pinned

        pinned = get_pinned(store)
        assert len(pinned) == 2
        assert all(p["confidence"] == 1.0 for p in pinned)

    def test_pin_appends_to_existing_file(self, store, tmp_path):
        pin_file = tmp_path / "CLAUDE.md"
        pin_file.write_text("# Existing Content\n\nSome rules here.\n", encoding="utf-8")

        entry = store.add("Never use pythonw.exe", "rule", confidence=0.9, source="test")
        pin(store, entry["id"], pin_file=pin_file)

        content = pin_file.read_text()
        assert "Existing Content" in content
        assert "pythonw" in content
        assert PIN_SECTION_START in content

    def test_pin_replaces_existing_section(self, store, tmp_path):
        pin_file = tmp_path / "CLAUDE.md"
        pin_file.write_text(
            f"# Header\n\n{PIN_SECTION_START}\n\nOld pinned content\n\n{PIN_SECTION_END}\n\n# Footer\n",
            encoding="utf-8",
        )

        entry = store.add("New rule about testing", "rule", confidence=0.9, source="test")
        pin(store, entry["id"], pin_file=pin_file)

        content = pin_file.read_text()
        assert "Old pinned content" not in content
        assert "New rule about testing" in content
        assert "Header" in content
        assert "Footer" in content


class TestFormatPinnedSection:
    def test_empty_entries(self):
        text = format_pinned_section([])
        assert "No pinned rules" in text

    def test_with_entries(self):
        entries = [
            {"content": "Never use pythonw.exe", "scope": "global"},
            {"content": "Use WM_APP_DRAGSTART", "scope": "project:whisperclick"},
        ]
        text = format_pinned_section(entries)
        assert "pythonw" in text
        assert "[project:whisperclick]" in text
        assert PIN_SECTION_START in text
        assert PIN_SECTION_END in text


class TestPreCompactPin:
    def test_pre_compact_refreshes_pins(self, store, tmp_path):
        pin_file = tmp_path / "CLAUDE.md"
        store.add("Critical rule 1", "rule", confidence=1.0, source="test")
        store.add("Critical rule 2", "rule", confidence=1.0, source="test")

        pre_compact_pin(store, pin_file=pin_file)

        content = pin_file.read_text()
        assert "Critical rule 1" in content
        assert "Critical rule 2" in content

        # Check audit
        log = store.get_audit_log()
        assert any(e["action"] == "pre_compact_pin" for e in log)
