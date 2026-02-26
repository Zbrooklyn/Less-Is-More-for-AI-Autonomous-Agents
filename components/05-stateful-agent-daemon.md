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

## The Five Components

1. **Event bus** — unified queue ingesting file watchers, webhooks, log monitors, system metrics, timers, and manual triggers
2. **Triage layer** — lightweight filter (rule-based or small model) that decides what's worth waking the full agent for, batches low-priority events, and deduplicates
3. **Persistent state store** — tracks in-progress tasks, recent actions, pending approvals, known context, and pattern history between activations
4. **Authority boundaries** — four tiers from autonomous (just do it) to alert-only (never act, always escalate), configured by the user and enforced by the system
5. **Audit log** — full reasoning chain for every event: what triggered it, what the agent decided, why, what it did, and what the result was

## What It Covers

- CI/CD failure detection and auto-repair
- System health monitoring and proactive intervention
- Scheduled maintenance (stale branches, outdated dependencies, disk cleanup)
- File system watching and reactive test running
- Log monitoring and anomaly detection
- Event-driven automation with intelligent triage
- Full accountability trail for every autonomous action
