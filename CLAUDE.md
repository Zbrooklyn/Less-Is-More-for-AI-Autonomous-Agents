# CLAUDE.md — Autonomous AI Agent

## Project Overview
10-component autonomous AI agent infrastructure. Python 3.12, SQLite, all tests via pytest.

## Commands
- **Tests:** `pytest tests/ -q` (508 tests)
- **Memory CLI:** `python -m src memory <command>` (query/add/stats/enforce/capture/verify/pin/migrate/embed)
- **Credential CLI:** `python -m src cred <command>` (get/set/delete/list/scan/redact)
- **Daemon:** `python -m src daemon` (starts event loop)
- **Full setup:** `pip install -e ".[all,dev]" && memory-cli migrate && python scripts/seed-rules.py && memory-cli embed`

## Key Files
- `src/memory/store.py` — Core SQLite store (all modules depend on this)
- `src/hooks/enforce.py` — Pre-tool-call enforcement engine
- `src/daemon/loop.py` — Main daemon event processing loop
- `scripts/seed-rules.py` — Seeds enforcement rules into the DB
- `scripts/hook-*.py` — Claude Code hook scripts (wired in ~/.claude/hooks.json)

## Rules
- Always run `pytest tests/ -q` after changes
- Never commit the `demo.db` or `~/.claude/memory/memory.db` files (gitignored)
- Hook scripts must complete in <500ms (no embedding model loading in hooks)
- Use `--no-verify` for commits (pre-commit hook false-positives on scanner patterns)

<!-- PINNED_RULES_START -->

## Pinned Rules (auto-managed — do not edit manually)

_No pinned rules._

<!-- PINNED_RULES_END -->
