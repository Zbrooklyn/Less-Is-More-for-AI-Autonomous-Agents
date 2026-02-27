# Memory With Teeth

## Definition

A persistent, self-enforcing memory system that automatically loads relevant context, enforces learned rules, captures corrections without manual logging, survives context window compression, and verifies that the agent actually followed its own rules. Not notes the AI might check — a system that loads itself, enforces itself, and learns on its own.

## Purpose

Without real memory, every AI conversation starts from zero. The agent makes the same mistakes it was corrected for yesterday. It forgets project rules, user preferences, rejected alternatives, and hard-won debugging insights. The user becomes the memory system — repeating instructions, re-explaining context, catching the same errors over and over.

Memory with teeth transforms the agent from a stateless tool into something that genuinely learns from experience and gets better over time.

## Status: PRIMITIVE

Manual markdown files (MEMORY.md, hot-memory.md) exist. Bootstrap instructions tell the AI to read them. Claude Code hooks provide basic enforcement. But the system depends on the AI remembering to check its memory (circular), rules are suggestions not guardrails, memory decays as context compresses, there's no semantic retrieval, and correction logging is manual and often skipped.

## Key Insight

Current AI memory is **RAM without a hard drive**. Everything loaded at the start of a conversation degrades over time as context compresses. Critical rules and corrections need to be stored outside the conversation context entirely — in a persistent layer that survives regardless of how long the session runs or how much context gets compressed.

---

## What Currently Exists

Files. Markdown files that instructions tell the AI to read at session start. `MEMORY.md`, `hot-memory.md`, `corrections-log.md`, and so on. They're notes. Post-it notes on a desk that the AI is *told* to look at before it starts working.

## Why That's Not "Teeth"

Here's what actually happens:

1. **The AI has to be told to read them.** If the bootstrap instructions aren't perfect, it skips them. Memory that depends on the AI remembering to check its memory is circular.

2. **They're suggestions, not enforcement.** The AI reads "NEVER use `pythonw.exe`" — but nothing *stops* it. It's in context, it'll probably follow it, but there's no guardrail. It's a sign that says "don't touch the stove" vs an actual stove guard.

3. **They decay over long sessions.** As context compresses, the memory loaded at the start gets summarized or dropped. By turn 40, the AI may have functionally forgotten what it read at turn 1.

4. **No retrieval.** If the AI is debugging a pywebview issue, it can't query "what do I know about pywebview?" It only knows what was loaded at the start. If it's in `context-memory.md` and that file wasn't loaded, it doesn't exist.

5. **Manual logging.** When the user corrects the AI, it's supposed to write it down. But that depends on recognizing it as a correction, stopping work, writing to a file, and doing it in the right format. It's friction. So sometimes it just doesn't happen.

## The Six Levels

### Level 1: Automatic Injection (solves the "forgot to read" problem)

The system — not the AI — detects what it's working on and **injects relevant memory into context before the AI even starts thinking.** Not "please read this file." The memory is already there.

- The AI opens a file in `projects/WhisperClick V3/` → the system automatically injects WhisperClick rules, known pitfalls, rejected alternatives
- The AI is about to run a `git push` → the system injects the public/private repo sync rules
- No manual loading. No bootstrap phrase games. It's just *there*.

### Level 2: Enforcement Hooks (solves the "suggestions not guardrails" problem)

Rules that **intercept actions before they execute:**

- The AI tries to call `pythonw.exe` → the system blocks it and says "Memory rule: never use pythonw.exe on this system. Reason: silent crash with Qt/PySide6"
- The AI tries to `git push public main` → blocked. "Memory rule: this leaks private files. Use sync_public.py instead"
- Not a note it read. An actual gate it can't walk through.

A primitive version of this already exists — Claude Code hooks can run shell commands before/after tool calls. But they're blunt. Real enforcement would understand *intent*, not just pattern-match on commands.

### Level 3: Semantic Retrieval (solves the "didn't load the right file" problem)

Instead of flat files the AI sequentially reads, memory is a **searchable database with embeddings:**

- The AI encounters an error → the system searches past corrections and surfaces "You hit this same error on 2026-01-15. The fix was X"
- The AI is about to make an architecture decision → the system surfaces "You rejected this approach on 2025-12-03 because Y"
- No file organization required. No "which markdown file is this in?" Just ask and get relevant results, ranked by relevance and recency.

### Level 4: Automatic Capture (solves the "manual logging" problem)

The system watches the conversation and **detects corrections without the AI having to log them:**

- The user says "No, do it this way" → the system extracts: what was wrong, what's right, tags it with context, stores it
- The user says "Always use X" → the system creates an enforcement rule automatically
- The user says the same thing three times → the system promotes it to a high-confidence rule without anyone asking
- No friction. No "let me update my memory file." It just learns.

### Level 5: Persistent Across Context Compression (solves the decay problem)

