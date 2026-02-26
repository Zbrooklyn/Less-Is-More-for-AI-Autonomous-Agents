# Stateful Agent Daemon

## Definition

An always-on, event-driven agent process that stays alive between conversations, watches for events (file changes, CI failures, system alerts, scheduled checks), reasons about what to do, acts within defined authority boundaries, and logs everything. Not a cron job. Not a hook. An event-driven agent loop with persistent state and authority boundaries.

## Purpose

Current AI agents are request-response machines — they exist only while the user is looking at them and vanish the moment the conversation closes. They can't notice that a build broke at 3 AM, that disk space is running low, that a dependency got a CVE, or that a branch has drifted dangerously far from main.

A stateful agent daemon transforms the agent from a consultant you call when you have a problem into an employee who's always at their desk — watching, maintaining, preventing issues before they become emergencies.

## Status: DON'T HAVE

Claude Code hooks exist as primitive triggers during active sessions. Cron jobs exist at the OS level. Background task execution exists. But there is no event bus, no persistent state store between activations, no authority tier system, no triage layer, no audit logging, and no always-on presence. The agent dies when the conversation closes.

## Key Insight

The difference between a cron job and a stateful agent daemon is **state + reasoning + boundaries**. A cron job is an alarm clock — it wakes you up but doesn't know why, doesn't remember yesterday, and can't decide whether today is worth getting up for. A daemon is a night shift employee — watching the monitors, knowing the history, following the runbook, and only calling you when something exceeds their authority.

---

## The One-Phrase Definition

**An event-driven agent loop with persistent state and authority boundaries.**

Breaking it down:

- **Event-driven** — not just timers (cron), but file changes, webhooks, log patterns, system metrics. Anything that can trigger a reaction.
- **Agent loop** — not a script that runs and exits. A process that receives an event, reasons about it, decides what to do, acts, and then goes back to waiting. The "loop" part is key — it stays alive.
- **Persistent state** — it remembers what it did last time, what's in progress, what it's waiting on. This is what separates it from a cron job. A cron job wakes up with amnesia every time. A daemon wakes up knowing the full situation.
- **Authority boundaries** — hardcoded rules about what it can do autonomously vs. what requires human approval. Without this, it's either useless (can't do anything) or dangerous (can do everything).

## What Exists Today

**Cron jobs.** A timer fires, a script runs, it exits. No memory of last run. No awareness of context. No decision-making. It's a metronome — perfectly rhythmic, completely brainless.

**Hooks.** A trigger fires before or after a specific action. Claude Code hooks run shell commands when the agent uses a tool. They're reactive, but they only exist during an active session. Close the conversation, hooks die too. And they're pattern-matchers — they don't reason, they just check "did this command match a rule?"

**GitHub Actions / CI.** Event-driven scripts. A push triggers a workflow, a PR triggers checks. Closer to what we want — they respond to real events, not just timers. But they run predefined scripts. There's no reasoning, no context about what happened yesterday, no ability to say "this failure looks like the same one from last week, and that fix worked, so I'll try it again."

**Cron + LLM API call.** The hack version. A cron job runs every 5 minutes, checks for events, and if something needs attention, it calls an LLM API with the event details. This technically works. But it has no state between calls, no coordination between overlapping events, no authority model, and no way to handle multi-step tasks that span multiple wake-ups.

## Why None of These Are Enough

| Feature | Cron Job | Hooks | CI/CD | Cron + LLM |
|---------|----------|-------|-------|------------|
| Runs on a schedule | Yes | No | No | Yes |
| Responds to events | No | Yes (limited) | Yes | Partially |
| Reasons about what to do | No | No | No | Yes (but stateless) |
| Remembers previous runs | No | No | No | No |
| Handles multi-step tasks | No | No | Partially | No |
| Knows its authority limits | No | No | No | No |
| Survives session close | Yes | No | Yes | Yes |
| Coordinates competing events | No | No | No | No |

Every existing solution is missing at least three critical features. The closest is cron + LLM, but without state it's an amnesiac that wakes up every 5 minutes and has to figure out the world from scratch.

## What a Stateful Agent Daemon Actually Is

It's none of the above. It's a new thing. The closest analogy isn't a cron job or a hook — it's an **on-call engineer with a notebook and a runbook.**

