"""sandbox-cli — Command-line interface for sandbox management."""

import argparse
import sys
from pathlib import Path

# Fix Windows terminal encoding for Unicode
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from src.sandbox.manager import SandboxManager


def _resolve_repo_root() -> Path:
    """Walk up from cwd to find the git repo root."""
    import subprocess

    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode == 0:
        return Path(result.stdout.strip())
    # Fallback: current directory
    return Path.cwd()


def cmd_create(mgr: SandboxManager, args):
    info = mgr.create(args.name, base_branch=args.base)
    print(f"Created sandbox '{info.name}'")
    print(f"  Path:   {info.path}")
    print(f"  Branch: {info.branch}")


def cmd_run(mgr: SandboxManager, args):
    command = " ".join(args.command)
    result = mgr.run(args.name, command)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result.returncode


def cmd_list(mgr: SandboxManager, _args):
    sandboxes = mgr.list_sandboxes()
    if not sandboxes:
        print("No active sandboxes.")
        return
    for sb in sandboxes:
        print(f"  {sb.name:20s}  branch={sb.branch}  path={sb.path}")


def cmd_diff(mgr: SandboxManager, args):
    output = mgr.diff(args.name)
    if output:
        print(output, end="")
    else:
        print("No changes in sandbox.")


def cmd_destroy(mgr: SandboxManager, args):
    mgr.destroy(args.name)
    print(f"Destroyed sandbox '{args.name}'.")


def cmd_promote(mgr: SandboxManager, args):
    output = mgr.promote(args.name, target_branch=args.target)
    print(f"Promoted sandbox '{args.name}' to '{args.target}'.")
    if output:
        print(output, end="")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="sandbox-cli", description="Git-worktree sandbox manager")
    parser.add_argument("--repo", type=str, help="Git repo root (default: auto-detect)")

    sub = parser.add_subparsers(dest="command")

    # create
    p_create = sub.add_parser("create", help="Create a new sandbox")
    p_create.add_argument("name", help="Sandbox name")
    p_create.add_argument("--base", default="master", help="Base branch (default: master)")

    # run
    p_run = sub.add_parser("run", help="Run a command inside a sandbox")
    p_run.add_argument("name", help="Sandbox name")
    p_run.add_argument("command", nargs="+", help="Command to execute")

    # list
    sub.add_parser("list", help="List active sandboxes")

    # diff
    p_diff = sub.add_parser("diff", help="Show sandbox changes")
    p_diff.add_argument("name", help="Sandbox name")

    # destroy
    p_destroy = sub.add_parser("destroy", help="Destroy a sandbox")
    p_destroy.add_argument("name", help="Sandbox name")

    # promote
    p_promote = sub.add_parser("promote", help="Merge sandbox back to target branch")
    p_promote.add_argument("name", help="Sandbox name")
    p_promote.add_argument("--target", default="master", help="Target branch (default: master)")

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1

    repo_root = Path(args.repo) if args.repo else _resolve_repo_root()
    mgr = SandboxManager(repo_root)

    try:
        commands = {
            "create": cmd_create,
            "run": cmd_run,
            "list": cmd_list,
            "diff": cmd_diff,
            "destroy": cmd_destroy,
            "promote": cmd_promote,
        }
        result = commands[args.command](mgr, args)
        return result or 0
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main() or 0)
