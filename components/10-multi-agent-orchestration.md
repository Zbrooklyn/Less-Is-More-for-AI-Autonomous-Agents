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

## The Six Components

1. **Supervisor agent** — holds the full picture, decomposes tasks, assigns to workers, monitors progress, resolves conflicts, adapts plans. Doesn't write code — plans and coordinates
2. **Worker agents** — specialists with defined roles, scoped context, autonomy within bounds, and checkpoint/report protocols. Can be homogeneous or heterogeneous, ephemeral or persistent
3. **Shared context store** — structured, searchable knowledge base containing architecture decisions, interface contracts, progress state, discovered constraints, and conflict flags
4. **Conflict resolution protocol** — handles file-level conflicts (auto-merge or escalate), design-level conflicts (supervisor mediates), resource conflicts (queue or sandbox), and priority conflicts (supervisor redirects)
5. **Communication protocol** — structured message types (TASK_ASSIGN, PROGRESS, BLOCKER, ARTIFACT, QUERY, CONFLICT, REVIEW_REQUEST, REVIEW_RESULT, REPLAN, CHECKPOINT) that are parseable, routable, auditable, and filterable
6. **Adaptive planning engine** — handles scope changes, failed subtasks, discovered complexity, worker failures, and opportunity discovery without starting over

## When to Use vs. Single Agent

**Use multi-agent when:**
- The task is naturally decomposable with clear subtask boundaries
- Subtasks can run in parallel
- Different subtasks benefit from different specializations
- The task is large enough that sequential execution is unacceptably slow
- Quality requires independent review

**Use a single agent when:**
- The task is small and focused
- Deep context matters more than breadth
- Coordination cost would exceed the benefit
- Consistency matters more than speed

## What It Covers

- Parallel execution of independent subtasks across multiple agents
- Specialized agent roles (frontend dev, backend dev, security reviewer, test writer, architect)
- Intelligent task decomposition and assignment
- Shared knowledge that grows as the project progresses
- Conflict detection and resolution at file and design levels
- Dynamic replanning when tasks fail, scope changes, or complexity is discovered
- Quality assurance through dedicated reviewer agents
- Cost-aware scaling — knowing when more agents help vs. when coordination overhead outweighs the benefit
