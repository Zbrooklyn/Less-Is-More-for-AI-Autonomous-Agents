"""cred-cli — Command-line interface for credential management and secret scanning."""

import argparse
import getpass
import sys
from pathlib import Path

# Fix Windows terminal encoding for Unicode
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from src.credentials import broker
from src.credentials.scanner import redact, scan_output


def cmd_get(args):
    """Retrieve a credential."""
    value = broker.get(args.service, scope=args.scope)
    if value is None:
        scope_display = args.scope or "global"
        print(f"No credential found for '{args.service}' (scope: {scope_display})")
        return 1
    print(value)
    return 0


def cmd_set(args):
    """Store a credential."""
    if args.value:
        value = args.value
    else:
        value = getpass.getpass(f"Enter value for '{args.service}': ")

    broker.set(args.service, value, scope=args.scope)
    scope_display = args.scope or "global"
    print(f"Stored credential for '{args.service}' (scope: {scope_display})")
    return 0


def cmd_delete(args):
    """Delete a credential."""
    deleted = broker.delete(args.service, scope=args.scope)
    scope_display = args.scope or "global"
    if deleted:
        print(f"Deleted credential for '{args.service}' (scope: {scope_display})")
        return 0
    else:
        print(f"No credential found for '{args.service}' (scope: {scope_display})")
        return 1


def cmd_list(_args):
    """List all stored credentials."""
    services = broker.list_services()
    if not services:
        print("No credentials stored (or enumeration not supported on this backend).")
        return 0
    print("Stored credentials:")
    for svc in services:
        print(f"  {svc}")
    return 0


def cmd_scan(args):
    """Scan text for leaked secrets."""
    if args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"File not found: {args.file}", file=sys.stderr)
            return 1
        text = path.read_text(encoding="utf-8", errors="replace")
    elif args.text:
        text = " ".join(args.text)
    else:
        # Read from stdin
        text = sys.stdin.read()

    findings = scan_output(text)
    if not findings:
        print("No secrets detected.")
        return 0

    print(f"Found {len(findings)} potential secret(s):\n")
    for i, f in enumerate(findings, 1):
        # Show truncated match for safety
        match_display = f["match"]
        if len(match_display) > 20:
            match_display = match_display[:10] + "..." + match_display[-6:]
        print(f"  {i}. [{f['severity'].upper()}] {f['pattern']}")
        print(f"     Match: {match_display}")
    return 1  # non-zero = secrets found


def cmd_redact(args):
    """Redact secrets from text and print the result."""
    if args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"File not found: {args.file}", file=sys.stderr)
            return 1
        text = path.read_text(encoding="utf-8", errors="replace")
    elif args.text:
        text = " ".join(args.text)
    else:
        text = sys.stdin.read()

    print(redact(text))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="cred-cli", description="Credential management and secret scanning")

    sub = parser.add_subparsers(dest="command")

    # get
    p_get = sub.add_parser("get", help="Retrieve a credential")
    p_get.add_argument("service", help="Service name (e.g., 'openai')")
    p_get.add_argument("--scope", help="Project scope (default: global)")

    # set
    p_set = sub.add_parser("set", help="Store a credential")
    p_set.add_argument("service", help="Service name (e.g., 'openai')")
    p_set.add_argument("--scope", help="Project scope (default: global)")
    p_set.add_argument("--value", help="Credential value (prompted if omitted)")

    # delete
    p_del = sub.add_parser("delete", help="Delete a credential")
    p_del.add_argument("service", help="Service name")
    p_del.add_argument("--scope", help="Project scope (default: global)")

    # list
    sub.add_parser("list", help="List all stored credentials")

    # scan
    p_scan = sub.add_parser("scan", help="Scan text for leaked secrets")
    p_scan.add_argument("text", nargs="*", help="Text to scan (reads stdin if omitted)")
    p_scan.add_argument("--file", help="File to scan instead of text argument")

    # redact
    p_redact = sub.add_parser("redact", help="Redact secrets from text")
    p_redact.add_argument("text", nargs="*", help="Text to redact (reads stdin if omitted)")
    p_redact.add_argument("--file", help="File to redact instead of text argument")

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "get": cmd_get,
        "set": cmd_set,
        "delete": cmd_delete,
        "list": cmd_list,
        "scan": cmd_scan,
        "redact": cmd_redact,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main() or 0)
