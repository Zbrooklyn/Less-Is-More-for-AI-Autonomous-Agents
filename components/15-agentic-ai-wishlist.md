# Agentic AI Wishlist

## What This Is

The 10-component framework covers what an AI agent needs to be fully autonomous. This document covers what it doesn't — capabilities, behaviors, and qualities that don't fit neatly into any of the 10 components but would make a meaningful difference in real-world use. These are the things you don't realize you need until you've been using the agent for six months and hit the same friction point for the fiftieth time.

None of these are components in the structural sense. They're cross-cutting concerns, quality-of-life features, and emergent capabilities that sit on top of the 10-component foundation. Some are easy. Some are research problems. All of them would be useful.

---

## 1. Cost Awareness and Budget Management

**The problem:** AI agents have no concept of how much they cost to run. A 200-turn conversation with Opus burns through dollars without the agent knowing or caring. A daemon running overnight could rack up hundreds in API calls. Multi-agent orchestration with 8 parallel Opus agents is powerful but expensive — and the agent has no signal to trade off quality against cost.

**What it would look like:**
- The agent knows its per-token cost and tracks cumulative spend per session
- It can choose model tiers dynamically — use Opus for architecture decisions, Haiku for formatting
- The daemon's triage layer factors in cost: "Is this event worth $0.50 of inference to handle?"
- Multi-agent orchestration has a budget: "You have $10 for this task. Use it wisely."
- The user sets a ceiling: "Don't spend more than $5 on this session" — and the agent respects it
- End-of-session cost summary: "This session cost $3.42 across 47 tool calls"

**Why it's not in the 10 components:** Cost is an operational constraint, not a capability. The agent doesn't need cost awareness to be functionally complete — it needs it to be practically sustainable.

---

## 2. Self-Improving Tool Creation

**The problem:** When the agent encounters a task that its existing tools can't handle efficiently, it has no mechanism to build a new tool for itself. If it needs to parse a specific log format 20 times, it does it manually each time instead of writing a parser tool and reusing it.

**What it would look like:**
- The agent recognizes repetitive multi-step operations and proposes creating a reusable tool
- It writes the tool (a script, MCP server, or structured command), tests it, and registers it for future use
- Tools are stored in a personal toolbox that persists across sessions
- The agent can compose tools — "use the log parser I built last week, then pipe into the metrics extractor"
- Tool usage is tracked: frequently used tools get maintained, unused ones get pruned

**Why it's not in the 10 components:** The 10 components define what tools the agent needs. This is about the agent creating its own tools on top of that foundation. It's a meta-capability — tooling that makes tooling.

---

## 3. Offline and Degraded Mode

**The problem:** Current AI agents are completely dependent on API connectivity. If the API is down, rate-limited, or the internet drops, the agent is dead. There's no graceful degradation, no local fallback, no cached responses for common operations.

**What it would look like:**
- Common operations (file editing patterns, git commands, standard build steps) have cached playbooks that work without an API call
- A local small model (Llama, Phi, Gemma) handles simple tasks when the main API is unavailable
- The agent detects connectivity issues and switches to degraded mode automatically: "I've lost API access. I can still run commands, read files, and apply cached patterns, but I can't reason about complex problems until connectivity returns."
- Work done in degraded mode is queued for review when full capability returns
- Memory and enforcement still work locally — they're database-backed, not API-dependent

**Why it's not in the 10 components:** The framework assumes the agent is running. This is about what happens when it partially can't.

---

## 4. Cross-Machine Portability

**The problem:** An agent's accumulated state — memory, credentials, tool configurations, learned preferences, enforcement rules — is trapped on the machine where it was built. Move to a new laptop and you start from zero. Work from a second machine and the agent doesn't know what you did on the first.

**What it would look like:**
- The agent's entire state exports as a portable package: memory database, credential vault (encrypted), tool configs, hook definitions, pinned rules
- Import on a new machine restores the agent to full capability in minutes
- Sync between machines — work on laptop A, continue seamlessly on laptop B
- Selective sync: memory and preferences sync everywhere, credentials sync only to trusted machines, project-specific state stays with the project
- Version-controlled state: the agent's configuration and memory are in a git repo that syncs

