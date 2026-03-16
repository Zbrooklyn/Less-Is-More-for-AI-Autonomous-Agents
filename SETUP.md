# Setup Guide

## Prerequisites
- Python 3.12+
- Windows 11 (some features use Windows APIs)
- Git

## Quick Start

```bash
cd C:/Users/Owner/Documents/autonomous-ai-agent

# 1. Create and activate venv (if not already done)
python -m venv venv
./venv/Scripts/activate

# 2. Install the package with all dependencies
pip install -e ".[all,dev]"

# 3. Populate the memory database from existing markdown files
memory-cli migrate

# 4. Seed enforcement rules (pythonw.exe, git push public, etc.)
python scripts/seed-rules.py

# 5. Generate embeddings for semantic search (takes ~30s on first run)
memory-cli embed

# 6. Verify everything works
pytest tests/ -q
```

## Subsystem Commands

After `pip install -e .`, these commands are available:

| Command | What it does |
|---------|-------------|
| `memory-cli stats` | Show memory database statistics |
| `memory-cli query "pywebview"` | Search memory entries |
| `memory-cli enforce --tool Bash --input "pythonw.exe"` | Test enforcement rules |
| `memory-cli capture "Don't use X"` | Test correction detection |
| `cred-cli list` | List stored credentials |
| `cred-cli scan "text with sk-abc123"` | Scan text for secrets |
| `daemon-service start` | Start the daemon as a background process |
| `daemon-service status` | Check if the daemon is running |
| `daemon-service schedule` | Auto-start daemon at login (Task Scheduler) |

Or use the unified launcher:
```bash
python -m src memory stats
python -m src daemon
python -m src cred scan "text"
```

## Claude Code Hook Wiring

The hooks are already configured in `~/.claude/hooks.json`:
- **SessionStart** — auto-injects relevant memories
- **PreToolUse** — enforces rules (blocks pythonw.exe, git push public, etc.)
- **PostToolUse** — verifies tool output compliance
- **PreCompact** — pins critical rules before context compression

## Running Tests

```bash
# Full suite
pytest tests/ -q

# Specific module
pytest tests/test_memory_store.py -v

# With coverage (if installed)
pytest tests/ --cov=src --cov-report=term-missing
```
