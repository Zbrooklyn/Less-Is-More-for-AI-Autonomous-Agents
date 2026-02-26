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

## What It Covers

- File reading with line targeting and format support (images, PDFs)
- File writing and creation
- Precision text editing with uniqueness checks and diff visibility
- Content search with structured file + line results
- File pattern matching sorted by modification time
- General-purpose shell command execution
- Process management, package installation, build tooling, git operations