**Why it's not in the 10 components:** The components define what the agent does. This is about making the agent's accumulated intelligence portable rather than machine-bound.

---

## 5. Context Window Management

**The problem:** The context window is the agent's working memory. When it fills up, old information gets compressed or lost. But the agent has no strategy for what to keep and what to drop. It doesn't know that line 3 of the conversation is more important than line 300. It doesn't actively prune irrelevant context. It just fills up until the system compresses it, and the system's compression is lossy and context-unaware.

**What it would look like:**
- The agent actively manages its context window like a developer manages RAM
- Relevance scoring: information is tagged with relevance to the current task, and low-relevance items are candidates for eviction
- Strategic summarization: instead of the system blindly compressing, the agent decides what to summarize vs. what to keep verbatim
- External context pointers: instead of holding a 500-line file in context, hold a pointer — "file X, lines 42-60 are relevant, re-read if needed"
- Context budget display: the agent knows how much context it has left and adjusts behavior — "I'm at 80% context, let me offload research findings to a file before continuing"
- Proactive offloading: "I've gathered enough research. Let me write a summary file and clear my context before starting implementation."

**Why it's not in the 10 components:** Memory with teeth (component 4) handles persistent storage. This is about managing the ephemeral working memory within a single session — how the agent uses the context it currently has.

---

## 6. Progress Reporting and Task Estimation

**The problem:** When the agent is working on a complex task, the user has no idea how far along it is, what it's currently doing, or how much longer it will take. For short tasks this doesn't matter. For a 30-minute multi-file refactoring, it's the difference between trusting the process and killing the session out of uncertainty.

**What it would look like:**
- Task decomposition with visible progress: "Step 3 of 7: updating test files (2 of 5 complete)"
- Confidence-based estimation: "Based on similar past tasks, this will likely take 15-25 minutes"
- Live status during long operations: "Currently running test suite... 42 of 118 tests passed so far"
- Blocker detection: "I'm stuck on this dependency issue. It's taken 3 attempts. Should I continue or try a different approach?"
- Session summary at the end: "Completed 4 of 5 planned tasks. Remaining: update documentation. Total time: 22 minutes."

**Why it's not in the 10 components:** The components define what the agent can do. This is about communicating what it's doing while it does it.

---

## 7. User Intent Disambiguation

**The problem:** Users give ambiguous instructions. "Fix the login" could mean fix a CSS bug, fix an authentication error, fix a performance issue, or redesign the entire login flow. The agent usually picks an interpretation and runs with it — sometimes for 10 minutes — before the user realizes it's doing the wrong thing.

**What it would look like:**
- Before starting ambiguous tasks, the agent identifies the ambiguity and asks exactly the right clarifying question — not a generic "can you clarify?" but "I see three potential issues with the login: the CSS is broken on mobile, the auth token expires too quickly, and the error messages are generic. Which one?"
- Confidence-based behavior: high-confidence interpretation → just do it. Medium confidence → state the interpretation and ask for confirmation. Low confidence → ask before starting.
- Pattern learning: if the user always means "fix the frontend" when they say "fix X," the agent learns this preference
- Scope negotiation: "This could be a 5-minute fix or a 2-hour refactor depending on scope. Which are you looking for?"

**Why it's not in the 10 components:** This is about the quality of the agent's reasoning and communication, not about what capabilities it has.

---

## 8. Multi-Modal Output

**The problem:** AI agents output text and code. That's it. But sometimes the right output is a diagram, a chart, a table visualization, an interactive prototype, or a screen recording of what the agent did. "Let me show you" is often better than "let me describe to you."

**What it would look like:**
- Architecture diagrams generated as SVG or Mermaid — not described in ASCII, actually rendered
- Data visualizations: "Here's the performance profile of your app" with an actual chart, not a markdown table
- Interactive prototypes: "Here's what the UI would look like" with a rendered HTML preview
- Diff visualizations: not just text diffs, but side-by-side visual comparisons of before/after
- Screen recordings: "Here's a replay of the 15 steps I took to fix this" — the agent shows its work
- Presentation generation: "Here's a 5-slide summary of what I found" — actual slides, not bullet points

**Why it's not in the 10 components:** The components define the agent's inputs and actions. This is about the richness of its outputs.

---

