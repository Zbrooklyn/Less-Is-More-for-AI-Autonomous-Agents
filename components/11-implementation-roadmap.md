# Implementation Roadmap

## Definition

A prioritized build plan for the 10 components of a fully autonomous AI agent. Maps out what to build first, what depends on what, which components unlock the most value earliest, estimated complexity for each, and the critical path from "1 out of 10 built" to "10 out of 10 built."

## Purpose

The "Less Is More" document answers **what** an AI agent needs. This document answers **in what order do you build it.** Without a roadmap, you either build the wrong thing first (wasting effort on a component that depends on something you haven't built yet) or build the easiest thing first (which may not be the most impactful).

The roadmap identifies the highest-leverage components — the ones that unlock the most capability per unit of effort — and sequences the build so that each component can lean on the ones built before it.

---

## Dependency Graph

Not all 10 components are independent. Some require others to exist first. Some enhance others but don't strictly require them.

```
Terminal + Structured Tools (1)
  ├── Web Browser (2)              [independent — can build anytime]
  ├── Desktop Vision + Control (3) [independent — can build anytime]
  ├── Interactive PTY (6)          [independent — can build anytime]
  ├── Audio/Video I/O (7)          [independent — can build anytime]
  │
  ├── Memory With Teeth (4)        [independent — but enhances everything]
  │     └── Stateful Agent Daemon (5)  [REQUIRES memory — useless without state]
  │           └── Sandboxed Execution (8) [most valuable WITH daemon]
  │
  ├── Credential Management (9)    [independent — but critical for daemon]
  │
  └── Multi-Agent Orchestration (10) [REQUIRES memory + benefits from all others]
```

### Hard Dependencies

| Component | Requires | Why |
|-----------|----------|-----|
| Stateful Agent Daemon (5) | Memory With Teeth (4) | A daemon without persistent state is just a cron job. Memory is what makes it stateful. |
| Multi-Agent Orchestration (10) | Memory With Teeth (4) | Shared context store is a form of memory. Without it, agents can't coordinate. |
| Multi-Agent Orchestration (10) | Terminal + Structured Tools (1) | Workers need tools to do actual work. Already built. |

### Soft Dependencies (enhances but doesn't require)

| Component | Enhanced By | Why |
|-----------|-----------|-----|
| Stateful Agent Daemon (5) | Credential Management (9) | Daemon needs service access at 3 AM without asking for keys. |
| Stateful Agent Daemon (5) | Sandboxed Execution (8) | Daemon should test fixes in sandbox before applying to reality. |
| Multi-Agent Orchestration (10) | Sandboxed Execution (8) | Workers should work in isolated environments to avoid conflicts. |
| Multi-Agent Orchestration (10) | Interactive PTY (6) | Workers debugging in parallel need persistent terminal sessions. |
| All components | Memory With Teeth (4) | Memory improves everything — learned patterns, error avoidance, user preferences. |

### Fully Independent (can build in any order)

- Web Browser (2)
- Desktop Vision + Control (3)
- Interactive PTY (6)
- Audio/Video I/O (7)
- Credential Management (9)

These five have no dependencies on anything except the terminal (which is already built). Build them whenever it makes sense based on impact, not sequencing.

---

## Impact vs. Effort Matrix

| # | Component | Effort | Impact | Ratio | Notes |
|---|-----------|--------|--------|-------|-------|
| 4 | Memory With Teeth | Medium | **Very High** | **Best** | Improves every session, every component, every interaction. Buildable with existing tech (embeddings, hooks, vector DB). Foundation for daemon and multi-agent. |
| 9 | Credential Management | Low | **High** | **Best** | Prevents catastrophic security failures. Uses existing OS tools (Credential Manager, keyring). Small build, high risk reduction. |
| 2 | Web Browser | Low | **High** | **Great** | MCP browser or Playwright integration. Most of the tech exists. Unlocks research, testing, web interaction. |
| 5 | Stateful Agent Daemon | High | **Very High** | **Good** | Category-changing capability. But complex — event bus, state store, authority system, audit log. Requires memory first. |
| 8 | Sandboxed Execution | Medium | **High** | **Good** | Safe experimentation. Multiplied value when combined with daemon. OS-level tech exists (containers, overlayfs). |
| 10 | Multi-Agent Orchestration | Very High | **Very High** | **Fair** | Massive impact but massive build. Supervisor, workers, shared context, conflict resolution, communication protocol. Build last. |
| 3 | Desktop Vision + Control | Medium | **Medium** | **Fair** | Opens GUI apps. Not needed for terminal-based workflows. High value for specific use cases, low value if you live in the terminal. |
| 6 | Interactive PTY | Medium | **Medium** | **Fair** | Unlocks debuggers, REPLs, SSH. Important for some workflows, rarely needed for others. |
| 7 | Audio/Video I/O | High | **Medium** | **Low** | Big build. Bandwidth, real-time constraints, hardware variability. High value for meetings/voice, but most dev work is text. |
| 1 | Terminal + Structured Tools | Done | Done | — | Already built. Nothing to do. |

---

## Build Phases

### Phase 0: Immediate Hardening (Week 1)

No new capabilities. Fix what's broken and dangerous.

| Action | Component | Effort | What It Fixes |
|--------|-----------|--------|---------------|
| Move secrets to OS credential manager | Credential (9) | 1 day | Eliminates plaintext API keys |
| Add pre-commit secret scanning | Credential (9) | 2 hours | Prevents accidental key commits |
| Add 3-5 enforcement hooks for known-bad actions | Memory (4) | 2 hours | Turns post-it notes into guardrails |
| Configure MCP browser tool | Browser (2) | 30 min | Unlocks web research from agent |

**Cost: ~2 days. Result: Security gaps closed, browser access gained, memory slightly hardened.**

### Phase 1: Memory Foundation (Weeks 2-4)

Memory is the foundation everything else builds on. Build it before anything else.

| Action | Component | Effort | What It Unlocks |
|--------|-----------|--------|----------------|
| Implement automatic context injection based on file/project being worked on | Memory (4) | 1 week | Right memory loads without manual reading |
| Build semantic retrieval over memory files (embeddings + vector store) | Memory (4) | 1 week | Query past experience by meaning |
| Add automatic correction capture (detect "no, do it this way" patterns) | Memory (4) | 3 days | Memory grows without manual logging |
| Implement compression-proof rule pinning | Memory (4) | 3 days | Rules survive long sessions |

**Cost: ~3 weeks. Result: Memory goes from PRIMITIVE to functional. Every future session is better.**

### Phase 2: Always-On Intelligence (Weeks 5-10)

With memory working, build the daemon. This is the category change.

| Action | Component | Effort | What It Unlocks |
|--------|-----------|--------|----------------|
| Build event bus (file watchers, webhooks, timers) | Daemon (5) | 1 week | Events can trigger the agent |
| Build triage layer (rule-based + small model filter) | Daemon (5) | 1 week | Cost control — only wake agent when it matters |
| Build persistent state store (SQLite) | Daemon (5) | 1 week | Daemon remembers between activations |
| Implement authority tier system | Daemon (5) | 3 days | Safe autonomous action within boundaries |
| Build audit log | Daemon (5) | 2 days | Full accountability trail |
| Integrate credential broker with daemon | Credential (9) | 3 days | Daemon can access services securely at 3 AM |

**Cost: ~5 weeks. Result: First always-on AI agent. Monitors, reacts, acts within boundaries, logs everything.**

### Phase 3: Safe Autonomy (Weeks 11-14)

The daemon is running. Make it safer with sandboxes and better browser.

| Action | Component | Effort | What It Unlocks |
|--------|-----------|--------|----------------|
| Build sandbox orchestrator (instant environment cloning) | Sandbox (8) | 2 weeks | Daemon tests fixes before applying to reality |
| Add concurrent sandbox support | Sandbox (8) | 1 week | Parallel experimentation |
| Integrate Playwright as full browser automation | Browser (2) | 1 week | Complete web interaction — testing, scraping, complex flows |

**Cost: ~4 weeks. Result: Daemon can safely experiment. Browser is fully functional.**

### Phase 4: Expanded Capabilities (Weeks 15-22)

Fill in the remaining independent components based on workflow needs.

| Action | Component | Effort | What It Unlocks |
|--------|-----------|--------|----------------|
| Build PTY multiplexer with output parsing | Interactive PTY (6) | 3 weeks | Debuggers, REPLs, SSH sessions |
| Integrate desktop vision via pyautogui + UI Automation API | Desktop (3) | 3 weeks | GUI app interaction |
| Connect audio pipeline (mic → transcription → agent) | Audio/Video (7) | 2 weeks | Voice input to agent |

**Cost: ~8 weeks. Result: Agent can debug interactively, use desktop apps, and hear you.**

### Phase 5: The Team (Weeks 23-30)

Everything else is built. Now build coordination.

| Action | Component | Effort | What It Unlocks |
|--------|-----------|--------|----------------|
| Build supervisor agent runtime | Multi-Agent (10) | 2 weeks | Task decomposition and delegation |
| Build shared context store | Multi-Agent (10) | 2 weeks | Agents share knowledge |
| Implement communication protocol and message bus | Multi-Agent (10) | 1 week | Structured agent-to-agent communication |
| Build conflict resolver | Multi-Agent (10) | 1 week | Handle agents editing same files |
| Add coherence checker and observability dashboard | Multi-Agent (10) | 2 weeks | Quality assurance and visibility |

**Cost: ~8 weeks. Result: Multiple agents working as a coordinated team.**

---

## The Critical Path

The shortest sequence from current state to maximum capability:

```
Week 1:     Phase 0 — Harden security, add hooks, configure browser
Weeks 2-4:  Phase 1 — Build memory foundation
Weeks 5-10: Phase 2 — Build stateful daemon
Weeks 11-14: Phase 3 — Add sandboxes, complete browser
Weeks 15-22: Phase 4 — PTY, desktop, audio (parallel tracks)
Weeks 23-30: Phase 5 — Multi-agent orchestration
```

**Total: ~30 weeks from start to full 10/10.**

The critical path runs through: **Memory → Daemon → Sandbox → Multi-Agent**. These must be sequential because each depends on the previous. Everything else (browser, desktop, PTY, audio, credentials) can be built in parallel whenever resources allow.

---

## Quick Wins (high impact, minimal effort)

These can be done right now, today, regardless of what phase you're in:

| Win | Effort | Impact |
|-----|--------|--------|
| Move credentials to OS keychain | 1 hour | Eliminates highest-risk security gap |
| Add MCP browser to agent config | 10 min | Instant web research capability |
| Add enforcement hooks for top 3 dangerous actions | 30 min | Turns memory rules into guardrails |
| Add CLAUDE.md rule to check error-solutions.md on errors | 5 min | Existing memory file actually gets used |
| Add pre-commit hook for secret scanning | 30 min | Prevents accidental credential commits |

**Total: ~2.5 hours for all five. Disproportionately high impact.**

---

## The Long Poles

Components that take the longest and should be started early if they're on your roadmap:

| Component | Why It's a Long Pole |
|-----------|---------------------|
| **Multi-Agent Orchestration** | Most complex build. 6 sub-components, hardest coordination problems. Depends on memory and benefits from everything else. Start last but expect it to take longest. |
| **Stateful Agent Daemon** | 5 sub-components that must work together reliably. Event handling, state management, authority enforcement, and audit logging all need to be solid before trusting it with autonomous action. |
| **Audio/Video I/O** | Real-time constraints, hardware variability, bandwidth challenges. Not technically dependent on other components but requires different infrastructure than everything else (media processing vs. text processing). |

---

## Per-Component Summary

| # | Component | Status | Complexity | Prerequisites | Build Phase | What It Unlocks |
|---|-----------|--------|-----------|---------------|-------------|-----------------|
| 1 | Terminal + structured tools | **DONE** | — | — | — | Foundation for everything |
| 2 | Web browser | Partial | Low | None | Phase 0 + 3 | Research, testing, web interaction |
| 3 | Desktop vision + control | Missing | Medium | None | Phase 4 | GUI app interaction |
| 4 | Memory with teeth | Primitive | Medium | None | Phase 1 | Better sessions, foundation for daemon + multi-agent |
| 5 | Stateful agent daemon | Missing | High | Memory (4) | Phase 2 | Always-on intelligence, proactive intervention |
| 6 | Interactive PTY | Missing | Medium | None | Phase 4 | Debuggers, REPLs, SSH |
| 7 | Audio/video I/O | Missing | High | None | Phase 4 | Voice, meetings, multimedia |
| 8 | Sandboxed execution | Primitive | Medium | None (best with daemon) | Phase 3 | Safe experimentation, parallel approaches |
| 9 | Credential management | Primitive | Low | None | Phase 0 | Secure service access, risk reduction |
| 10 | Multi-agent orchestration | Primitive | Very High | Memory (4) | Phase 5 | Agent teams, parallel complex tasks |
