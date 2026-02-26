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

---

## What Exists Today

**One-shot command execution.** The agent runs a command, it finishes, the agent gets the output. That's it. Every single thing done in Bash works like this — fire and receive. It's like communicating by letter. Send a message, wait, get a response. The agent can never interrupt, react mid-stream, or have a back-and-forth.

**What that means practically:**
- Can run `python -c "print(2+2)"` — a single expression, one result
- **Cannot** run `python`, then type `x = 5`, then type `print(x)`, then type `exit()` as a live session
- Can run `git log` — but **cannot** run `git rebase -i` because it opens an editor and waits for interaction
- Can run `ssh user@server "ls /tmp"` — a single remote command. **Cannot** open an SSH session and navigate around interactively
- Can run a test suite. **Cannot** attach a debugger, set a breakpoint, inspect a variable, step through code, and then continue

## Why This Matters More Than It Sounds

Interactive processes are everywhere in real development work:

| Task | Why It Needs Interactive PTY |
|------|------------------------------|
| Debugging | Breakpoints, variable inspection, stepping — all interactive |
| REPL-driven development | Python, Node, Ruby, Elixir — all have REPLs that developers live in |
| SSH sessions | Navigating remote servers, editing configs, checking logs |
| Database consoles | `psql`, `mysql`, `redis-cli` — all interactive |
| Package managers | `npm init`, `pip install` with prompts, `apt` confirmation dialogs |
| Installers | "Do you accept the license? [y/N]" — can't answer |
| Git interactive operations | `git rebase -i`, `git add -p` (patch mode), merge conflict resolution |
| Container shells | `docker exec -it container bash` — the `-it` literally stands for "interactive terminal" |

Every one of these is a wall right now. Not a difficulty — a wall. The agent literally cannot do them.

## What a Proper Interactive PTY Looks Like

A **pseudo-terminal (PTY)** is a virtual terminal that lets a program think it's talking to a human at a keyboard. The AI needs:

**1. Session creation** — spawn a process with a PTY attached, keep it alive across multiple interactions

**2. Send input** — type characters into the running process, including special keys (Ctrl+C, Ctrl+D, arrow keys, Enter)

**3. Read output** — get what the process prints back, in real-time, not just when it exits

**4. State awareness** — know when the process is waiting for input vs. still producing output vs. finished

**5. Session management** — multiple concurrent sessions (SSH in one, debugger in another), ability to switch between them, close them, resume them

## The Hard Problems

**1. Timing.** When input is sent, how does the agent know the process is ready for it? If it types too fast, characters might get swallowed. If it waits too long, it's wasting time. A human sees the prompt appear and types. The AI needs to reliably detect "the process is waiting for my input."

**2. Output parsing.** Terminal output includes ANSI escape codes — colors, cursor movements, screen clearing. A human sees a nicely formatted screen. The AI sees `\033[32m\033[1muser@host\033[0m:\033[34m~/project\033[0m$ `. Parsing this into meaningful content without losing information is non-trivial.

**3. Screen-based applications.** Programs like `vim`, `htop`, `less`, or `nano` don't output lines — they paint a screen. They use cursor positioning to update specific cells. To interact with these, the AI needs to understand a 2D terminal screen, not just a stream of text. This is essentially the "desktop vision + control" problem but inside a terminal.

**4. Blocking and timeouts.** Some commands run for minutes. Some run forever until interrupted. The AI needs to decide: wait longer, send Ctrl+C, or abandon the session. A human uses judgment ("this compile is taking too long, something's wrong"). The AI needs equivalent heuristics.

**5. Security.** An interactive session to a production server is powerful and dangerous. The same authority boundary model from the daemon applies here — but faster, because interactive sessions happen in real-time and mistakes can't be easily batched or reviewed before execution.

## The Difference

| | Current (one-shot) | Interactive PTY |
|---|-------------------|-----------------|
| Process lifetime | Starts, runs, exits | Stays alive across interactions |
| Input model | All input provided upfront | Input sent incrementally, in response to output |
| Output model | All output received at end | Output streamed in real-time |
| Debugging | Can't attach a debugger | Set breakpoints, inspect, step |
| Remote access | Single command over SSH | Full SSH session |
| REPL workflows | One expression at a time | Persistent session with state |

## What Would Need to Be Built

1. **A PTY multiplexer** — like `tmux` or `screen`, but API-driven. Create sessions, send input, read output, all through structured commands rather than keyboard input
2. **An output parser** — strips ANSI codes, detects prompts, identifies when the process is waiting for input
3. **A screen reader for TUI apps** — for full-screen applications, captures the terminal screen state as structured data
4. **Session lifecycle management** — track which sessions are alive, idle, waiting for input, or finished
5. **Input sanitization** — prevent accidental injection of dangerous commands in interactive sessions

## What It Covers

- Debugger attachment — set breakpoints, inspect variables, step through code
- REPL-driven development — persistent Python/Node/Ruby sessions with state
- SSH sessions — navigate remote servers, edit configs, check logs interactively
- Database consoles — run queries, explore schemas, manage data
- Package manager prompts — answer installation questions, accept licenses
- Git interactive operations — interactive rebase, patch-mode staging, conflict resolution
- Container shells — full interactive access to Docker containers
- Any process that expects back-and-forth human input