## 9. Dependency Graph Awareness

**The problem:** Code doesn't exist in isolation. Changing function A affects everything that calls function A. Updating a package might break 12 downstream dependencies. The agent makes changes without a map of what depends on what — it sees the file it's editing, not the system it's editing within.

**What it would look like:**
- Before making a change, the agent builds or consults a dependency graph: "Changing this function will affect 7 callers across 4 files"
- Impact analysis: "Upgrading this package will require changes in 3 projects and breaks 2 known patterns"
- Ripple detection: after making a change, automatically identify everything downstream that might need updating
- Visualization: "Here's the dependency tree for this module" — not a guess, an actual computed graph
- Cross-project awareness: "This shared library is used by WhisperClick and Mission Control. Changes here affect both."

**Why it's not in the 10 components:** The terminal and structured tools handle file operations. This is about understanding the relationships between files — the invisible structure that determines whether a change is safe.

---

## 10. Workflow Recording and Replay

**The problem:** Users do the same complex workflows repeatedly — deploy sequences, data migrations, test-fix-test cycles, release processes. Each time, they either walk the agent through it step by step or write a script manually. The agent never says "I notice you've done this three times. Want me to remember the workflow?"

**What it would look like:**
- The agent detects repeated multi-step patterns: "You've done build → test → commit → push → deploy in this order 5 times this week"
- It proposes creating a named workflow: "Should I save this as your 'release' workflow?"
- Saved workflows are parameterized: "Run the release workflow for version 2.3.1"
- Workflows adapt: if the user modifies a step, the agent asks "Should I update the workflow to include this change?"
- Connects to the daemon: "Run the release workflow every Friday at 5 PM"

**Why it's not in the 10 components:** Memory (component 4) remembers facts and rules. This is about remembering procedures — sequences of actions that form a coherent workflow.

---

## 11. Regulatory and License Awareness

**The problem:** The agent generates and copies code without awareness of licensing implications. It might suggest GPL-licensed code for an MIT project. It might store personal data in a way that violates GDPR. It might generate code that handles payment data without PCI compliance patterns. It doesn't know and can't check.

**What it would look like:**
- License scanning: before suggesting or copying code, check its license compatibility with the project
- Project license declarations: "This is an MIT project. Never suggest GPL-only dependencies."
- Compliance patterns: when working with user data, automatically apply privacy-by-design patterns (data minimization, consent tracking, deletion support)
- Regulatory context: "This project handles health data → HIPAA patterns apply" or "This serves EU users → GDPR patterns apply"
- Flagging: "This code stores email addresses without a deletion mechanism. That may be a GDPR issue."

**Why it's not in the 10 components:** The framework covers capabilities and safety. This is about legal and regulatory constraints that vary by jurisdiction, industry, and project.

---

## 12. Explainability and Teaching Mode

**The problem:** The agent does things but doesn't always explain why. For experienced developers, that's fine — just do it. For learning developers, or for unfamiliar codebases, the "why" is more valuable than the "what." The agent has no concept of the user's knowledge level or when explanation would be helpful.

**What it would look like:**
- Adaptive verbosity: detect whether the user wants "just do it" or "explain while you do it" based on their questions and responses
- Teaching mode toggle: "Explain your decisions as you go" — the agent narrates its reasoning, not just its actions
- "Why did you do that?" is always answerable — the agent can retroactively explain any decision it made
- Knowledge gap detection: "You seem unfamiliar with Python decorators. Here's a quick explanation before I use one."
- Learning paths: "You've asked about async patterns 4 times. Here's a quick overview that should cover most cases."

**Why it's not in the 10 components:** The components define what the agent can do. This is about how it communicates what it's doing and why — the pedagogical layer.

---

## 13. Graceful Failure and Recovery Patterns

**The problem:** When something goes wrong — a build fails, an API returns an error, a file can't be found — the agent's recovery is ad hoc. Sometimes it retries the same thing. Sometimes it tries a different approach. Sometimes it gives up. There's no structured failure recovery, no escalation path, and no "I've tried 3 things and none worked, here's what I know so far."

