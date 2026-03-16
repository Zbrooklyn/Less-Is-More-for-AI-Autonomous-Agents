# Multi-Agent Orchestration

## Definition

A coordination layer that enables multiple AI agents to work together as a team — with a supervisor that plans and delegates, specialized workers that execute subtasks in parallel, a shared context store for common knowledge, structured communication protocols, conflict resolution mechanisms, and adaptive replanning when things change. Not a pipeline that passes data between scripts. A team with roles, shared understanding, and the ability to adapt.

## Purpose

A single agent with all nine other components can do anything one person can do at a computer. But complex real-world tasks — building a full feature, refactoring a large codebase, managing a deployment — benefit from (or require) multiple agents working in parallel. One handles the frontend while another handles the backend. A security reviewer checks the code writer's work. A supervisor coordinates, resolves conflicts, and adapts the plan when reality doesn't match expectations.

Multi-agent orchestration is what takes the system from "one agent doing one task" to "a team of agents autonomously building complex systems." It's the difference between a solo contractor and a coordinated crew.

## Status: PRIMITIVE

Sub-agents exist via the Task tool (ephemeral, no persistent identity, no awareness of each other). CrewAI, AutoGen, and LangGraph exist externally as multi-agent frameworks with scripted coordination. No system combines intelligent planning, dynamic reassignment, shared context, conflict resolution, and adaptive replanning into a true team-like structure.

## Key Insight

The closest analogy is a **film production crew**, not an assembly line. An assembly line is rigid — Station A → Station B → Station C, and if Station B breaks, everything stops. A film crew has a director (supervisor) with a vision, and specialists (cinematographer, actors, editor) who work semi-independently toward that vision, communicate constantly, and adapt when something unexpected happens. Multi-agent orchestration needs to mirror the film crew, not the assembly line.

---

## What Exists Today

**Sub-agents within a single session.** The agent can spawn sub-agents using the Task tool. They run in parallel, do their work, and report back. But they're disposable — they have no identity, no persistent state, no awareness of each other. The parent is the only coordinator, and it's doing it manually in its head. If three research agents are spawned, they might all search for the same thing because none of them know the others exist.

**Framework-level multi-agent (CrewAI, AutoGen, LangGraph).** These let you define "agents" with roles — researcher, coder, reviewer — and chain them together. But the coordination is scripted, not reasoned. You hardcode "Agent A passes output to Agent B who passes to Agent C." If something unexpected happens at step B, there's no supervisor that can reroute, reassign, or adapt the plan. It's a pipeline pretending to be a team.

**Microservices architecture.** The non-AI world solved this decades ago — independent services communicating through APIs, message queues, and service meshes. But microservices are deterministic. Service A always does the same thing with the same input. AI agents are non-deterministic. Agent A might interpret the task differently each time, produce conflicting results, or go down a rabbit hole. The coordination problem is fundamentally harder.

**Human teams with AI assistants.** The current reality. Each developer has their own AI (Copilot, Claude, Cursor). The humans coordinate with each other. The AIs don't know the other AIs exist. The human is the orchestration layer — reading one AI's output and pasting relevant parts into another AI's context.

## Why None of These Are Enough

| Feature | Sub-agents | CrewAI/AutoGen | Microservices | Human + AI Assistants |
|---------|-----------|----------------|---------------|----------------------|
| Agents aware of each other | No | Partially | Yes (via APIs) | No |
| Dynamic task reassignment | No | No | No | Yes (human decides) |
| Shared context | No | Partially | No (isolated by design) | Yes (human transfers) |
| Conflict resolution | No | No | No (avoided by design) | Yes (human resolves) |
| Adaptive planning | No | No | No | Yes (human replans) |
| Scales beyond one machine | No | Partially | Yes | Yes |
| Works without human in the loop | Yes | Yes | Yes | No |

The gap is clear: sub-agents and frameworks can work without humans but can't coordinate intelligently. Humans coordinate intelligently but are the bottleneck. No current system does both.

## What a True Multi-Agent System Actually Is

It's not a pipeline. It's not a script that passes data between agents. It's **a team with roles, shared understanding, conflict resolution, and adaptive planning** — the same things that make human teams work, implemented for AI.

The closest analogy: a **film production crew**, not an assembly line.

An assembly line is: raw material → Station A → Station B → Station C → product. If Station B breaks, everything stops.