Critical rules are **pinned outside the conversation context entirely:**

- Even when the context window compresses old messages, pinned rules remain at full fidelity
- They're not part of the conversation history that gets summarized — they're a separate, persistent layer
- Think of it as the difference between RAM and a hard drive. Currently all AI memory is RAM. It gets flushed.

### Level 6: Behavioral Verification

The system **checks whether the AI actually followed the rules:**

- After the AI completes a task, a verification pass runs: "Did this response violate any known rules?"
- If the AI suggests `pythonw.exe` despite the rule, it gets caught before the response reaches the user
- A feedback loop: violations get logged, repeated violations strengthen the rule's enforcement level

## The Full Picture

| Level | What It Does | Current State |
|-------|-------------|---------------|
| Automatic injection | Right memory loads based on context | Manual file reads |
| Enforcement hooks | Blocks known-bad actions | Post-it notes the AI might follow |
| Semantic retrieval | Query past experience by meaning | Sequential file reads, hope it's there |
| Automatic capture | Learns from corrections without friction | Manual logging that sometimes gets skipped |
| Compression-proof | Rules survive long sessions | Decays as context compresses |
| Behavioral verification | Checks if rules were actually followed | Honor system |

## The Hard Problems

**1. Relevance filtering.** Not every memory is relevant to every task. Injecting too much context wastes the context window. Injecting too little misses important rules. The system needs to judge relevance — which requires understanding what the agent is about to do, not just what file it opened.

**2. Conflicting memories.** Over time, rules may contradict each other — especially across projects. "Always use TypeScript" for Project A, "Use JavaScript only" for Project B. The system needs scope-aware memory that knows which rules apply where.

**3. Memory decay vs. memory bloat.** Old memories that are never referenced should eventually fade. But removing a memory that turns out to still be relevant is dangerous. The balance between keeping memory lean and keeping it complete is hard to get right.

**4. Privacy and sensitivity.** Memory persists across sessions. If the user discusses something sensitive in one session, it shouldn't surface unexpectedly in another. The system needs a concept of memory sensitivity and appropriate retention policies.

**5. Bootstrapping from zero.** A new user has no memory. The system needs to learn quickly from the first few sessions without being annoying ("Should I remember this? And this? And this?"). The early experience defines whether the user trusts the system enough to keep using it.

## What Would Need to Be Built

1. **A context-aware injector** — monitors what the agent is working on and loads relevant memory automatically
2. **An enforcement engine** — hooks into the agent's action pipeline and blocks known-bad actions
3. **A vector store** — embeddings over all memory entries, searchable by semantic similarity
4. **A correction detector** — NLP system that identifies corrections in conversation ("No, do it this way")
5. **A pinning system** — critical rules stored outside the conversation context, immune to compression
6. **A verification checker** — post-response scan that compares actions against known rules

## What It Covers

- User preferences and workflow habits
- Project-specific rules and conventions
- Rejected alternatives and why they were rejected
- Debugging solutions for recurring problems
- Architectural decisions and their rationale
- Corrections from the user, automatically captured and enforced
- Cross-session continuity — picking up where the last session left off

## Market Landscape (February 2026)

The memory space has exploded. At least a dozen competing systems now exist, with three major benchmarks (LOCOMO, LongMemEval, Letta Memory Benchmark) creating some standardization. Despite the activity, **nobody implements all six levels.**

### The 6-Level Market Matrix

| System | L1 Auto-Inject | L2 Enforce | L3 Semantic | L4 Auto-Capture | L5 Compress-Proof | L6 Verify | Notes |
|--------|:-:|:-:|:-:|:-:|:-:|:-:|-------|
| **Letta** | YES | PARTIAL | YES | YES | YES | NO | Git-backed Context Repositories + sleep-time compute. Model-dependent. |
| **Mastra OM** | YES | NO | YES | YES | YES | NO | 94.87% LongMemEval. Observer/Reflector agents. 3-6x compression. Open source. |
| **Zep (Graphiti)** | YES | NO | YES | YES | YES | NO | Temporal knowledge graphs. Old facts invalidated, not deleted. 94.8% DMR. |
| **Hindsight** | YES | NO | YES | YES | YES | NO | 91.4% LongMemEval. Four memory networks. MIT-licensed. |
| **Cognee** | YES | NO | YES | YES | YES | NO | Knowledge graph engine. $7.5M seed. 70+ companies. 38+ source types. |
| **Mem0** | YES | NO | YES | YES | YES | NO | 66.9% LOCOMO. Simplest integration. Graph memory paywalled at $249/mo. |
| **Google Memory Bank** | YES | NO | YES | YES | YES | NO | Only major cloud provider with managed agent memory. Black box. |
| **ODEI** | YES | YES | YES | YES | YES | NO | Constitutional memory — 7 validation layers. Built for financial/transactional agents. |
| **memU** | YES | NO | YES | YES | YES | NO | Claims 92% LOCOMO — unverified independently. Hierarchical knowledge graphs. |
| **Claude Code** | YES | YES | NO | NO | PARTIAL | NO | CLAUDE.md + hooks. Simplest and most transparent. Also most manual. |
| **OpenAI** | PARTIAL | NO | PARTIAL | PARTIAL | PARTIAL | NO | No developer-facing memory API. Biggest gap of any major provider. |

