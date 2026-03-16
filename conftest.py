"""Pytest configuration — exclude live torture tests from normal test runs."""

collect_ignore = ["tests/test_live_torture.py"]
