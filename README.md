# Less Is More for AI Autonomous Agents

![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)
![Tests](https://img.shields.io/badge/tests-508%20passing-brightgreen.svg)
![Version](https://img.shields.io/badge/version-1.0.0-orange.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

> A framework for the minimum viable toolkit that gives an AI agent maximum capability, reliability, and efficiency — plus a working implementation of all 10 components.

---

## The Premise

There is no need to add hundreds of tools for an AI agent. A terminal is Turing-complete. In theory, one tool is sufficient. In practice, the gap between "can do it" and "does it reliably" is where real work lives.

**Six raw capabilities** cover everything a computer can do: terminal, web browser, desktop vision, interactive PTY, persistent listener, and audio/video I/O. Everything else is an **accuracy multiplier** — specialized tools that don't enable anything new, but make the success rate go from 40% to 99%.

This repo contains both the research framework and its working implementation.

## The 10 Components

| # | Component | What It Does | Code |
|---|-----------|-------------|------|
| 1 | **Terminal + Structured Tools** | SQLite memory store, FTS5 search, CLI, markdown migration | `src/memory/` |
| 2 | **Web Browser** | Search, fetch, form filling, cookies (httpx + Playwright) | `src/browser/` |
| 3 | **Desktop Vision + Control** | Screenshots, mouse/keyboard, window automation | `src/vision/` |
| 4 | **Memory With Teeth** | 6 levels: inject, enforce, capture, pin, verify, query | `src/hooks/` |
| 5 | **Stateful Agent Daemon** | Event bus, triage, 4-tier authority, background service | `src/daemon/` |
| 6 | **Interactive PTY** | Persistent subprocess sessions, debugger attachment | `src/pty/` |
| 7 | **Audio/Video I/O** | Mic capture, Whisper transcription, TTS, voice detection | `src/audio/` |
| 8 | **Sandboxed Execution** | Git worktree isolation for safe experimentation | `src/sandbox/` |
| 9 | **Credential Management** | OS keyring broker, 14-pattern secret scanner, redaction | `src/credentials/` |
| 10 | **Multi-Agent Orchestration** | Supervisor/worker, shared context, file locking, replanning | `src/orchestrator/` |

All 10 components implemented. 508 tests.

## Quick Start

```bash
git clone https://github.com/Zbrooklyn/Less-Is-More-for-AI-Autonomous-Agents.git
cd Less-Is-More-for-AI-Autonomous-Agents
python -m venv venv
source venv/bin/activate  # or ./venv/Scripts/activate on Windows
pip install -e ".[all,dev]"
memory-cli migrate        # Import markdown memory into SQLite
python scripts/seed-rules.py  # Seed enforcement rules
memory-cli embed          # Generate embeddings for semantic search
pytest tests/ -q          # 508 tests
```

## How It Works

### Memory With Teeth (the core innovation)

Most AI agents have no memory between sessions. This one has a 6-level memory system:

1. **Auto-injection** — Relevant memories load at session start based on what project you're working on
2. **Enforcement** — Rules like "never use pythonw.exe" are enforced *before* the tool executes, not after
3. **Correction capture** — When you correct the agent ("don't do X"), it's logged and deduplicated
4. **Auto-promotion** — Same correction 3 times? It becomes an enforcement rule automatically
5. **Pinning** — Critical rules are written to config files so they survive context window compression
6. **Verification** — Post-action compliance checking catches violations in tool output

### The Daemon

A background process that watches for events and acts within boundaries:

- **File watcher** (watchdog) detects changes and triages them (`.pyc` = noise, `.py` = interesting, `CLAUDE.md` = critical)
- **4-tier authority**: autonomous (run tests) → act+notify (fix lint) → propose+wait (code changes) → alert only (deploys)
- **Daily digest** summarizes what happened overnight
- **Windows Service wrapper** with Task Scheduler auto-start

### Multi-Agent Orchestration

Supervisor decomposes complex tasks into worker assignments:

- **Shared context store** (SQLite) for cross-agent state
- **File-level locking** prevents two workers from editing the same file
- **Message passing** between agents with read/unread tracking
- **Conflict resolution** and **replanning** when things go wrong

## Repository Structure

```
research/                 The "why" — 10-component framework
  README.md               Full deep-dive (~1250 lines)
  EXECUTIVE-SUMMARY.md    One-page overview
  components/             Deep-dives, scorecard (17 agents), roadmap

src/                      The "how" — working Python implementation
  memory/                 SQLite + FTS5 + embeddings + injection
  hooks/                  Enforcement, capture, pinning, verification
  credentials/            OS keyring broker, secret scanner
  daemon/                 Event bus, triage, state, authority, loop
  browser/                httpx + BeautifulSoup (Playwright fallback)
  sandbox/                Git worktree isolation
  pty/                    Subprocess sessions, debugger
  vision/                 mss screenshots, pyautogui, UI automation
  audio/                  sounddevice, Whisper, pyttsx3, VAD
  orchestrator/           Supervisor/worker, shared context

tests/                    508 tests
scripts/                  Hook scripts, seed rules, migration tools
```

## The Research

The framework identifies the minimum viable toolkit by asking: what are the actual *capabilities* vs *accuracy multipliers*?

- **[Executive Summary](research/EXECUTIVE-SUMMARY.md)** — One page, the whole framework
- **[Full Deep-Dive](research/README.md)** — Complete analysis (~1250 lines)
- **[Agent Framework Scorecard](research/components/12-agent-framework-scorecard.md)** — 17 autonomous AI agents scored on all 10 components
- **[Implementation Roadmap](research/components/11-implementation-roadmap.md)** — Dependency graph and build order

## CLI Tools

After `pip install -e "."`:

```bash
memory-cli query "pywebview"           # Search memory
memory-cli enforce --tool Bash --input "pythonw.exe"  # Test enforcement
memory-cli capture "Don't use X"       # Test correction detection
cred-cli scan "text with sk-abc123"    # Scan for leaked secrets
daemon-service start                   # Start background daemon
daemon-service status                  # Check daemon status
```

## License

[MIT](LICENSE)
