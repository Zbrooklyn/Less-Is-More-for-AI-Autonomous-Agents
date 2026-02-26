# Sandboxed Execution

## Definition

The ability for an AI agent to instantly spin up isolated copies of the current environment — same files, same packages, same configuration — where it can experiment, test, and break things without affecting the real system. Includes instant cloning, multiple concurrent sandboxes, snapshot/rollback, graduated promotion from sandbox to reality, and resource limits.

## Purpose

Currently, everything the agent does happens on your real machine. Edit a file — it's your real file. Run a dangerous command — it hits your real system. Try an experimental fix — if it breaks something, your real codebase is broken. The safety model is entirely permission-based: the agent asks, you approve, and if something goes wrong, you clean it up manually.

Sandboxing answers the question: **"where is the agent allowed to do it?"** Even if the agent has authority to try a fix, it should try it in a sandbox first and only apply it to reality after verifying it works. This is especially critical for daemon mode, where the agent acts autonomously at 3 AM and can't ask for permission.

## Status: PRIMITIVE

Git worktrees via the Task tool provide repo-level file isolation. Docker exists for manual container-based isolation. Python venvs isolate packages. Windows Sandbox, WSL, and Firecracker microVMs exist as OS-level isolation technologies. None of these are integrated into any AI agent framework as a native, instant, automated capability.

## Key Insight

The killer feature isn't isolation — it's **parallel experimentation**. A human developer can try one approach at a time. An AI with concurrent sandboxes can try three approaches simultaneously, compare results, and apply the winner. This is something humans literally cannot do efficiently, and it turns the agent's non-determinism from a weakness into a strength — try multiple paths, pick the best outcome.

## The Five Capabilities

1. **Instant environment cloning** — full copy of project state in under 2 seconds, same OS/packages/config, completely isolated, disposable
2. **Multiple concurrent sandboxes** — try approach A, B, and C simultaneously, compare results, apply the winner
3. **Graduated promotion** — sandbox → verified → local dev → tested → staging → production, with checks at each stage
4. **Snapshot and rollback** — save state at any point, try something risky, roll back instantly if it fails
5. **Resource limits** — CPU/memory caps, disk quotas, network restrictions, time limits to prevent runaway processes

## What It Covers

- Safe testing of fixes before committing to the real codebase
- Running untrusted or downloaded code without risk to the system
- Experimenting with system configuration changes
- Daemon mode auto-fixes verified in sandbox before applying to reality
- Parallel approach comparison — multiple solutions tested simultaneously
- Destructive testing — "what happens if I delete this?" without consequences
- Dependency upgrade testing — try the upgrade, see what breaks, without breaking the real project