A film crew is: the director has a vision, the cinematographer and actors and editor all work semi-independently toward that vision, they communicate constantly, and when something unexpected happens (weather, an actor's improvisation, a location falling through), the team adapts without starting over.

## The Six Components

### 1. The Supervisor Agent (the director)

One agent that holds the full picture. It doesn't do the work — it plans, delegates, monitors, and adapts.

**What the supervisor does:**
- Receives the high-level task ("Build a user authentication system")
- Decomposes it into subtasks ("Design the database schema", "Write the API endpoints", "Build the login UI", "Write tests", "Set up password hashing")
- Assigns subtasks to appropriate worker agents based on their specialization
- Monitors progress and intervenes when something goes wrong
- Resolves conflicts between workers
- Adapts the plan when new information surfaces
- Assembles the final result from all workers' outputs

**What the supervisor does NOT do:**
- Write code itself (that's for workers)
- Make every micro-decision (workers have autonomy within their scope)
- Exist as a single point of failure (if the supervisor dies, workers can checkpoint and resume when a new supervisor spins up)

The supervisor is a lighter-weight model — it doesn't need to be the most capable coder. It needs to be a good planner, delegator, and conflict resolver.

### 2. Worker Agents (the specialists)

Agents that do the actual work. Each worker has:

- **A role/specialization** — "frontend developer", "database architect", "security reviewer", "test writer"
- **A scoped context** — only the information relevant to their task, not the entire project
- **Autonomy within bounds** — they make decisions within their domain without asking the supervisor for every line of code
- **A checkpoint/report protocol** — at defined intervals or milestones, they report progress, flag blockers, and share artifacts

Workers can be:
- **Homogeneous** — same model, same tools, different tasks (a team of generalists)
- **Heterogeneous** — different models for different jobs (Opus for architecture decisions, Sonnet for routine coding, Haiku for formatting and linting)
- **Ephemeral** — spun up for a task, destroyed when done
- **Persistent** — long-lived specialists that accumulate domain knowledge (connects back to memory with teeth)

### 3. Shared Context Store (the team wiki)

Workers need to share information without dumping their entire context into each other:

**What it stores:**
- **Architecture decisions** — "We're using PostgreSQL, not MongoDB. Here's why." Every agent sees this.
- **Interface contracts** — "The auth API returns `{token, expires_at, user_id}`. The frontend expects this shape." Workers on both sides reference this instead of guessing.
- **In-progress state** — "The database schema is done. The API is 60% complete. Tests haven't started." Any agent can check overall progress.
- **Discovered constraints** — "The hosting provider doesn't support WebSockets. Switched to SSE." One agent discovers this, all agents know it immediately.
- **Conflict flags** — "Worker A and Worker B both want to modify `auth.py`. Needs resolution."

**What it does NOT store:**
- Every line of every agent's reasoning (too noisy)
- Raw conversation history between supervisor and workers (irrelevant to other workers)
- Temporary scratch work (stays local to the worker)

The context store is structured and searchable — not a chat log, but a knowledge base that grows as the project progresses.

### 4. Conflict Resolution Protocol (the merge strategy)

When multiple agents work on the same codebase, conflicts are inevitable:

**File-level conflicts:**
- Worker A edits `auth.py` line 42 while Worker B edits `auth.py` line 87
- If the edits are independent → auto-merge (same as git)
- If the edits interact → escalate to supervisor, who decides which approach wins or asks one worker to adapt

**Design-level conflicts:**
- Worker A designs the API to return user objects. Worker B's frontend expects only user IDs.
- The supervisor detects the mismatch through interface contracts in the shared context store
- Resolution: supervisor calls both workers into a "meeting" — shares both perspectives, asks for a unified approach, updates the contract

**Resource conflicts:**
- Two workers both need to run the test suite simultaneously
- The orchestrator queues them, or spins up sandboxes so both can run independently

**Priority conflicts:**
- A security reviewer flags a critical vulnerability while the feature developer is mid-implementation
- The supervisor pauses feature work, redirects the developer to fix the vulnerability first

The key insight: **conflict resolution in multi-agent systems mirrors conflict resolution in human teams.** The same patterns work — shared standards, clear ownership, escalation paths, and a decision-maker with full context.

### 5. Communication Protocol (the shared language)

Agents need a structured way to talk to each other. Not free-form text — structured messages with defined types:

**Message types:**
```
TASK_ASSIGN:     Supervisor → Worker    "Do this specific thing"
PROGRESS:        Worker → Supervisor    "Here's where I am"
BLOCKER:         Worker → Supervisor    "I'm stuck on this"
ARTIFACT:        Worker → Context Store "I produced this output"
QUERY:           Worker → Context Store "What do I need to know about X?"
CONFLICT:        System → Supervisor    "Two workers are colliding"
REVIEW_REQUEST:  Worker → Reviewer      "Check my work"
REVIEW_RESULT:   Reviewer → Worker      "Approved / Changes needed"
REPLAN:          Supervisor → All       "Plan changed, here's the new state"
CHECKPOINT:      Worker → System        "Save my state, I can resume from here"
```

**Why structured, not free-form:**
- Parseable by the system without AI interpretation
- Routable — the system knows which messages go where without the supervisor manually forwarding everything
- Auditable — every interaction is logged in a standard format
- Filterable — workers only see messages relevant to them

### 6. Adaptive Planning Engine (the ability to replan)

No plan survives contact with reality. The orchestration system needs to handle:

**Scope changes:**
- Mid-project, the user says "Actually, add OAuth support too"
- The supervisor decomposes the new requirement, assigns it, and adjusts the timeline for dependent tasks

**Failed subtasks:**
- Worker A can't get the database migration to work after 3 attempts
- The supervisor reassigns to Worker B (different approach), or decomposes the task differently, or escalates to the user

**Discovered complexity:**
- Worker A reports "This is way more complex than estimated, it touches 15 files instead of 3"
- The supervisor splits the task into smaller subtasks, possibly assigns helpers

**Worker failure:**
- An agent crashes, times out, or produces garbage
- The system detects the failure, recovers from the last checkpoint, and either retries or reassigns

**Opportunity discovery:**
- Worker A notices "While I was working on auth, I found a performance bug in the query layer"
- The supervisor decides: fix it now (if quick), log it for later (if complex), or spawn a new worker for it

## The Hard Problems

**1. Task decomposition quality.** If the supervisor breaks a task down poorly — wrong boundaries, missing dependencies, unclear scope — every worker suffers. Bad decomposition is the #1 cause of failure in human teams too. The supervisor needs to be genuinely good at planning, not just good at delegating.

**2. Context window economics.** Each agent has a limited context window. The more agents you run, the more total context you're consuming — and paying for. A 10-agent team running for an hour with Opus-class models gets expensive fast. Smart context management (giving each agent only what it needs) is both a performance and cost problem.

**3. Coherence.** Ten agents working independently will produce ten slightly different coding styles, naming conventions, and architectural assumptions — unless the shared context store actively enforces consistency. Without active coherence management, the assembled result feels like it was written by ten different people (because it was).

**4. Diminishing returns.** More agents doesn't always mean faster results. Communication overhead grows with team size (just like human teams). Two agents might be 1.8x as productive as one. Five agents might be 3x. Ten agents might be 3.5x. The coordination cost eventually outweighs the parallelism benefit. The system needs to know when to stop adding agents.

**5. Observability.** With one agent, you can read its reasoning. With ten agents running in parallel, the amount of output is overwhelming. The user needs a dashboard-level view ("3 of 5 subtasks complete, one blocked, one in review") without having to read every agent's full transcript. This is a UX problem as much as a technical one.

**6. Trust and verification.** How do you know the final result is correct when no single agent saw the whole picture? The supervisor saw the plan but not the code. The workers saw their code but not the whole system. You need either a dedicated verification agent that checks everything end-to-end, or a systematic testing pipeline that validates the assembled result. Probably both.

## The Difference

| | Single Agent | Multi-Agent Orchestration |
|---|-------------|--------------------------|
| Complex tasks | Sequential, one thing at a time | Parallel, multiple subtasks simultaneously |
| Specialization | One generalist does everything | Specialists handle their domain |
| Failure handling | Agent gets stuck, everything stops | Reassign, retry, or escalate — work continues |
| Quality assurance | Self-review only | Dedicated reviewers check others' work |
| Task scale | Limited by one context window | Scales across many context windows |
| Coherence | Inherently consistent (one author) | Requires active coherence management |
| Cost | Predictable | Higher total, but faster time-to-completion |
| Coordination overhead | Zero | Significant — the key tradeoff |

## When to Use Multi-Agent vs. Single Agent

Multi-agent is NOT always better. Use it when:

- **The task is naturally decomposable** — clear subtasks with defined boundaries
- **Subtasks can run in parallel** — dependencies don't force sequential execution
- **Different subtasks benefit from different specializations** — security review vs. UI development vs. database design
- **The task is large enough** that sequential execution would take unacceptably long
- **Quality requires independent review** — the person who wrote it shouldn't be the only one checking it

Use a single agent when:

- **The task is small and focused** — one file, one function, one bug
- **Deep context is more important than breadth** — understanding a complex system requires holding the full picture in one mind
- **Coordination cost would exceed the benefit** — if explaining the task to 5 agents takes longer than one agent just doing it
- **Consistency matters more than speed** — one voice, one style, one architectural vision

## What Would Need to Be Built

1. **A supervisor runtime** — the execution environment for the planning/coordination agent, with tools for decomposition, assignment, monitoring, and replanning
2. **A worker pool manager** — spawns, tracks, checkpoints, and destroys worker agents. Handles scaling, timeouts, and failure recovery
3. **A shared context store** — structured, searchable knowledge base that agents read and write to. Enforces consistency and detects conflicts
4. **A message bus** — routes structured messages between agents, supervisor, and context store. Handles ordering, deduplication, and priority
5. **A conflict resolver** — detects file-level and design-level conflicts, escalates to supervisor, applies resolutions
6. **A coherence checker** — scans assembled outputs for style inconsistencies, naming mismatches, and architectural drift
7. **An observability dashboard** — shows team status, progress, blockers, and key decisions at a glance
8. **A cost controller** — monitors token usage across all agents, enforces budgets, suggests agent count optimization

## What It Covers

- Parallel execution of independent subtasks across multiple agents
- Specialized agent roles (frontend dev, backend dev, security reviewer, test writer, architect)
- Intelligent task decomposition and assignment
- Shared knowledge that grows as the project progresses
- Conflict detection and resolution at file and design levels
- Dynamic replanning when tasks fail, scope changes, or complexity is discovered
- Quality assurance through dedicated reviewer agents
- Cost-aware scaling — knowing when more agents help vs. when coordination overhead outweighs the benefit
