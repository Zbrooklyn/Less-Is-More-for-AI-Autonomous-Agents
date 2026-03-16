"""Sandbox manager — git-worktree-based isolated execution environments.

Each sandbox is a git worktree on its own branch, stored under `.sandboxes/`
relative to the repo root.  This gives every agent task a full, writable copy
of the repo without touching the main working tree.
"""

import subprocess
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class SandboxInfo:
    """Metadata for an active sandbox."""

    name: str
    path: Path
    branch: str
    created_at: str


@dataclass
class RunResult:
    """Result of running a command inside a sandbox."""

    stdout: str
    stderr: str
    returncode: int


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_git(args: list[str], cwd: Optional[Path] = None, check: bool = True) -> subprocess.CompletedProcess:
    """Run a git command and return the CompletedProcess."""
    return subprocess.run(
        ["git"] + args,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=check,
    )


class SandboxManager:
    """Manage isolated git-worktree sandboxes.

    Parameters
    ----------
    repo_root : Path
        Root of the git repository that owns the worktrees.
    """

    def __init__(self, repo_root: Path):
        self.repo_root = Path(repo_root).resolve()
        self.sandboxes_dir = self.repo_root / ".sandboxes"
        self.sandboxes_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create(self, name: str, base_branch: str = "master") -> SandboxInfo:
        """Create an isolated git worktree sandbox.

        Raises
        ------
        ValueError
            If a sandbox with *name* already exists.
        """
        sandbox_path = self.sandboxes_dir / name
        if sandbox_path.exists():
            raise ValueError(f"Sandbox '{name}' already exists at {sandbox_path}")

        branch_name = f"sandbox/{name}"

        # Create a new branch from base_branch and add a worktree for it
        _run_git(["worktree", "add", "-b", branch_name, str(sandbox_path), base_branch],
                 cwd=self.repo_root)

        return SandboxInfo(
            name=name,
            path=sandbox_path,
            branch=branch_name,
            created_at=_now_iso(),
        )

    def run(self, name: str, command: str) -> RunResult:
        """Run a shell command inside a sandbox.

        Raises
        ------
        ValueError
            If the sandbox does not exist.
        """
        sandbox_path = self._require(name)

        result = subprocess.run(
            command,
            shell=True,
            cwd=str(sandbox_path),
            capture_output=True,
            text=True,
        )

        return RunResult(
            stdout=result.stdout,
            stderr=result.stderr,
            returncode=result.returncode,
        )

    def destroy(self, name: str) -> None:
        """Remove a sandbox worktree and its branch.

        Raises
        ------
        ValueError
            If the sandbox does not exist.
        """
        sandbox_path = self._require(name)
        branch_name = f"sandbox/{name}"

        # Remove the worktree
        _run_git(["worktree", "remove", "--force", str(sandbox_path)],
                 cwd=self.repo_root, check=False)

        # If worktree removal didn't clean the dir, do it manually
        if sandbox_path.exists():
            shutil.rmtree(sandbox_path, ignore_errors=True)

        # Delete the branch (best-effort — may already be gone)
        _run_git(["branch", "-D", branch_name], cwd=self.repo_root, check=False)

    def list_sandboxes(self) -> list[SandboxInfo]:
        """List all active sandboxes in the `.sandboxes/` directory."""
        if not self.sandboxes_dir.exists():
            return []

        sandboxes: list[SandboxInfo] = []
        result = _run_git(["worktree", "list", "--porcelain"], cwd=self.repo_root, check=False)

        # Parse porcelain output: blocks separated by blank lines
        # Each block has lines like: worktree /path, HEAD <hash>, branch refs/heads/...
        worktrees: dict[str, dict[str, str]] = {}
        current: dict[str, str] = {}
        for line in result.stdout.splitlines():
            if not line.strip():
                if current.get("worktree"):
                    worktrees[current["worktree"]] = current
                current = {}
            else:
                parts = line.split(" ", 1)
                key = parts[0]
                val = parts[1] if len(parts) > 1 else ""
                current[key] = val
        if current.get("worktree"):
            worktrees[current["worktree"]] = current

        # Match worktrees to sandbox directories
        sandboxes_str = str(self.sandboxes_dir)
        for wt_path, info in worktrees.items():
            # Normalise paths for comparison
            wt_norm = str(Path(wt_path).resolve())
            if not wt_norm.startswith(str(Path(sandboxes_str).resolve())):
                continue
            name = Path(wt_path).name
            branch = info.get("branch", "").replace("refs/heads/", "")
            sandboxes.append(SandboxInfo(
                name=name,
                path=Path(wt_path),
                branch=branch,
                created_at="",  # git doesn't store creation time
            ))

        return sandboxes

    def diff(self, name: str) -> str:
        """Show uncommitted changes in the sandbox vs its HEAD.

        Returns the raw diff output string (may be empty).

        Raises
        ------
        ValueError
            If the sandbox does not exist.
        """
        sandbox_path = self._require(name)
        result = _run_git(["diff", "HEAD"], cwd=sandbox_path, check=False)
        return result.stdout

    def promote(self, name: str, target_branch: str = "master") -> str:
        """Merge sandbox changes back to *target_branch*.

        Returns the merge output.

        Raises
        ------
        ValueError
            If the sandbox does not exist.
        """
        self._require(name)
        branch_name = f"sandbox/{name}"

        result = _run_git(["merge", branch_name, "--no-edit"],
                          cwd=self.repo_root)
        return result.stdout

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require(self, name: str) -> Path:
        """Return the sandbox path or raise ValueError."""
        sandbox_path = self.sandboxes_dir / name
        if not sandbox_path.exists():
            raise ValueError(f"Sandbox '{name}' does not exist")
        return sandbox_path
