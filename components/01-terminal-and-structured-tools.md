# Terminal + Structured Tools

## Definition

The foundational layer of AI agent capability. A terminal (shell) provides universal command execution — anything a human can type at a command line, the agent can execute. Structured tools (Read, Write, Edit, Grep, Glob) are precision wrappers around common terminal operations that add safety checks, structured output, and context efficiency.

## Purpose

The terminal alone makes everything *possible*. The structured tools make common operations *reliable*. Together they handle all file manipulation, code editing, system administration, package management, build processes, and general-purpose computation.

Without this layer, the agent can't do anything. This is the foundation every other component builds on.

## Status: HAVE

This is the only component that is fully built today. Read, Write, Edit, Grep, Glob, and Bash are all functional and integrated into AI agent tooling (Claude Code, Cursor, etc.).

## Key Insight

Structured tools are **accuracy multipliers**, not capability additions. They prevent specific classes of errors (wrong-location edits, context window overflow, parse ambiguity) that the terminal alone would cause. They earn their place by reducing the error rate on common operations, not by enabling new ones.

A human can do surgery with a kitchen knife. The scalpel doesn't enable anything new — it just makes the success rate go from 40% to 99%.

---

## Why the Terminal Is Enough (in theory)

A terminal is a universal interface. Bash is Turing-complete. In theory, one tool is sufficient. Every other structured tool is doing something the terminal can already do:

- **Read** → `cat`, `head`, `tail`
- **Write** → `echo >`, `cat << EOF`
- **Edit** → `sed`, `awk`
- **Grep** → `grep`, `rg`
- **Glob** → `find`, `ls`

If you took away every structured tool, the agent could still do everything. It would just make more mistakes and burn more context doing it.

## Why Structured Tools Still Matter (in practice)

Each structured tool earns its place by **preventing a specific class of error**:

| Tool | What It Prevents | How Bash Fails |
|------|-----------------|----------------|
| **Read** | Context overflow — reading only the lines you need, handling images/PDFs natively | `cat` dumps the entire file into context. A 5000-line file wastes the whole window. |
| **Edit** | Wrong-location edits — uniqueness check ensures you edit exactly what you intend. User sees the exact diff. | `sed` is blind. It matches patterns, not intent. A common string edits the wrong line. |
| **Write** | Format consistency — keeps parity with Read/Edit for file creation | `echo >` with heredocs works but requires careful quoting. Easy to mangle content. |
| **Grep** | Parse ambiguity — returns structured file + line results | `grep` returns raw text. The AI has to parse filenames, line numbers, and content from an unstructured string. |
| **Glob** | Result ordering — sorted by modification time, focused results | `find` returns unsorted, verbose output. Easy to miss the most relevant file. |
| **Bash** | Nothing — it's the escape hatch | It IS bash. Used for everything the other tools don't cover. |

## The Practical Working Set

### Layer 1: Core File Work (daily, every session)

| Tool | Why Not Just Bash? |
|------|--------------------|
| **Read** | Targets line ranges, reads images/PDFs, doesn't blow up context on big files |
| **Edit** | Uniqueness check prevents wrong-location edits. User sees exact diff |
| **Write** | Keeps parity with Read/Edit for file creation |
| **Grep** | Structured file+line results without parsing ambiguity |
| **Glob** | Sorted by modification time, cleaner than `find` |
| **Bash** | The escape hatch. Everything else that doesn't need guardrails |

**6 tools.** Each one prevents a specific class of error.

### Layer 2: Force Multipliers (most sessions)

| Tool | What It Saves |
|------|--------------|
| **Sub-agents / Task** | Parallel work. Without this, everything runs sequentially — 3x slower on research-heavy tasks |
| **Web search + fetch** | The AI can't reason about what it hasn't read. Without this, it's stuck with training data |

**8 tools total.** This handles ~95% of real software engineering work efficiently.

## What It Covers

- File reading with line targeting and format support (images, PDFs)
- File writing and creation
- Precision text editing with uniqueness checks and diff visibility
- Content search with structured file + line results
- File pattern matching sorted by modification time
- General-purpose shell command execution
- Process management, package installation, build tooling, git operations
- Sub-agent spawning for parallel work
- Web search and fetch for current information

## Where It Falls Short

The terminal + structured tools cover ~90-95% of software engineering work. The remaining 5-10% is where the other 9 components come in:

1. **Interactive processes** — can't type into running programs (→ Interactive PTY)
2. **GUI interaction** — can't click buttons or see the screen (→ Desktop Vision + Control)
3. **Real-time state** — can't watch and react to ongoing processes (→ Stateful Agent Daemon)
4. **Web apps** — can't navigate complex web interfaces (→ Web Browser)
5. **Parsing ambiguity** — even with structured tools, raw terminal output still has edge cases

## The Bottom Line

The terminal is the foundation. Structured tools are the guardrails. Together they're the only component that's fully built today — and they handle the vast majority of real work. Everything else in the 10-component framework builds on top of this layer.