### Key Findings

**Level 6 (behavioral verification) doesn't exist anywhere.** Zero implementations across the entire market. No system checks whether the agent actually followed its own rules after acting. This is the biggest open problem in agent memory.

**Level 2 (enforcement) is almost nobody.** Only Claude Code (hooks) and ODEI (constitutional validation). Everyone else can remember things but can't block bad actions based on what they remember. Memory without enforcement is still a suggestion.

**Most systems cluster at L1+L3+L4+L5.** They can inject, search, capture, and persist. But they can't enforce or verify. The pattern is clear: the industry has solved memory storage. It hasn't solved memory enforcement.

**Claude Code is unique:** the only system with L2 enforcement but missing L3 (semantic retrieval) and L4 (automatic capture). It can block bad actions but can't search memory by meaning or learn from corrections automatically.

### Benchmark Landscape

Multiple benchmarks now exist, with different methodologies producing different scores:

| Benchmark | What It Tests | Top Score | By Whom |
|-----------|--------------|-----------|---------|
| **LongMemEval** (ICLR 2025) | Multi-session recall, temporal reasoning, knowledge updates. 500 questions, 115K-1.5M tokens. | 94.87% | Mastra OM + gpt-5-mini |
| **LOCOMO** (ACL 2024) | Multi-session conversations, ~600 turns. Single-hop, multi-hop, temporal, open-domain. | 92.09% (unverified) | memU (NevaMind) |
| **Deep Memory Retrieval** | Memory retrieval accuracy. | 94.8% | Zep (Graphiti) |
| **Letta Leaderboard** | Agentic memory operations (read, write, update). Tests models, not systems. | Claude Sonnet 4 | Letta (own benchmark) |

**Warning:** LOCOMO scores vary wildly by scoring methodology — F1, BLEU, and LLM-as-Judge produce different numbers. Scores from different systems using different methodologies are not directly comparable.

### Notable Approaches

**Mastra Observational Memory** — the dark horse. Two background agents (Observer and Reflector) watch conversations and compress them into dated observation logs. Observer triggers at 30K unobserved tokens, Reflector consolidates at 40K observations. Achieves 3-6x text compression, 5-40x for tool-heavy workloads. Stable append-only prefix enables high prompt cache hit rates (4-10x cost reduction). Open source, from the team that built Gatsby.

**Letta Sleep-Time Compute** — background agents that run during idle periods to consolidate fragmented memories, identify patterns, and reorganize/deduplicate memory blocks. The closest thing to "memory that improves itself" in production.

**Zep Temporal Knowledge Graphs** — when facts change, old ones are marked as superseded, not deleted. The agent always uses current information but can access the history of how facts evolved. Critical for long-running agents where context changes over weeks and months.

**ODEI Constitutional Memory** — 7 validation layers before every memory write: immutability, temporal validity, referential integrity, authority, deduplication, provenance, constitutional alignment. Zero hallucination errors and zero duplicate actions in Jan-Feb 2026 production. The only system designed specifically for agents handling money.

### Build vs. Integrate Assessment

For the [Implementation Roadmap](11-implementation-roadmap.md) Phase 1 (Memory Foundation):

- **Integrate for L3+L4+L5:** Mastra OM (best compression + benchmarks), Hindsight (MIT license, four-network architecture), or Cognee (knowledge graphs, production-proven) can provide semantic retrieval, automatic capture, and compression-proof persistence as a foundation.
- **Build for L2:** Enforcement hooks are custom to your agent's rule system. Only Claude Code has this, and it's primitive. The daemon's enforcement engine needs to understand intent, not just pattern-match commands.
- **Build for L6:** Nobody has this. First-mover opportunity. A post-response verification pass that compares actions against known rules would be genuinely novel.
- **Build the glue:** The integration between L1 injection, L2 enforcement, and L3 retrieval is the custom work. No existing system combines all three.

---

## The Bottom Line

**Memory with teeth is the single biggest limitation of AI agents today.** Tools, browser, desktop control — those are all solvable engineering problems. Memory touches the architecture of how models work at a fundamental level. It's the foundation that the stateful daemon and multi-agent orchestration both depend on. Build it first.

The market has made significant progress on Levels 1, 3, 4, and 5 — injection, retrieval, capture, and persistence are solved problems with multiple production implementations. **Levels 2 (enforcement) and 6 (verification) remain wide open.** The first system to combine all six levels will have a memory architecture that no existing tool matches.
