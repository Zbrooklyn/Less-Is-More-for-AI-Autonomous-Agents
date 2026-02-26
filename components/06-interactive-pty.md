# Interactive PTY

## Definition

A pseudo-terminal (PTY) capability that lets the AI agent have back-and-forth conversations with running processes. Instead of one-shot "run command, get output," the agent can spawn a persistent process, send input incrementally, read output in real-time, and respond to prompts — just like a human typing at a terminal.

## Purpose

Interactive processes are everywhere in real development work: debuggers, REPLs (Python, Node, Ruby), SSH sessions, database consoles (psql, mysql, redis-cli), package manager prompts, installers, git interactive operations (rebase -i, add -p), and container shells (docker exec -it). Every one of these is a hard wall for current AI agents — not a difficulty, a wall. The agent literally cannot do them.

Without interactive PTY, an entire class of developer workflows is inaccessible. The agent can write code but can't debug it interactively. It can connect to a server but can't navigate around. It can start a REPL but can't use it.

## Status: DON'T HAVE

One-shot Bash command execution exists — run a command, get the output when it finishes. `pexpect` (Python), `expect` (Tcl), and `tmux` scripting exist as primitive tools for automating interactive sessions but aren't connected to AI agents. No AI agent framework has native interactive terminal support.

## Key Insight

The fundamental shift is from **fire-and-forget** to **conversational execution**. Current agents treat every command as a letter — send it, wait for the full reply. Interactive PTY treats commands as a conversation — send a line, read the response, decide what to say next based on what came back. This is the same shift that made chat interfaces more powerful than single-prompt interfaces, applied to process interaction.

## The Five Requirements

1. **Session creation** — spawn a process with a PTY attached, keep it alive across multiple interactions
2. **Send input** — type characters including special keys (Ctrl+C, Ctrl+D, arrow keys, Enter)
3. **Read output** — get what the process prints in real-time, not just when it exits
4. **State awareness** — know when the process is waiting for input vs. still producing output vs. finished
5. **Session management** — multiple concurrent sessions, ability to switch, close, and resume

## What It Covers

- Debugger attachment — set breakpoints, inspect variables, step through code
- REPL-driven development — persistent Python/Node/Ruby sessions with state
- SSH sessions — navigate remote servers, edit configs, check logs interactively
- Database consoles — run queries, explore schemas, manage data
- Package manager prompts — answer installation questions, accept licenses
- Git interactive operations — interactive rebase, patch-mode staging, conflict resolution
- Container shells — full interactive access to Docker containers
- Any process that expects back-and-forth human input