The on-call engineer:
- Stays available (daemon process)
- Gets paged when something happens (event bus)
- Checks their notebook to understand current context (persistent state)
- Follows the runbook for what they're authorized to do (authority boundaries)
- Escalates when something exceeds their authority (human approval queue)
- Writes down what they did for the next person (audit log)
- Hands off cleanly at shift change (state continuity)

## The Five Components

### 1. Event Bus (the ears)

Not just cron timers. A unified system that ingests events from multiple sources:

- **File system watchers** — a file changed, a new file appeared, a config drifted
- **Webhooks** — GitHub push, Slack message, API callback, deployment notification
- **Log monitors** — a pattern appeared in a log file, an error rate spiked
- **System metrics** — CPU/memory/disk crossed a threshold
- **Timers** — scheduled checks (this is where cron lives, as one input among many)
- **Manual triggers** — the user says "go check on X"

All of these feed into one queue. The daemon doesn't care *how* the event arrived. It just processes events.

### 2. Triage Layer (the judgment)

Not every event deserves full AI inference. That's expensive. So a lightweight filter sits between the event bus and the AI:

- **Rule-based filters** — "ignore file changes in `node_modules/`", "always escalate production errors"
- **Small model classification** — a fast, cheap model (Haiku-class) reads the event and decides: ignore, batch, or wake the main agent
- **Batching** — 50 test files changed in 2 minutes? That's one event ("test suite updated"), not 50
- **Priority assignment** — production down = immediate. Stale branch reminder = batch for morning summary
- **Deduplication** — same error firing every 30 seconds doesn't generate 30 wake-ups

This is the key cost control. The expensive agent only wakes up when it matters.

### 3. Persistent State Store (the notebook)

This is what separates a daemon from a cron job. Between activations, the agent has a state store that tracks:

- **Current tasks in progress** — "I started a dependency update at 2:15 PM, waiting for CI to pass before merging"
- **Recent actions taken** — "I restarted the dev server 10 minutes ago because of a memory leak"
- **Pending approvals** — "I proposed a fix for issue #42, waiting for human sign-off"
- **Known context** — "The user is on vacation until Thursday, batch non-critical items"
- **Pattern history** — "This service has crashed 3 times this week, same root cause each time"

When the agent wakes up, it loads relevant state *before* it starts reasoning. It doesn't start from zero. It starts from "here's where we left off."

This connects directly to the memory with teeth problem. The state store IS the memory system, applied to daemon operations.

### 4. Authority Boundaries (the runbook)

Hardcoded rules about what the daemon can do without asking:

**Tier 1 — Autonomous (just do it, log it):**
- Run tests
- Generate reports and summaries
- Clean up build artifacts and temp files
- Restart dev services that crashed
- Update status dashboards
- Send informational notifications

**Tier 2 — Act then notify (do it, tell the human):**
- Fix lint errors and formatting
- Update minor dependency versions
- Close stale branches older than 30 days
- Auto-merge PRs that pass all checks and have approval

**Tier 3 — Propose and wait (describe the plan, wait for approval):**
- Push code to shared branches
- Modify CI/CD pipelines
- Update major dependency versions
- Respond to external communications
- Delete anything non-trivial

**Tier 4 — Alert only (never act, always escalate):**
- Production deployments
- Security-related changes
- Anything involving credentials or secrets
- Actions affecting external users
- Anything financially consequential

The user configures these tiers. The daemon enforces them. No exceptions, no "I thought it would be fine."

### 5. Audit Log (the paper trail)

Everything the daemon does gets logged with full context:

```
[2026-02-26 03:42:17] EVENT: CI pipeline failed (PR #187, commit abc123)
[2026-02-26 03:42:18] TRIAGE: Priority HIGH — production branch affected
[2026-02-26 03:42:19] STATE LOADED: PR #187 context, recent CI history
[2026-02-26 03:42:23] REASONING: Test failure in auth_test.py:42 —
    missing import after refactor in commit abc123. Same pattern as
    fix applied to PR #165 on 2026-02-19.
[2026-02-26 03:42:24] DECISION: Apply same fix (add missing import).
    Authority: Tier 2 (act then notify).
[2026-02-26 03:42:31] ACTION: Created commit def456, pushed to PR #187
[2026-02-26 03:42:32] NOTIFICATION: Sent to user — "Fixed missing import
    in auth_test.py. Same issue as PR #165. CI re-running."
[2026-02-26 03:42:45] RESULT: CI passed. PR #187 green.
```

