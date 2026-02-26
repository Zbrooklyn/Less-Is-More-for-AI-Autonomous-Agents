# Agent Framework Scorecard

## Definition

A comparative analysis of every major AI agent tool and framework — scored against the 10-component framework defined in "Less Is More for AI Autonomous Agents." Each tool gets rated on each component (HAVE / PARTIAL / PRIMITIVE / DON'T HAVE), revealing where each tool is strong, where it's weak, and who's closest to the full 100%.

## Purpose

The AI agent space is crowded and moving fast. Claude Code, Cursor, Copilot, Devin, OpenHands, Windsurf, Aider, Continue, Cline — every tool claims to be the most capable. But without a consistent scoring framework, comparing them is just vibes and marketing.

This document applies the same 10-component lens to every major player. It answers: who's actually closest to a fully autonomous agent? Where is each tool investing? Where are the market gaps that no one is filling? And most importantly — which tool should you use for which type of work?

## Scoring Key

| Symbol | Rating | Meaning |
|--------|--------|---------|
| **HAVE** | 3 pts | Fully functional, integrated, production-ready |
| **PARTIAL** | 2 pts | Works but incomplete — missing features, requires add-ons, or limited scope |
| **PRIMITIVE** | 1 pt | Rough foundation exists — basic version, workaround, or community hack |
| **DON'T HAVE** | 0 pts | Not present in any form |

**Scoring date: February 2026.** This space moves fast. Scores reflect the state of each tool at the time of research, not their roadmap or announcements.

---

## The Master Scorecard

| # | Component | Claude Code | Cursor | Copilot | Devin | OpenHands | Windsurf | Aider | Continue | Cline | Amazon Q / Kiro | Jules | Codex CLI |
|---|-----------|-------------|--------|---------|-------|-----------|----------|-------|----------|-------|-----------------|-------|-----------|
| 1 | Terminal + structured tools | **HAVE** | **HAVE** | **HAVE** | **HAVE** | **HAVE** | **HAVE** | **HAVE** | **HAVE** | **HAVE** | **HAVE** | **HAVE** | **HAVE** |
| 2 | Web browser | PARTIAL | **HAVE** | DON'T HAVE | **HAVE** | **HAVE** | PRIMITIVE | PRIMITIVE | DON'T HAVE | **HAVE** | DON'T HAVE | DON'T HAVE | PRIMITIVE |
| 3 | Desktop vision + control | DON'T HAVE | PRIMITIVE | DON'T HAVE | PRIMITIVE | PRIMITIVE | PRIMITIVE | DON'T HAVE | DON'T HAVE | PRIMITIVE | DON'T HAVE | PRIMITIVE | PRIMITIVE |
| 4 | Memory with teeth | PARTIAL | PRIMITIVE | PRIMITIVE | PARTIAL | DON'T HAVE | PARTIAL | DON'T HAVE | PRIMITIVE | PRIMITIVE | PRIMITIVE | PRIMITIVE | PRIMITIVE |
| 5 | Stateful agent daemon | PRIMITIVE | DON'T HAVE | PARTIAL | PARTIAL | DON'T HAVE | DON'T HAVE | DON'T HAVE | PRIMITIVE | PRIMITIVE | PRIMITIVE | PARTIAL | PRIMITIVE |
| 6 | Interactive PTY | DON'T HAVE | PRIMITIVE | DON'T HAVE | PRIMITIVE | PRIMITIVE | PRIMITIVE | PRIMITIVE | DON'T HAVE | PRIMITIVE | PRIMITIVE | DON'T HAVE | PARTIAL |
| 7 | Audio/video I/O | DON'T HAVE | DON'T HAVE | DON'T HAVE | PRIMITIVE | DON'T HAVE | DON'T HAVE | PRIMITIVE | DON'T HAVE | DON'T HAVE | DON'T HAVE | PRIMITIVE | PRIMITIVE |
| 8 | Sandboxed execution | PARTIAL | PARTIAL | PARTIAL | **HAVE** | **HAVE** | PRIMITIVE | DON'T HAVE | DON'T HAVE | PRIMITIVE | PARTIAL | **HAVE** | **HAVE** |
| 9 | Credential management | PARTIAL | DON'T HAVE | PARTIAL | PRIMITIVE | PRIMITIVE | DON'T HAVE | DON'T HAVE | PRIMITIVE | PRIMITIVE | PARTIAL | PRIMITIVE | PRIMITIVE |
| 10 | Multi-agent orchestration | PARTIAL | PARTIAL | PRIMITIVE | PRIMITIVE | PARTIAL | PRIMITIVE | DON'T HAVE | PRIMITIVE | PARTIAL | PARTIAL | PRIMITIVE | PARTIAL |

---

## Total Scores

| Rank | Tool | Score | Profile |
|------|------|-------|---------|
| 1 | **Devin** | 18/30 | Most complete autonomous agent — browser, sandbox, memory, event-driven |
| 2 | **Codex CLI** | 16/30 | Strong sandbox, multi-agent, and interactive PTY — open source |
| 3 | **Claude Code** | 14/30 | Best terminal tools, strong memory and multi-agent, MCP ecosystem |
| 3 | **OpenHands** | 14/30 | Best open-source sandbox and browser, strong multi-agent architecture |
| 3 | **Cline** | 14/30 | Built-in browser, multi-agent via CLI 2.0, community-driven |
| 6 | **Cursor** | 13/30 | Best IDE experience, built-in browser, 8-agent parallelism |
| 6 | **Jules** | 13/30 | Async cloud agent, ephemeral VM sandbox, Google ecosystem |
| 8 | **Amazon Q / Kiro** | 12/30 | AWS-native, sandbox execution, CAO multi-agent framework |
| 9 | **GitHub Copilot** | 11/30 | Event-driven via GitHub, secret scanning, ephemeral environments |
| 10 | **Windsurf** | 10/30 | Auto-learning memories, new multi-agent, catching up fast |
| 11 | **Continue** | 7/30 | CI-enforceable rules are unique, but narrow scope |
| 12 | **Aider** | 6/30 | Best pure pair programmer, but minimal beyond file editing and git |

---

## Per-Tool Analysis

### Claude Code (Anthropic) — 14/30

**What it does best:** Terminal and structured tools are best-in-class. Read, Edit, Write, Grep, Glob, and Bash are native, well-designed, and integrated. The CLAUDE.md memory system auto-loads at session start and hooks provide primitive enforcement. The MCP ecosystem is the largest — browser tools, memory servers, and community integrations all available as add-ons. Sub-agents are native, Agent Teams (experimental) adds multi-agent coordination, and community orchestrators (Gas Town, Multiclaude, Claude Flow) fill gaps.

**Where it falls short:** No built-in browser — relies on MCP add-ons. No desktop vision or control despite Claude having Computer Use capability (not exposed in Claude Code). No interactive PTY (open feature request). No audio/video. Cloud sandbox exists but no local sandboxing.

**Best for:** Terminal-centric development, codebase-scale work, projects that benefit from the MCP ecosystem, teams already using Claude.

**Unique strength:** The MCP server ecosystem. No other tool has an equivalent third-party plugin architecture. If someone builds it as an MCP server, Claude Code can use it.

---

### Cursor (Anysphere) — 13/30

**What it does best:** The best IDE experience. Built-in Chromium browser for testing web apps directly in the editor. 8 parallel agents with git worktree isolation and Mission Control grid view for monitoring them. RAG indexing over the entire codebase maintains patterns across thousands of files. Visual Editor allows drag-and-drop interaction with rendered web content.

**Where it falls short:** No daemon mode — it's an IDE that runs when open. No credential management. Memory is limited to Cursor Rules (advisory, not enforced) with no cross-session semantic retrieval. No audio/video. Desktop vision limited to web content inside the editor.

**Best for:** IDE-native developers who want agent capabilities without leaving their editor. Web application development where built-in browser testing matters. Tasks that benefit from parallel agent execution.

**Unique strength:** 8-agent parallelism with visual Mission Control. No other tool offers this many concurrent agents with a visual monitoring interface.

---

### GitHub Copilot (Microsoft) — 11/30

**What it does best:** Event-driven triggering via GitHub ecosystem — assign an issue, mention @copilot, respond to a failed build. Agent HQ / Mission Control provides a dashboard for managing tasks. Copilot coding agent runs in ephemeral GitHub Actions environments with full shell access. Secret scanning is built into GitHub's infrastructure. Agentic Memory (public preview) learns from coding sessions with 28-day auto-expiry.

**Where it falls short:** No browser. No desktop vision. No interactive PTY. No audio/video. Memory has a 28-day expiry — learned preferences disappear. Multi-agent is cross-tool orchestration (SDK preview), not parallel Copilot agents working together.

**Best for:** Teams deeply embedded in the GitHub ecosystem. CI/CD-triggered autonomous coding. Enterprise environments with existing GitHub infrastructure.

**Unique strength:** The only tool natively triggered by GitHub events (issue assignment, PR comments, build failures). No other tool has this level of integration with the world's largest code hosting platform.

---

### Devin (Cognition) — 18/30

**What it does best:** The most complete autonomous agent. Built-in Chrome browser inside a full cloud sandbox. Vectorized codebase memory with full replay timeline. Event-driven triggers (build failures, Linear tickets, Slack messages). Session-scoped secrets with enterprise SSO. Internal multi-model architecture (Planner + Coder + Critic). Can process UI mockups and video recordings as input.

**Where it falls short:** Least transparent and customizable. No user-facing multi-agent API — the internal multi-model system isn't configurable. Desktop vision limited to sandbox browser, not the user's desktop. Interactive PTY not confirmed as true back-and-forth. Credential management details are sparse. It's a managed service — you can't self-host or deeply customize.

**Best for:** Fully autonomous task execution where you want to hand off a complete problem ("fix this bug", "implement this feature") and come back to a finished result. Teams that want a cloud-based coding agent without infrastructure management.

**Unique strength:** Highest overall score. The only tool that meaningfully combines browser, sandbox, memory, and event-driven execution in a single integrated product. The full replay timeline enables unique debugging and rollback capabilities.

---

### OpenHands (formerly OpenDevin) — 14/30

**What it does best:** The strongest open-source option. Every session runs in a Docker container with full OS capabilities. Built-in Playwright Chromium browser via BrowserGym. SDK supports scaling to thousands of parallel agents. AgentDelegateAction enables hierarchical agent delegation with specialist agents (CodeActAgent, BrowserAgent). Fully self-hostable.

**Where it falls short:** No persistent memory between sessions — each conversation starts from zero. No daemon mode. No credential vault. Desktop vision limited to web screenshots. Interactive PTY is command-response, not true back-and-forth.

**Best for:** Organizations that want a self-hosted, open-source agent with strong sandbox isolation. Research and experimentation. Tasks that benefit from the Docker-based execution model.

**Unique strength:** The most scalable sandbox architecture. Docker-based isolation with SDK support for thousands of concurrent agents is unmatched in the open-source space.

---

### Windsurf (Codeium) — 10/30

**What it does best:** Auto-learning memories — Windsurf autonomously analyzes the codebase over ~48 hours and learns architecture, conventions, libraries, and style. User corrections are stored and auto-injected in future sessions. Cascade's Turbo Mode enables fully autonomous multi-step editing and command execution.

**Where it falls short:** No daemon mode. No credential management. Browser limited to MCP add-ons and app previews. Multi-agent (parallel sessions with git worktrees) is very new. No sandboxing beyond git worktrees. No audio/video. No interactive PTY.

**Best for:** Developers who want an IDE that learns their style over time. Projects where consistency with existing codebase patterns matters. Teams evaluating alternatives to Cursor.

**Unique strength:** The auto-learning memory system. No other tool autonomously analyzes and learns codebase patterns over a 48-hour onboarding period without explicit configuration.

---

### Aider — 6/30

**What it does best:** The purest pair programmer. Terminal-first, focused on what it does well — reading, writing, and editing code across your repo. Automatic git commits with descriptive messages. Repo map provides intelligent codebase navigation. Supports 100+ languages. Voice coding (speak to dictate instructions). Works with any model provider (OpenAI, Anthropic, local models).

**Where it falls short:** Almost everything beyond file editing. No browser automation. No desktop control. No persistent memory. No daemon mode. No sandbox. No credential management. No multi-agent. The community fork AiderDesk addresses many gaps (vector memory, subagents, worktree isolation), but base Aider is deliberately minimal.

**Best for:** Developers who want a focused, terminal-based pair programmer without IDE lock-in. Quick code edits, refactoring, and generation across a repo. Budget-conscious users who want to choose their own model.

**Unique strength:** Model-agnostic. Aider works with more model providers than any other tool on this list. It's the universal adapter — bring any LLM, and Aider will pair-program with it.

---

### Continue — 7/30

**What it does best:** CI-enforceable AI rules. Continue's standout feature is storing coding standards as version-controlled markdown that runs as AI checks on every PR in CI. This is genuine enforcement with teeth — the rules are checked automatically, not just loaded as context. The CLI runs headlessly in CI/CD pipelines for automated code review and generation. Open source with a permissive license.

**Where it falls short:** No browser. No desktop vision. No interactive PTY. No sandbox. No audio/video. Memory is human-authored rules, not learned. Multi-agent is limited to async CLI operations. The scope is narrower than most tools on this list.

**Best for:** Teams that want AI-assisted code review enforcement in CI. Organizations that need auditable, version-controlled coding standards applied by AI. Pipeline-integrated autonomous code operations.

**Unique strength:** AI-as-CI-check. No other tool treats coding rules as version-controlled CI checks that run automatically on every PR. This is the closest any tool gets to "enforcement hooks" from the Memory With Teeth framework.

---

### Cline — 14/30

**What it does best:** Built-in Remote Browser based on Anthropic's Computer Use — navigate, click, fill forms, capture screenshots and console logs. CLI 2.0 brings full terminal operation with parallel agent instances, subagent delegation, and process isolation. The Memory Bank methodology provides structured cross-session context via project markdown files. One of the most active open-source communities.

**Where it falls short:** Memory is a methodology, not a built-in system — requires discipline to maintain. No daemon mode beyond headless CLI. Sandbox is process isolation, not container-level. Credential management is basic. Desktop vision limited to browser content.

**Best for:** Developers who want a VS Code-native agent with built-in browser automation. Teams that need visual web testing alongside code generation. Projects that benefit from the community's extensive MCP server ecosystem.

**Unique strength:** The only open-source tool with a first-party built-in browser (not via MCP or add-on). Remote Browser is native to Cline, not a plugin.

---

### Amazon Q Developer / Kiro CLI — 12/30

**What it does best:** Deepest cloud infrastructure integration. Native AWS IAM, SSO, and Identity Center support. Isolated sandbox execution environments with comprehensive logging. The CLI Agent Orchestrator (CAO) framework enables multi-agent workflows with three orchestration patterns (Handoff, Assign, Send Message). Kiro's agent hooks fire on events like file saves. Works with Amazon Q CLI, Claude Code, and other CLI tools.

**Where it falls short:** No browser. No desktop vision. No audio/video. Memory is limited to steering rules. Credential management is AWS-native — great for AWS, useless for everything else. Interactive PTY is conversational but not confirmed for debuggers/REPLs.

**Best for:** AWS-centric development teams. Infrastructure-as-code, serverless, and cloud-native workloads. Teams that want multi-agent orchestration across different CLI tools.

**Unique strength:** The CLI Agent Orchestrator. CAO is the only framework that orchestrates across different AI CLI tools (Q, Claude Code, Codex CLI) as first-class participants in a unified multi-agent system.

---

### Google Jules / Gemini Code Assist — 13/30

**What it does best:** Asynchronous cloud execution. Submit a task, leave, come back to a finished result. Every task runs in a dedicated, ephemeral cloud VM on Google Cloud — the strongest disposable sandbox model. Cross-surface context persistence (web app, CLI, Gemini CLI extension, API). Audio changelogs summarize recent commits as spoken summaries. Multiple concurrent tasks on separate VMs.

**Where it falls short:** No browser automation. No desktop control. No interactive PTY. Memory doesn't persist learned patterns across sessions. Multi-agent is concurrent tasks, not coordinated teamwork. Credential management is Google-account-only.

**Best for:** Developers who want to fire off coding tasks and come back later. Teams in the Google Cloud ecosystem. Projects where ephemeral VM isolation matters (compliance, security).

**Unique strength:** The async fire-and-forget model. Jules is the most "hand it off and walk away" agent on this list. No other tool is as cleanly designed for asynchronous, background task execution with disposable infrastructure.

---

### Codex CLI (OpenAI) — 16/30

**What it does best:** The strongest sandbox in any CLI tool — OS-enforced with macOS seatbelt, Linux Landlock or bubblewrap, configurable filesystem and network restrictions. First-party multi-agent with `spawn_agents_on_csv` for fan-out work with progress tracking. Interactive TUI with a js_repl tool for REPL interaction. Voice input via hold-spacebar transcription. Built in Rust for speed. Thread persistence allows resuming work across sessions.

**Where it falls short:** No browser automation (web search only). No desktop control beyond screenshot input. Memory is thread persistence, not learned rules or semantic retrieval. Not an always-on daemon. Credential management has no vault or rotation.

**Best for:** Developers who want a fast, sandboxed terminal agent with strong multi-agent capabilities. Bulk operations across many files or repos. Security-conscious teams that need OS-level execution isolation.

**Unique strength:** OS-enforced sandboxing. Codex CLI is the only tool using kernel-level isolation (Landlock, seatbelt, bubblewrap) rather than containers or git worktrees. This is the tightest security boundary of any local agent.

---

## Market Gap Analysis

### What every tool has

**Terminal + structured tools.** All 12 tools score HAVE. This is table stakes. The foundation is completely solved.

### What most tools have

**Web browser (7 of 12 have it at PARTIAL or above).** Cursor, Devin, OpenHands, and Cline have built-in browsers. Claude Code and Windsurf have it via MCP add-ons. Codex has web search. But 5 tools (Copilot, Aider, Continue, Amazon Q, Jules) have no browser capability at all.

**Sandboxed execution (7 of 12 have it at PARTIAL or above).** Devin, OpenHands, Jules, and Codex CLI have strong sandbox. Claude Code, Cursor, Copilot, and Amazon Q have partial sandbox. The remaining 4 have primitive or no sandbox.

### What few tools have

**Memory with teeth (3 of 12 at PARTIAL or above).** Only Claude Code, Devin, and Windsurf reach PARTIAL. Everyone else is PRIMITIVE or DON'T HAVE. Memory is the most underserved high-impact component.

**Stateful agent daemon (3 of 12 at PARTIAL or above).** Only Copilot, Devin, and Jules reach PARTIAL. No tool has a full daemon. This is the biggest capability gap in the market.

**Credential management (3 of 12 at PARTIAL or above).** Only Claude Code, Copilot, and Amazon Q reach PARTIAL. Most tools rely on environment variables. Security is an afterthought.

### What no tool has

**Desktop vision + control.** Every score is PRIMITIVE or DON'T HAVE. Despite Anthropic's Computer Use existing as a product, no coding agent integrates it natively. This remains a research capability, not a product feature.

**Interactive PTY.** Only Codex CLI reaches PARTIAL (via js_repl). Every other tool is PRIMITIVE or DON'T HAVE. No coding agent can step through a debugger, use a REPL interactively, or navigate an SSH session.

**Audio/video I/O.** The weakest dimension across the entire market. Aider and Codex have voice input. Jules has audio summaries. Devin can ingest video files. No tool has real-time audio/video I/O.

---

## Best-in-Class Picks

| Component | Best Tool | Why |
|-----------|----------|-----|
| Terminal + structured tools | **Claude Code** | Native structured tools (Read, Edit, Grep, Glob) with explicit design rationale. Others have terminal access but not the same precision tooling. |
| Web browser | **Devin** | Built-in Chrome in a full cloud sandbox. Autonomous web navigation, API doc reading, Figma browsing. Cursor is close with built-in Chromium. |
| Desktop vision + control | **No leader** | No tool scores above PRIMITIVE. The entire market is missing this. |
| Memory with teeth | **Devin** | Vectorized codebase snapshots, full replay timeline, Devin Wiki. Claude Code is close with CLAUDE.md + hooks. Windsurf's auto-learning is distinctive. |
| Stateful agent daemon | **Devin** | Closest to always-on — event-driven triggers, persistent cloud service. Copilot is close with GitHub event integration. Jules with async cloud tasks. |
| Interactive PTY | **Codex CLI** | js_repl provides interactive REPL. No other tool has native PTY interaction. This is a wide-open gap. |
| Audio/video I/O | **No leader** | No tool scores above PRIMITIVE. Voice input (Aider, Codex) and video file ingestion (Devin) are the closest, but none are integrated. |
| Sandboxed execution | **Codex CLI** | OS-enforced kernel-level isolation (Landlock, seatbelt). Devin and Jules have strong cloud sandbox. OpenHands has the most scalable Docker sandbox. |
| Credential management | **GitHub Copilot** | Built-in secret scanning, short-lived tokens in ephemeral environments. Amazon Q is strong for AWS-native. Claude Code's scoped proxy is solid. |
| Multi-agent orchestration | **Cursor** | 8 parallel agents with Mission Control grid view. Codex CLI is close with first-party multi-agent. Claude Code has the richest ecosystem (native + community). |

---

## Trajectory Analysis — Who's Moving Fastest

### Accelerating

**Claude Code.** Background agents, Agent Teams (experimental), Slack integration, cloud sandbox, and the MCP ecosystem growing daily. Moving fast on multi-agent and daemon-adjacent capabilities. The MCP server architecture means the community fills gaps faster than any proprietary roadmap.

**Cursor.** 2.0 shipped built-in browser, 8-agent parallelism, and Mission Control in a single release. The pace of feature delivery is aggressive. If they add daemon mode and memory, they'll jump several spots.

**Codex CLI.** Open-source Rust rewrite, OS-enforced sandboxing, first-party multi-agent, voice input. OpenAI is clearly investing heavily. The sandbox and multi-agent capabilities are already best-in-class for a CLI tool.

**Cline.** CLI 2.0 brought terminal-native operation, parallel agents, subagent delegation, and process isolation in one update. The Remote Browser is unique among open-source tools. The community is one of the most active.

### Steady

**Devin.** Already the highest-scoring tool. Adding features (Wiki, Search) but the core architecture hasn't changed dramatically. The risk is that open-source tools (OpenHands, Claude Code, Codex) catch up by offering similar capabilities with more transparency and customization.

**GitHub Copilot.** Methodical expansion. Agentic Memory, CLI GA, Agent HQ. Strong integration story with GitHub ecosystem. Not moving as fast as Claude Code or Cursor on raw agent capabilities, but the event-driven model is unique.

### Falling Behind

**Aider.** Deliberately minimal by design. Not falling behind accidentally — the maintainers have chosen to stay focused on pair programming. The community fork (AiderDesk) is where new capabilities are being added.

**Continue.** The CI-enforceable rules are genuinely unique, but the overall capability set is narrow. Without browser, sandbox, or daemon capabilities, it's becoming a niche tool for CI integration rather than a general-purpose agent.

---

## The Honest Answer: Which One Should You Use?

There's no single winner. The right tool depends on what you're doing.

**If you live in the terminal and want the best tools + ecosystem:** Claude Code. The structured tools are genuinely better than any other tool's file manipulation. The MCP ecosystem means you can extend it infinitely.

**If you want an IDE and never leave it:** Cursor. Built-in browser, 8-agent parallelism, Mission Control. The most complete IDE-integrated agent experience.

**If you want to hand off tasks and walk away:** Devin (managed service) or Jules (Google ecosystem). Both run in the cloud, both work asynchronously, both handle full tasks autonomously.

**If you want open-source and self-hosted:** OpenHands for the strongest sandbox and browser. Cline for VS Code integration with built-in browser. Codex CLI for the tightest local security.

**If you're all-in on GitHub:** Copilot. Event-driven triggers, Agent HQ, secret scanning, ephemeral environments. Nothing else integrates as deeply with GitHub's workflow.

**If you're all-in on AWS:** Amazon Q / Kiro. IAM-native credentials, sandbox execution, CAO multi-agent across CLI tools.

**If you want a focused pair programmer, nothing more:** Aider. Does one thing well. Works with any model.

**If you want CI-integrated rule enforcement:** Continue. The only tool where AI coding standards are version-controlled CI checks.

### The Uncomfortable Truth

No tool scores above 18/30. The best tool in the market covers 60% of what a fully autonomous agent needs. The remaining 40% — desktop control, interactive PTY, audio/video, proper memory, daemon mode, credential security — is either primitive or nonexistent across the entire industry.

The "Less Is More" framework identifies 10 components. The market has built 1 completely (terminal), is converging on 3 more (browser, sandbox, multi-agent), and has barely started on the remaining 6.

We're early.

---

## Component Coverage Heatmap

How many tools cover each component at PARTIAL or above:

| Component | Tools at PARTIAL+ | % of Market | Assessment |
|-----------|------------------|-------------|------------|
| Terminal + structured tools | 12/12 | 100% | **Solved** |
| Web browser | 7/12 | 58% | Converging |
| Sandboxed execution | 7/12 | 58% | Converging |
| Multi-agent orchestration | 6/12 | 50% | Active investment |
| Memory with teeth | 3/12 | 25% | **Underserved** |
| Stateful agent daemon | 3/12 | 25% | **Underserved** |
| Credential management | 3/12 | 25% | **Underserved** |
| Desktop vision + control | 0/12 | 0% | **Nobody building** |
| Interactive PTY | 1/12 | 8% | **Nearly nobody building** |
| Audio/video I/O | 0/12 | 0% | **Nobody building** |

### The Three Tiers of Market Maturity

**Tier 1 — Solved:** Terminal + structured tools. Done. Everyone has it.

**Tier 2 — Active competition:** Browser, sandbox, multi-agent. These are the current battleground. Tools are differentiating here.

**Tier 3 — Wide open:** Memory, daemon, credentials, desktop, PTY, audio/video. Six out of ten components are either underserved or completely absent from the market. This is where the next wave of differentiation will come from.

The tool that figures out memory with teeth and daemon mode first will leapfrog everyone else. Those two components are force multipliers — they make every other component more valuable. The market knows this (Devin and Claude Code are both investing here), but nobody has cracked it yet.
