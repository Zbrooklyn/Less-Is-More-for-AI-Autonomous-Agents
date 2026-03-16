#!/usr/bin/env python3
"""Migrate API keys from .env files to Windows Credential Manager.

Scans known .env locations, extracts key=value pairs, stores them via keyring,
and reports what was migrated. Does NOT delete .env files — that's manual.

Usage:
  python scripts/migrate-credentials.py              # Dry run (show what would be migrated)
  python scripts/migrate-credentials.py --execute    # Actually migrate
  python scripts/migrate-credentials.py --verify     # Verify stored credentials
"""

import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.credentials import broker as cred_broker

# Known .env locations to scan
ENV_LOCATIONS = [
    Path.home() / ".claude" / ".env",
    Path("C:/Users/Owner/Downloads/AI_Projects/.env"),
    Path("C:/Users/Owner/Downloads/AI_Projects/projects/easy-ecommerce-group/.env"),
    Path("C:/Users/Owner/Downloads/AI_Projects/projects/easy-ecommerce-group/.env.local"),
    Path("C:/Users/Owner/Downloads/AI_Projects/projects/WhisperClick Electron/.env"),
    Path("C:/Users/Owner/Downloads/AI_Projects/projects/mission-control/.env"),
]

# Map env var names to service names and scopes
SERVICE_MAP = {
    "ANTHROPIC_API_KEY": ("anthropic", "global"),
    "OPENAI_API_KEY": ("openai", "global"),
    "CLAUDE_API_KEY": ("anthropic", "global"),
    "SUPABASE_URL": ("supabase-url", "easy-ecommerce"),
    "SUPABASE_ANON_KEY": ("supabase-anon", "easy-ecommerce"),
    "SUPABASE_SERVICE_ROLE_KEY": ("supabase-service-role", "easy-ecommerce"),
    "NEXT_PUBLIC_SUPABASE_URL": ("supabase-url", "easy-ecommerce"),
    "NEXT_PUBLIC_SUPABASE_ANON_KEY": ("supabase-anon", "easy-ecommerce"),
    "CLOUDFLARE_API_TOKEN": ("cloudflare", "global"),
    "GOOGLE_CLIENT_ID": ("google-client-id", "easy-ecommerce"),
    "GOOGLE_CLIENT_SECRET": ("google-client-secret", "easy-ecommerce"),
    "DEEPGRAM_API_KEY": ("deepgram", "whisperclick"),
    "GROQ_API_KEY": ("groq", "whisperclick"),
}


def parse_env_file(path: Path) -> dict[str, str]:
    """Parse a .env file into key=value pairs."""
    if not path.exists():
        return {}

    pairs = {}
    text = path.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", line)
        if match:
            key = match.group(1)
            value = match.group(2).strip().strip("'\"")
            if value:  # Skip empty values
                pairs[key] = value
    return pairs


def scan_all() -> dict[str, dict]:
    """Scan all known .env files and return findings."""
    findings = {}
    for env_path in ENV_LOCATIONS:
        pairs = parse_env_file(env_path)
        for key, value in pairs.items():
            if key not in findings:  # First occurrence wins
                findings[key] = {
                    "value": value,
                    "source": str(env_path),
                    "service": SERVICE_MAP.get(key, (key.lower().replace("_", "-"), "global")),
                }
    return findings


def cmd_dry_run():
    """Show what would be migrated without doing anything."""
    findings = scan_all()
    if not findings:
        print("No .env files found or all are empty.")
        return

    print(f"\nFound {len(findings)} credentials to migrate:\n")
    for key, info in sorted(findings.items()):
        service, scope = info["service"]
        value_preview = info["value"][:8] + "..." if len(info["value"]) > 8 else info["value"]
        print(f"  {key}")
        print(f"    Source: {info['source']}")
        print(f"    Store as: autonomous-agent/{scope}/{service}")
        print(f"    Value: {value_preview}")
        print()

    print("Run with --execute to actually migrate.")


def cmd_execute():
    """Actually migrate credentials to Windows Credential Manager."""
    findings = scan_all()
    if not findings:
        print("No credentials to migrate.")
        return

    broker = cred_broker
    migrated = 0
    skipped = 0

    for key, info in sorted(findings.items()):
        service, scope = info["service"]

        # Check if already stored
        existing = broker.get(service, scope=scope)
        if existing:
            print(f"  SKIP {key} → already stored as {service} ({scope})")
            skipped += 1
            continue

        broker.set(service, info["value"], scope=scope)
        print(f"  MIGRATED {key} → {service} ({scope})")
        migrated += 1

    print(f"\nDone: {migrated} migrated, {skipped} skipped (already existed).")
    if migrated > 0:
        print("\nNext steps:")
        print("1. Verify with: python scripts/migrate-credentials.py --verify")
        print("2. Clear .env files manually once verified")


def cmd_verify():
    """Verify that all expected credentials are stored."""
    broker = cred_broker
    findings = scan_all()

    print("\nCredential verification:\n")
    all_ok = True
    for key, info in sorted(findings.items()):
        service, scope = info["service"]
        stored = broker.get(service, scope=scope)
        if stored:
            matches = stored == info["value"]
            status = "OK" if matches else "MISMATCH"
            if not matches:
                all_ok = False
            print(f"  [{status}] {service} ({scope})")
        else:
            print(f"  [MISSING] {service} ({scope}) — not in Credential Manager")
            all_ok = False

    if all_ok:
        print("\nAll credentials verified.")
    else:
        print("\nSome credentials missing or mismatched. Run --execute to fix.")


def main():
    parser = argparse.ArgumentParser(description="Migrate .env credentials to Windows Credential Manager")
    parser.add_argument("--execute", action="store_true", help="Actually perform the migration")
    parser.add_argument("--verify", action="store_true", help="Verify stored credentials")
    args = parser.parse_args()

    if args.verify:
        cmd_verify()
    elif args.execute:
        cmd_execute()
    else:
        cmd_dry_run()


if __name__ == "__main__":
    main()
