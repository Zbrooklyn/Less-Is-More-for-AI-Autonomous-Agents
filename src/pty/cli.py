"""pty-cli — Command-line interface for interactive PTY sessions."""

import argparse
import sys

from src.pty.session import SessionManager

# Module-level session manager (persistent across CLI calls in same process)
_manager: SessionManager | None = None


def _get_manager() -> SessionManager:
    """Get or create the module-level SessionManager."""
    global _manager
    if _manager is None:
        _manager = SessionManager()
    return _manager


def cmd_create(manager: SessionManager, args) -> int:
    """Create a new named PTY session."""
    try:
        manager.create(args.name, command=args.command)
        print(f"Created session '{args.name}' (command: {args.command})")
        return 0
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_send(manager: SessionManager, args) -> int:
    """Send input to a named session."""
    try:
        text = " ".join(args.text)
        manager.send(args.name, text)
        print(f"Sent to '{args.name}': {text}")
        return 0
    except KeyError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_read(manager: SessionManager, args) -> int:
    """Read output from a named session."""
    try:
        output = manager.read(args.name, timeout=args.timeout)
        if output:
            print(output, end="")
        else:
            print(f"(no output from '{args.name}' within {args.timeout}s)")
        return 0
    except KeyError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_list(manager: SessionManager, _args) -> int:
    """List all active sessions."""
    sessions = manager.list_sessions()
    if not sessions:
        print("No active sessions.")
        return 0

    print(f"{'Name':<20s} {'Status':<10s}")
    print("-" * 30)
    for s in sessions:
        print(f"{s['name']:<20s} {s['status']:<10s}")
    return 0


def cmd_close(manager: SessionManager, args) -> int:
    """Close a named session."""
    try:
        manager.close(args.name)
        print(f"Closed session '{args.name}'")
        return 0
    except KeyError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main(argv=None) -> int:
    """CLI entry point for PTY session management."""
    parser = argparse.ArgumentParser(
        prog="pty", description="Interactive PTY session manager"
    )
    sub = parser.add_subparsers(dest="command")

    # create
    p_create = sub.add_parser("create", help="Create a new named session")
    p_create.add_argument("name", help="Session name")
    p_create.add_argument(
        "--command", default="cmd.exe", help="Command to run (default: cmd.exe)"
    )

    # send
    p_send = sub.add_parser("send", help="Send input to a session")
    p_send.add_argument("name", help="Session name")
    p_send.add_argument("text", nargs="+", help="Text to send")

    # read
    p_read = sub.add_parser("read", help="Read output from a session")
    p_read.add_argument("name", help="Session name")
    p_read.add_argument(
        "--timeout", type=float, default=5.0, help="Read timeout in seconds"
    )

    # list
    sub.add_parser("list", help="List active sessions")

    # close
    p_close = sub.add_parser("close", help="Close a session")
    p_close.add_argument("name", help="Session name")

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1

    manager = _get_manager()
    commands = {
        "create": cmd_create,
        "send": cmd_send,
        "read": cmd_read,
        "list": cmd_list,
        "close": cmd_close,
    }
    return commands[args.command](manager, args)


if __name__ == "__main__":
    sys.exit(main() or 0)
