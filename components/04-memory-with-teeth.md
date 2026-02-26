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

## The Bottom Line

**Memory with teeth is the single biggest limitation of AI agents today.** Tools, browser, desktop control — those are all solvable engineering problems. Memory touches the architecture of how models work at a fundamental level. It's the foundation that the stateful daemon and multi-agent orchestration both depend on. Build it first.
