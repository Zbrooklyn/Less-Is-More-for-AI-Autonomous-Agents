# Glossary

Terms defined or coined in the Less Is More framework, in alphabetical order.

---

**Accuracy multiplier** — A tool that doesn't add new capability but reduces the error rate on common operations.

**Agent, code-first** — An autonomous AI agent whose primary entry point is writing, editing, and reasoning about code — but whose architecture (the 10 components) is universal. As a code-first agent adds memory, a daemon, browser, and audio, it naturally grows beyond coding because the components are inherently general. Examples: Claude Code, Devin, Cursor, Codex CLI.

**Agent, general-purpose** — An autonomous AI agent whose primary focus is personal automation, messaging, or life orchestration rather than coding specifically. Scored against the same 10-component framework as code-first agents because the architecture is universal. Often has stronger implementations of memory, daemon, and desktop control. Examples: OpenClaw, NanoClaw, Letta. Example: the Edit tool prevents wrong-location edits that raw `sed` would cause. The operation is possible without it; it's just less reliable.

**Adaptive planning engine** — The component of multi-agent orchestration that handles replanning when reality doesn't match the original plan — scope changes, failed subtasks, discovered complexity, worker failures.

**Agent loop** — A process that receives an event, reasons about it, decides what to do, acts, and goes back to waiting. Distinguished from a script (runs once and exits) by staying alive and maintaining state between activations.

**Authority boundaries** — Hardcoded rules defining what an autonomous agent is allowed to do without human approval. Organized into tiers from fully autonomous (run tests, clean up artifacts) to alert-only (production deployments, security changes).

**Authority tiers** — The four levels of autonomous action: Tier 1 (autonomous — just do it, log it), Tier 2 (act then notify), Tier 3 (propose and wait for approval), Tier 4 (alert only — never act, always escalate).

**Behavioral verification** — A post-response check that verifies the AI actually followed its own learned rules. The sixth level of memory with teeth. Currently doesn't exist — compliance is honor-based.

**Capability unlock** — A tool that enables something fundamentally impossible without it.

**Claw** — Andrej Karpathy's term for the next stage of AI agent evolution. The progression is "Chat → Code → Claw." The 10-component framework shows why this progression is natural — a code-first agent that adds memory, a daemon, browser, and audio doesn't become a different thing, it becomes a more complete version of the same thing. The components are universal. Examples: OpenClaw (68K stars), NanoClaw (security-first alternative), ZeroClaw (Rust, minimal footprint).

**Component ecosystem** — The layer of specialized tools, frameworks, and infrastructure beneath complete agents — each with a best-in-class implementation of a single component from the 10-component framework. Not competitors to complete agents, but building blocks any agent could integrate. Examples: Mastra OM and Mem0 (memory), E2B (sandbox), LiveKit (audio/video), Composio (credentials), Browser-Use (browser).

**Compression-proof persistence** — Memory that survives context window compression during long sessions. Critical rules pinned outside the conversation context so they remain at full fidelity regardless of session length. The fifth level of memory with teeth.

**Computer use** — Anthropic's term for desktop vision + control — the ability to take screenshots, see the screen, and interact via mouse/keyboard. Exists as a separate product, not integrated into agent tooling.

**Conflict resolution protocol** — The multi-agent orchestration mechanism for handling collisions — file-level (two agents edit the same file), design-level (incompatible approaches), resource-level (competing for shared resources), priority-level (urgent work preempting planned work).

**Context store** — See "shared context store."

**Credential broker** — A system component that sits between the AI agent and external services, handling authentication injection, token refresh, and scope enforcement. The agent says "push to GitHub" and the broker transparently handles auth.

**Daemon** — A background process that stays alive and reacts to events. In the framework, a "stateful agent daemon" is an always-on AI agent process with persistent state, event-driven activation, authority boundaries, and full audit logging.

**Enforcement hooks** — Rules that intercept and block known-bad actions before they execute, rather than merely suggesting the agent should avoid them. The second level of memory with teeth. Primitive version exists in Claude Code hooks.

**Escape hatch** — The terminal/Bash tool, used for anything that specialized tools don't cover. Provides universal capability at the cost of reduced reliability.

**Event bus** — A unified queue that ingests events from multiple sources (file watchers, webhooks, log monitors, system metrics, timers, manual triggers) and feeds them to the triage layer. The "ears" of the daemon.

