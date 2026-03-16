"""Tests for sandbox manager — create, run, destroy, list, diff, duplicates, missing."""

import subprocess
from pathlib import Path

import pytest

from src.sandbox.manager import SandboxManager, SandboxInfo


@pytest.fixture
def git_repo(tmp_path):
    """Create a temporary git repo with an initial commit for isolation."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=str(repo), capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=str(repo), capture_output=True, check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=str(repo), capture_output=True, check=True,
    )
    # Create an initial commit so branches can be created
    (repo / "README.md").write_text("# Test repo\n")
    subprocess.run(["git", "add", "."], cwd=str(repo), capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=str(repo), capture_output=True, check=True,
    )
    return repo


@pytest.fixture
def mgr(git_repo):
    """SandboxManager backed by the temporary git repo."""
    return SandboxManager(git_repo)


class TestCreate:
    """Sandbox creation via git worktree."""

    def test_create_makes_worktree_directory(self, mgr, git_repo):
        info = mgr.create("alpha")
        assert isinstance(info, SandboxInfo)
        assert info.name == "alpha"
        assert info.path.exists()
        assert info.path.is_dir()
        # The worktree should contain the same files as the base
        assert (info.path / "README.md").exists()

    def test_create_sets_branch_name(self, mgr):
        info = mgr.create("beta")
        assert info.branch == "sandbox/beta"

    def test_create_populates_created_at(self, mgr):
        info = mgr.create("gamma")
        assert info.created_at  # non-empty ISO timestamp

    def test_cannot_create_duplicate(self, mgr):
        mgr.create("dup")
        with pytest.raises(ValueError, match="already exists"):
            mgr.create("dup")


class TestRun:
    """Command execution inside a sandbox."""

    def test_run_executes_command(self, mgr):
        mgr.create("runner")
        result = mgr.run("runner", "echo hello")
        assert result.returncode == 0
        assert "hello" in result.stdout

    def test_run_captures_stderr(self, mgr):
        mgr.create("stderr-test")
        result = mgr.run("stderr-test", "echo oops >&2")
        assert "oops" in result.stderr

    def test_run_returns_nonzero_on_failure(self, mgr):
        mgr.create("fail-test")
        result = mgr.run("fail-test", "exit 42")
        assert result.returncode == 42

    def test_run_works_in_sandbox_directory(self, mgr):
        info = mgr.create("cwd-test")
        result = mgr.run("cwd-test", "git branch --show-current")
        assert "sandbox/cwd-test" in result.stdout

    def test_run_nonexistent_sandbox(self, mgr):
        with pytest.raises(ValueError, match="does not exist"):
            mgr.run("ghost", "echo hi")


class TestDestroy:
    """Sandbox cleanup."""

    def test_destroy_removes_directory(self, mgr):
        info = mgr.create("cleanup")
        assert info.path.exists()
        mgr.destroy("cleanup")
        assert not info.path.exists()

    def test_destroy_nonexistent_fails_gracefully(self, mgr):
        with pytest.raises(ValueError, match="does not exist"):
            mgr.destroy("nonexistent")


class TestList:
    """Listing active sandboxes."""

    def test_list_empty(self, mgr):
        sandboxes = mgr.list_sandboxes()
        assert sandboxes == []

    def test_list_returns_active_sandboxes(self, mgr):
        mgr.create("one")
        mgr.create("two")
        sandboxes = mgr.list_sandboxes()
        names = {s.name for s in sandboxes}
        assert "one" in names
        assert "two" in names

    def test_list_excludes_destroyed(self, mgr):
        mgr.create("keep")
        mgr.create("remove")
        mgr.destroy("remove")
        sandboxes = mgr.list_sandboxes()
        names = {s.name for s in sandboxes}
        assert "keep" in names
        assert "remove" not in names


class TestDiff:
    """Diff detection in sandboxes."""

    def test_diff_empty_on_clean_sandbox(self, mgr):
        mgr.create("clean")
        output = mgr.diff("clean")
        assert output.strip() == ""

    def test_diff_shows_changes(self, mgr):
        info = mgr.create("dirty")
        # Modify a tracked file inside the sandbox
        readme = info.path / "README.md"
        readme.write_text("# Modified\n")
        output = mgr.diff("dirty")
        assert "Modified" in output
        assert "diff" in output.lower() or "---" in output

    def test_diff_nonexistent_sandbox(self, mgr):
        with pytest.raises(ValueError, match="does not exist"):
            mgr.diff("nope")
