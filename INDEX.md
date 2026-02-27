# Index — Document Navigation

## How to Read This Repository

**New here?** Start with the [Executive Summary](EXECUTIVE-SUMMARY.md) — one page, the whole framework.

**Want the full story?** Read the [README](README.md) — the complete deep-dive built as a conversation, ~1250 lines.

**Want to go deep on one component?** Jump to the relevant [component document](#component-deep-dives) below.

**Want to know who's winning?** The [Agent Framework Scorecard](components/12-agent-framework-scorecard.md) scores 17 autonomous AI agents against all 10 components — from code-first tools to general-purpose platforms.

**Want to build it?** The [Implementation Roadmap](components/11-implementation-roadmap.md) gives the build order, and the [Deep Spec](components/13-deep-spec-highest-impact-component.md) gives the technical blueprint for the first component.

---

## Overview Documents

| Document | Description |
|----------|-------------|
| [README.md](README.md) | The full deep-dive — all 10 components explored in conversational detail (~1250 lines) |
| [EXECUTIVE-SUMMARY.md](EXECUTIVE-SUMMARY.md) | One-page framework overview with market context and key findings |
| [GLOSSARY.md](GLOSSARY.md) | Definitions of all terms coined or used throughout the framework |
| [LICENSE](LICENSE) | MIT License |

---

## README.md — Section Map

### Part 1: The Foundation
| Section | Line | Topic |
|---------|------|-------|
| The Core Premise | 7 | "Less is more" — where it holds and where it breaks |
| The Raw Capability List | 19 | 6 fundamental capabilities stripped to the minimum |
| Why Structured Tools Still Matter | 36 | Accuracy multipliers vs. raw capability |
| The Practical Working Set | 50 | 4 layers: core tools → force multipliers → capability unlocks → aspirational |
| Where "Just Give It a Terminal" Fails | 96 | The 5 hard walls — interactive processes, GUIs, real-time state, auth, parsing |
| The Bottom Line | 108 | 8-10 tools, not hundreds |

### Part 2: Memory
| Section | Line | Topic |
|---------|------|-------|
| Memory With Teeth | 124 | 6 levels from auto-injection to behavioral verification |

### Part 3: Daemon
| Section | Line | Topic |
|---------|------|-------|
| Persistent Daemon Mode | 216 | Why request-response isn't enough |
| Stateful Agent Daemon | 324 | Full deep-dive: 5 components, architecture, authority tiers, audit log |

### Part 4: Remaining Components
| Section | Line | Topic |
|---------|------|-------|
| Interactive PTY | 519 | Back-and-forth with running processes |
| Audio/Video I/O | 596 | Ears, voice, eyes, face |
| Sandboxed Execution | 691 | Instant cloning, parallel experiments, graduated promotion |
| Credential Management | 806 | Encrypted vault, scoped access, rotation, audit |

### Part 5: Multi-Agent and Final Assessment
| Section | Line | Topic |
|---------|------|-------|
| Now We're at 100% (single agent) | 937 | 9-component summary |
| Multi-Agent Orchestration | 980 | Supervisor, workers, shared context, conflict resolution, adaptive planning |
| Now We're Actually at 100% | 1200 | Full 10-component summary |
| Component Status Table | 1223 | All 10 components: what we have vs. what's missing |

---

## Component Deep-Dives

Each document covers: definition, purpose, current status, key insight, what exists today, comparison tables, hard problems, what would need to be built, and what it covers.

| # | Document | Component | Status |
|---|----------|-----------|--------|
| 01 | [Terminal + Structured Tools](components/01-terminal-and-structured-tools.md) | Core file ops, shell execution, accuracy multipliers | **HAVE** |
| 02 | [Web Browser](components/02-web-browser.md) | Semantic browsing + programmatic automation, two levels | **PARTIAL** |
| 03 | [Desktop Vision + Control](components/03-desktop-vision-and-control.md) | Pixel-based + accessibility-based, two approaches | **DON'T HAVE** |
| 04 | [Memory With Teeth](components/04-memory-with-teeth.md) | 6 levels from auto-injection to behavioral verification | **PRIMITIVE** |
| 05 | [Stateful Agent Daemon](components/05-stateful-agent-daemon.md) | 5 components: event bus, triage, state, authority tiers, audit | **DON'T HAVE** |
| 06 | [Interactive PTY](components/06-interactive-pty.md) | Conversational execution, REPLs, debuggers, SSH | **DON'T HAVE** |
| 07 | [Audio/Video I/O](components/07-audio-video-io.md) | 4 channels: audio in/out, video in/out | **DON'T HAVE** |
| 08 | [Sandboxed Execution](components/08-sandboxed-execution.md) | Instant cloning, concurrent sandboxes, graduated promotion | **PRIMITIVE** |
| 09 | [Credential Management](components/09-credential-management.md) | Encrypted vault, scoped access, rotation, output scanning | **PRIMITIVE** |
| 10 | [Multi-Agent Orchestration](components/10-multi-agent-orchestration.md) | Supervisor, workers, shared context, conflict resolution | **PRIMITIVE** |

---

## Analysis and Planning Documents

| # | Document | What It Covers |
|---|----------|---------------|
| 11 | [Implementation Roadmap](components/11-implementation-roadmap.md) | Dependency graph, impact vs. effort matrix, 6 build phases (30 weeks), critical path, quick wins |
| 12 | [Agent Framework Scorecard](components/12-agent-framework-scorecard.md) | 17 autonomous AI agents scored on all 10 components — rankings, per-tool analysis, market gaps, best-in-class picks, component ecosystem |
| 13 | [Deep Spec — Memory With Teeth](components/13-deep-spec-highest-impact-component.md) | Full technical spec: architecture, data models, API, tech stack, 7 phases (37 days), testing, risks |
| 14 | [Personal Agent Stack](components/14-personal-agent-stack.md) | Current setup assessment, per-component scoring, gap analysis, quick wins, priority ranking |
| 15 | [Agentic AI Wishlist](components/15-agentic-ai-wishlist.md) | 15 cross-cutting capabilities beyond the 10 components — cost, context management, failure recovery, portability |
