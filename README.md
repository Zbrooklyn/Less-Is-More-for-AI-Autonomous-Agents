# Less Is More for AI Autonomous Agents

> A framework for the minimum viable toolkit that gives an AI agent maximum capability, reliability, and efficiency — plus a working implementation of all 10 components.

## The Premise

There is no need to add hundreds of tools for an AI agent. A terminal is Turing-complete. In theory, one tool is sufficient. In practice, the gap between "can do it" and "does it reliably" is where real work lives.

**Six raw capabilities** cover everything a computer can do: terminal, web browser, desktop vision, interactive PTY, persistent listener, and audio/video I/O. Everything else is an **accuracy multiplier** — specialized tools that don't enable anything new, but make the success rate go from 40% to 99%.

This repo contains both the research framework and its implementation.

## The 10 Components

| # | Component | Status | Code |
|---|-----------|--------|------|
| 1 | Terminal + Structured Tools | **Built** | `src/memory/` (store, CLI, migration) |
| 2 | Web Browser | **Built** | `src/browser/` (search, fetch, forms, cookies) |
| 3 | Desktop Vision + Control | **Built** | `src/vision/` (screenshots, mouse/keyboard, window automation) |
| 4 | Memory With Teeth | **Built** | `src/memory/` + `src/hooks/` (6 levels: inject, enforce, capture, pin, verify, query) |
| 5 | Stateful Agent Daemon | **Built** | `src/daemon/` (event bus, triage, state, authority, loop, service) |
| 6 | Interactive PTY | **Built** | `src/pty/` (subprocess sessions, debugger attachment) |
| 7 | Audio/Video I/O | **Built** | `src/audio/` (mic capture, Whisper, TTS, VAD) |
| 8 | Sandboxed Execution | **Built** | `src/sandbox/` (git worktree isolation) |
| 9 | Credential Management | **Built** | `src/credentials/` (keyring broker, secret scanner) |
| 10 | Multi-Agent Orchestration | **Built** | `src/orchestrator/` (supervisor/worker, shared context, conflict resolution) |

All 10 components implemented. 508 tests passing.

## Quick Start

```bash
git clone https://github.com/Zbrooklyn/less-is-more-ai-agents.git
cd less-is-more-ai-agents
python -m venv venv && ./venv/Scripts/activate  # or source venv/bin/activate
pip install -e ".[all,dev]"
memory-cli migrate
python scripts/seed-rules.py
memory-cli embed
pytest tests/ -q
```

See [SETUP.md](SETUP.md) for detailed instructions.

## Repository Structure

```
.
├── research/                    The "why" — framework and analysis
│   ├── README.md                Full deep-dive (~1250 lines)
│   ├── EXECUTIVE-SUMMARY.md     One-page overview
│   ├── components/              10 component deep-dives + roadmap + scorecard
│   └── GLOSSARY.md
│
├── src/                         The "how" — working implementation
│   ├── memory/                  SQLite store, FTS5, embeddings, injection, migration
│   ├── hooks/                   Enforcement, correction capture, pinning, verification
│   ├── credentials/             Keyring broker, secret scanner, redaction
│   ├── daemon/                  Event bus, triage, state, authority, loop, watcher, webhook
│   ├── browser/                 httpx+BS4 engine (Playwright fallback)
│   ├── sandbox/                 Git worktree isolation
│   ├── pty/                     Interactive subprocess sessions
│   ├── vision/                  Screenshots, mouse/keyboard, window automation
│   ├── audio/                   Mic capture, Whisper, TTS, VAD
│   └── orchestrator/            Supervisor/worker, shared context, messages
│
├── tests/                       508 tests
├── scripts/                     Hook scripts, seed rules, credential migration
├── ROADMAP.md                   16-step build plan (all complete)
├── SETUP.md                     Installation and usage guide
└── pyproject.toml               Package config (v1.0.0)
```

## The Research

The research framework identifies the 10 components needed for a fully autonomous AI agent, scores 17 existing tools against them, and provides an implementation roadmap.

Start here:
- **[Executive Summary](research/EXECUTIVE-SUMMARY.md)** — one page, the whole framework
- **[Full Deep-Dive](research/README.md)** — the complete analysis (~1250 lines)
- **[Agent Framework Scorecard](research/components/12-agent-framework-scorecard.md)** — 17 tools scored
- **[Implementation Roadmap](research/components/11-implementation-roadmap.md)** — the build plan

## License

MIT — see [research/LICENSE](research/LICENSE).
