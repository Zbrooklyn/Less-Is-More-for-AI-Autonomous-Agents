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

## The Six Levels

1. **Automatic injection** — the system loads relevant memory based on what the agent is working on, not what the agent remembers to read
2. **Enforcement hooks** — rules that intercept and block known-bad actions before they execute
3. **Semantic retrieval** — search past experience by meaning, not by file location
4. **Automatic capture** — the system detects corrections in conversation and logs them without the agent having to manually write them down
5. **Compression-proof persistence** — critical rules pinned outside the conversation context, immune to summarization
6. **Behavioral verification** — a check after each response to verify rules were actually followed

## What It Covers

- User preferences and workflow habits
- Project-specific rules and conventions
- Rejected alternatives and why they were rejected
- Debugging solutions for recurring problems
- Architectural decisions and their rationale
- Corrections from the user, automatically captured and enforced
- Cross-session continuity — picking up where the last session left off
