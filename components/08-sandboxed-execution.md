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

---

## What Exists Today

**Everything runs on the real machine.** When the agent edits a file, it's the real file. When it runs a command, it's on the real system. When it installs a package, it goes into the real environment. There's no undo button on reality.

The safety model right now is entirely permission-based:
- The agent asks before doing risky things
- The user approves or denies
- If a mistake happens, it gets fixed manually (or it's already too late — `rm -rf` doesn't ask twice)

**What kind-of exists:**
- **Docker containers** — isolated environments, but have to be manually built, run, and managed. There's no "spin up a sandbox for this experiment" button.
- **Git worktrees** — isolated copy of the repo. This exists in tooling (the Task tool has an `isolation: "worktree"` mode). But it's repo-level only — it doesn't isolate the system, packages, or running processes.
- **Virtual environments (venv/conda)** — Python-level isolation. Doesn't protect the filesystem, system packages, or anything outside Python.
- **VMs** — full isolation, but heavy. Minutes to spin up, gigabytes of disk, complex management.

## Why This Matters

The more autonomous the agent becomes, the more it needs sandboxes:

| Scenario | What Goes Wrong Without a Sandbox |
|----------|-----------------------------------|
| Testing a fix before committing | The fix might break something else — now the real codebase is broken |
| Running untrusted code | A downloaded script could do anything to the system |
| Experimenting with system changes | "Let me try changing this config" — oops, now the server won't start |
| Daemon mode auto-fixes at 3 AM | The daemon's "fix" makes things worse — on the real production system |
| Trying multiple approaches | "Let me try approach A and approach B and compare" — can't do both simultaneously on one system |
| Destructive testing | "What happens if I delete this file?" — can't test on real data |
| Dependency upgrades | `npm update` breaks 15 things — now the real project is broken while you fix it |

The daemon section talked about authority boundaries — "what is the agent allowed to do?" Sandboxing answers a different question: **"where is the agent allowed to do it?"** Even if the agent has authority to try a fix, it should try it in a sandbox first and only apply it to reality after verifying it works.

## The Five Capabilities

### 1. Instant Environment Cloning

The AI says "I want to try something" and within seconds gets:
- A full copy of the current project state
- Same OS, same packages, same configuration
- Completely isolated — nothing the AI does here affects the real environment
- Disposable — destroy it when done, no cleanup needed

Not a Docker container you build from a Dockerfile over 5 minutes. An instant snapshot that's ready to use.

### 2. Multiple Concurrent Sandboxes

The AI needs to compare approaches:
- **Sandbox A**: Try fixing the bug by updating the dependency
- **Sandbox B**: Try fixing the bug by patching the code
- **Sandbox C**: Try fixing the bug by rolling back the last commit
- Run all three simultaneously, compare results, apply the winner to reality

This is something humans literally cannot do efficiently. An AI with concurrent sandboxes can explore a solution space in parallel.

### 3. Graduated Promotion

Changes don't jump from sandbox to production. They go through stages:

```
Sandbox → Verified in sandbox → Applied to local dev → Tested in dev → Promoted to staging → Production
```

The AI manages this pipeline. Each stage has its own checks. Failure at any stage rolls back without affecting later stages.

### 4. Snapshot and Rollback

At any point, the AI can:
- **Snapshot** the current state ("save game")
- **Try something risky** knowing it can roll back
- **Rollback** to any previous snapshot instantly

This turns every experiment into a safe experiment. The cost of failure drops to nearly zero.

### 5. Resource Limits

Sandboxes have hard limits:
- **CPU/memory caps** — a runaway process can't kill the host
- **Disk quotas** — can't fill up the real disk
- **Network restrictions** — can't accidentally hit production APIs from a test sandbox
- **Time limits** — sandbox auto-destructs after N minutes if forgotten

## The Hard Problems

**1. Speed.** If creating a sandbox takes 30 seconds, the AI won't use it for quick experiments. It needs to be near-instant (under 2 seconds) to be practical. This likely requires filesystem-level snapshotting (like ZFS/btrfs snapshots or overlayfs) rather than full copies.

**2. Fidelity.** A sandbox that doesn't perfectly match the real environment gives false results. "It worked in the sandbox but not in production" defeats the purpose. The closer to identical, the more useful — but perfect fidelity is expensive.

**3. State synchronization.** If the real environment changes while a sandbox is running (another developer pushes code, a config updates), the sandbox is now stale. The AI needs to know: "my sandbox is 15 minutes behind reality, results may not apply."

**4. Cost at scale.** If the daemon is spinning up sandboxes for every event at 3 AM, resource consumption can spike. Need smart decisions about when sandboxing is worth the cost vs. when the action is safe enough to apply directly.

**5. Platform differences.** Sandboxing on Linux (cgroups, namespaces, overlayfs) is well-supported. On Windows and macOS, the primitives are different and less mature. Building a cross-platform sandbox abstraction is significant engineering.

## The Difference

| | Current State | Sandboxed Execution |
|---|--------------|---------------------|
| Where experiments happen | On your real machine | In disposable copies |
| Cost of failure | Real damage, manual cleanup | Destroy sandbox, try again |
| Comparing approaches | One at a time, sequentially | Multiple in parallel |
| Rollback capability | `git checkout` (files only) | Full system state rollback |
| Daemon safety | Authority rules only | Authority rules + isolated execution |
| Speed to experiment | Minutes (manual setup) | Seconds (instant clone) |

## What Would Need to Be Built

1. **A snapshot engine** — instant filesystem snapshots using OS-level primitives (overlayfs on Linux, similar on other platforms)
2. **An environment cloner** — copies not just files but also installed packages, running services, environment variables, and configuration
3. **A sandbox orchestrator** — creates, tracks, and destroys sandboxes. Manages resource limits and lifetimes
4. **A diff/merge engine** — compares sandbox state to real state, generates a clean patch to apply the sandbox's changes to reality
5. **Integration with the daemon** — the daemon automatically sandboxes risky actions, verifies results, then promotes to reality

## What It Covers

- Safe testing of fixes before committing to the real codebase
- Running untrusted or downloaded code without risk to the system
- Experimenting with system configuration changes
- Daemon mode auto-fixes verified in sandbox before applying to reality
- Parallel approach comparison — multiple solutions tested simultaneously
- Destructive testing — "what happens if I delete this?" without consequences
- Dependency upgrade testing — try the upgrade, see what breaks, without breaking the real project