If something goes wrong at 3 AM, the user wakes up and reads exactly what happened, why, and what the daemon was thinking. Not "something changed." The full chain.

## How It Would Work Architecturally

```
┌─────────────────────────────────────────┐
│           EVENT BUS                      │
│  (file changes, webhooks, cron,          │
│   log patterns, system metrics)          │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│           TRIAGE LAYER                   │
│  - Is this worth waking the AI for?      │
│  - Priority: critical / normal / low     │
│  - Can it be batched with other events?  │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│           AI AGENT (wakes on demand)     │
│  - Receives event + relevant context     │
│  - Decides: act, alert, or ignore        │
│  - Has authority boundaries              │
│  - Logs everything it does               │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│           ACTION BOUNDARIES              │
│  - Safe actions: execute immediately     │
│  - Risky actions: queue for approval     │
│  - Critical actions: alert + wait        │
└─────────────────────────────────────────┘
```

## The Hard Problems

**1. Cost.** You can't run full AI inference 24/7 — it's expensive. So the triage layer has to be lightweight. A small, cheap model or even rule-based filters decide what's worth waking the real agent for. Most events get ignored or batched.

**2. Authority boundaries.** This is the big one. If the agent is running autonomously, what is it *allowed* to do without asking? Fix a typo? Probably fine. Push to production? Absolutely not without approval. The boundary has to be clearly defined, and getting it wrong in either direction is bad — too restrictive and it's useless, too permissive and it's dangerous.

**3. State continuity.** If the agent wakes up to handle an event, it needs to know what happened since the last time it was active. Not the full conversation history — a compressed, relevant summary. This connects directly back to the memory with teeth problem. Without good memory, a daemon is just a reactive script that happens to use an LLM.

**4. Coordination.** What if two events arrive simultaneously that conflict? What if the agent is mid-action on one thing and something higher-priority comes in? A human developer handles this with intuition. An AI daemon needs explicit priority rules and the ability to pause/resume work.

**5. Accountability.** If the daemon takes an action at 3 AM and it breaks something, there has to be a clear log of: what event triggered it, what the agent decided, why, what it did, and what the result was. Full audit trail, not optional.

## The Difference, Summarized

| | Cron Job | Hook | Stateful Agent Daemon |
|---|---------|------|----------------------|
| When it runs | On a timer | On a specific trigger | On any event, any time |
| What it knows | Nothing | The current action | Full history and context |
| What it decides | Nothing — runs a script | Nothing — pattern matches | Reasons about what to do |
| What it remembers | Nothing | Nothing | Everything relevant |
| What it's allowed to do | Whatever the script does | Whatever the hook does | Defined by authority tiers |
| What it logs | stdout | Pass/fail | Full reasoning chain |
| When it dies | After the script exits | When the session closes | Never (until stopped) |

## What Would Need to Be Built

1. **An event ingestion layer** — unified queue that accepts file watchers, webhooks, system metrics, timers, and manual triggers
2. **A triage classifier** — lightweight model or rule engine that filters and prioritizes events
3. **A state database** — persistent store the agent reads/writes between activations (SQLite would work for local, PostgreSQL for distributed)
4. **An authority configuration format** — user-defined tiers, probably YAML or similar, that the daemon enforces
5. **An agent execution runtime** — the thing that actually wakes the AI, loads context + state, lets it reason and act, then puts it back to sleep
6. **An audit log system** — append-only log with structured entries for every decision and action
7. **A notification system** — how the daemon communicates back to the human (Slack, email, desktop notification, dashboard)

None of these are individually hard. The hard part is making them work together reliably, affordably, and safely.

## What It Would Change

The shift from request-response to daemon mode is the difference between:

- **A consultant you call when you have a problem** → an employee who's always at their desk
- **Debugging after something breaks** → preventing it from breaking
- **You managing the AI** → the AI managing itself (within boundaries)

It's the single biggest UX jump remaining in AI tooling. Everything else — better models, more tools, faster inference — is incremental. Daemon mode is a category change.

## What It Covers

- CI/CD failure detection and auto-repair
- System health monitoring and proactive intervention
- Scheduled maintenance (stale branches, outdated dependencies, disk cleanup)
- File system watching and reactive test running
- Log monitoring and anomaly detection
- Event-driven automation with intelligent triage
- Full accountability trail for every autonomous action