**What it would look like:**
- Structured retry logic: first attempt → different approach → simplified approach → ask for help
- Failure budgets: "I'll try 3 approaches. If none work, I'll stop and explain what I've learned."
- Diagnostic mode: on failure, automatically gather relevant context (error logs, recent changes, similar past failures) before attempting a fix
- Partial progress preservation: "I completed 4 of 6 steps before hitting this error. The first 4 are solid. Here's what failed and why."
- Escalation protocol: "I can't solve this autonomously. Here's exactly what I've tried, what I've learned, and what I think the issue is. What would you like me to try next?"

**Why it's not in the 10 components:** The components assume the agent can act. This is about what happens when its actions fail — the recovery strategy that separates a frustrating tool from a reliable one.

---

## 14. Notification Preferences and Communication Style

**The problem:** The agent communicates in one mode — text in the conversation. But different situations call for different communication: a critical production error needs an immediate push notification, a stale branch cleanup is a morning summary, a completed background task is a quiet log entry. The agent can't match its communication urgency to the situation.

**What it would look like:**
- Configurable notification channels: conversation, desktop notification, Slack message, email, dashboard update
- Priority-based routing: critical → immediate push notification. Normal → next conversation. Low → weekly digest.
- Communication style preferences: "Be terse with me. No explanations unless I ask." vs. "Walk me through everything."
- Quiet hours: "Don't notify me between 10 PM and 8 AM unless it's critical"
- Digest mode: "Summarize everything the daemon did overnight in one message when I start my day"

**Why it's not in the 10 components:** The daemon (component 5) has a notification system as a sub-component. This generalizes it beyond the daemon to all agent communication — how, when, and in what style the agent talks to the user.

---

## 15. Energy and Resource Efficiency

**The problem:** AI agents consume significant compute — CPU for local operations, bandwidth for API calls, memory for context, and electricity for all of it. On a laptop running on battery, a daemon doing inference every 5 minutes is a power drain. Multi-agent orchestration with 8 parallel agents pins the CPU. The agent has no awareness of the machine's resource state.

**What it would look like:**
- Battery awareness: "I'm on battery. Switching to low-power mode — batching events, using smaller models, reducing polling frequency."
- CPU/memory monitoring: if the agent's operations are slowing the machine, it throttles itself
- Bandwidth efficiency: compress or batch API calls when on a metered connection
- Idle detection: if the user is away, the daemon reduces activity to maintenance-only
- Resource reporting: "This session used 2.3 GB of bandwidth, 45 minutes of CPU time, and made 312 API calls"

**Why it's not in the 10 components:** The framework assumes unlimited resources. In practice, agents run on real machines with real constraints — battery life, CPU limits, bandwidth caps, and electricity costs.

---

## Summary

| # | Wishlist Item | Category | Difficulty |
|---|--------------|----------|------------|
| 1 | Cost awareness and budget management | Operational | Medium |
| 2 | Self-improving tool creation | Meta-capability | Hard |
| 3 | Offline and degraded mode | Resilience | Hard |
| 4 | Cross-machine portability | Infrastructure | Medium |
| 5 | Context window management | Performance | Hard |
| 6 | Progress reporting and task estimation | Communication | Medium |
| 7 | User intent disambiguation | Reasoning | Medium |
| 8 | Multi-modal output | Output | Medium |
| 9 | Dependency graph awareness | Analysis | Medium |
| 10 | Workflow recording and replay | Automation | Medium |
| 11 | Regulatory and license awareness | Compliance | Hard |
| 12 | Explainability and teaching mode | Communication | Medium |
| 13 | Graceful failure and recovery patterns | Resilience | Medium |
| 14 | Notification preferences and communication style | Communication | Low |
| 15 | Energy and resource efficiency | Operational | Medium |

### Why These Aren't Components

The 10 components answer **"what can the agent do?"** — they define capabilities. These 15 items answer different questions:

- **How efficiently does it do it?** (cost, resources, context management)
- **How well does it communicate?** (progress, disambiguation, explainability, notifications)
- **How does it handle failure?** (offline mode, recovery patterns)
- **How does it improve over time?** (tool creation, workflow recording)
- **What constraints does it respect?** (licenses, regulations, budgets)
- **How portable is it?** (cross-machine, degraded mode)

These are the qualities that separate a capable agent from a great one. The 10 components get you to functional. The wishlist gets you to delightful.