**Event-driven agent loop** — The full phrase for what a stateful agent daemon is: an event-driven process with persistent state and authority boundaries.

**Force multiplier** — A tool that dramatically increases the agent's effectiveness without being strictly necessary. Sub-agents (parallel work) and web search (access to current information) are force multipliers — you can work without them, but you're 3x slower.

**Graduated promotion** — The sandboxed execution pattern where changes move through stages (sandbox → verified → local dev → tested → staging → production) with checks at each stage, rather than jumping directly from experiment to reality.

**Honey pot** — What you accidentally build when an always-running daemon with access to GitHub, AWS, Slack, and databases stores its credentials in plaintext `.env` files.

**Interactive PTY** — A pseudo-terminal that lets the AI have back-and-forth conversation with a running process — sending input, reading output in real-time, and responding to prompts. Distinguished from one-shot command execution where the entire command is provided upfront and all output is received at the end.

**Memory with teeth** — A persistent memory system that loads itself (automatic injection), enforces itself (enforcement hooks), searches by meaning (semantic retrieval), captures corrections automatically, survives context compression, and verifies compliance. Distinguished from current "post-it note" memory that depends on the AI remembering to check it.

**MCP (Model Context Protocol)** — A protocol for connecting AI agents to external tools and services. Used in the framework to reference MCP browser tools and MCP service connectors (Slack, GitHub, etc.).

**Multi-agent orchestration** — A coordination layer enabling multiple AI agents to work as a team — with a supervisor, specialized workers, shared context, structured communication, conflict resolution, and adaptive replanning.

**One-shot execution** — The current model of terminal interaction: send a complete command, wait for it to finish, receive all output at once. No ability to interact with the process while it's running. Contrasted with interactive PTY.

**Output scanner** — A system that monitors all AI output channels (terminal, files, logs, conversation) for accidentally exposed credentials. A reverse firewall — blocking outgoing secrets rather than incoming threats.

**Parallel experimentation** — The sandboxed execution capability of running multiple approaches simultaneously in concurrent sandboxes, comparing results, and applying the winner. Something humans cannot do efficiently but AI agents with sandboxes can.

**Persistent state store** — The "notebook" of the daemon — tracks in-progress tasks, recent actions, pending approvals, known context, and pattern history between activations. What separates a stateful daemon from a stateless cron job.

**PTY (Pseudo-Terminal)** — A virtual terminal that lets a program think it's talking to a human at a keyboard. The underlying technology that would enable interactive process interaction for AI agents.

**Request-response** — The current model of AI agent interaction: user sends a message, agent thinks and responds, agent stops. No persistence between conversations. Contrasted with daemon mode.

**Sandbox** — An isolated copy of the environment where the agent can experiment, test, and break things without affecting the real system. Disposable, instant to create, and resource-limited.

**Scoped access** — The principle of least privilege applied to AI agent credentials — each task gets only the credentials it needs, limiting blast radius if something goes wrong.

**Semantic retrieval** — Searching memory by meaning rather than file location. Instead of "open corrections-log.md and search for pywebview," the agent queries "what do I know about pywebview?" and gets relevant results ranked by relevance and recency. The third level of memory with teeth.

**Shared context store** — The multi-agent "team wiki" — a structured, searchable knowledge base containing architecture decisions, interface contracts, progress state, discovered constraints, and conflict flags. All agents read from and write to it.

**Structured tools** — Purpose-built tools (Read, Write, Edit, Grep, Glob) that wrap common terminal operations with safety checks, structured output, and context efficiency. Accuracy multipliers, not capability additions.

**Supervisor agent** — The coordinating agent in multi-agent orchestration that holds the full picture, decomposes tasks, assigns to workers, monitors progress, resolves conflicts, and adapts plans. Doesn't do the work — plans and coordinates.

**Triage layer** — A lightweight filter between the event bus and the AI agent that decides what's worth waking the full agent for. Uses rule-based filters, small model classification, batching, priority assignment, and deduplication. The key cost control for daemon mode.

**Worker agent** — An agent in multi-agent orchestration that does actual work. Has a role/specialization, scoped context, autonomy within bounds, and a checkpoint/report protocol. Can be homogeneous or heterogeneous, ephemeral or persistent.
