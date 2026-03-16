# Build Roadmap — Autonomous AI Agent

> This is the build plan, not the research plan. Claude builds it. Each step has concrete deliverables, testable "done" criteria, and a clear "what you can do after this that you couldn't before."

---

## How This Works

- **Builder:** Claude (in sessions with Edward)
- **Timing:** Per-session, not per-week. Each session = one focused build block.
- **Testing:** Every session ends with working tests. Nothing ships untested.
- **Dependency rule:** Each step only starts after the previous step's tests pass.
- **Research repo:** `projects/less-is-more/` (the "why"). This repo is the "how."

---

## Step 1: Quick Wins

**What:** Harden the current setup. No new code in this repo — these improve what's already running.

| Task | Where | Done When |
|------|-------|-----------|
| Move API keys from `.env` to Windows Credential Manager | `~/.claude/`, project `.env` files | `keyring` CLI retrieves keys, `.env` files deleted or emptied |
| Add pre-commit hook for secret scanning | AI_Projects repo | `git commit` with a key pattern in staged files gets rejected |
| Add 3 enforcement hooks to Claude Code | `~/.claude/hooks.json` | `pythonw.exe`, `git push public main`, `easy_drag=True` blocked before execution |
| Add CLAUDE.md rule: check error-solutions.md on errors | `CLAUDE.md` | Error-solutions file gets consulted when debugging |
| Configure MCP browser tool | `~/.claude/` config | Can search the web and fetch pages from within Claude Code |

**What changes for you:** Secrets aren't plaintext. Known-bad actions get blocked, not just discouraged. Web research works without leaving the agent.

**Estimated time:** ~30 minutes.

---

## Step 2: Memory — Structured Foundation

**What:** Replace flat markdown memory files with a queryable SQLite database. First real code in this repo.

**Build:**
- SQLite schema: `memory_entries`, `enforcement_rules`, `corrections`, `memory_audit_log`
- Migration script: reads all existing memory `.md` files, classifies entries, imports into DB
- `memory-cli query <text>` — full-text search
- `memory-cli add --type rule --content "..." --scope global`
- `memory-cli stats` — counts by type, scope, age
- Unit tests for all CRUD operations

**Done when:**
- `memory-cli stats` shows all existing memory content imported
- `memory-cli query "pywebview"` returns relevant entries
- `pytest tests/` passes

**What changes for you:** Nothing yet. This is the foundation. Markdown files still work. Database runs in parallel.

**Estimated time:** 1 session.

---

## Step 3: Memory — Context Injection

**What:** Relevant memories auto-load based on what you're working on. No more manual "read MEMORY.md" dance.

**Build:**
- Local embedding model (all-MiniLM-L6-v2, 384 dims, runs on CPU)
- Batch-embed all existing entries
- `memory.inject(session_context)` — semantic similarity + scope filtering
- Claude Code `SessionStart` hook wiring
- Relevance threshold (0.6), token budget (2000), max entries (15)

**Done when:**
- Opening a WhisperClick session auto-injects WhisperClick rules
- Opening an unrelated project does NOT inject WhisperClick rules
- Global rules (like `pythonw.exe`) inject everywhere
- Injection completes in under 500ms
- `pytest tests/` passes

**What changes for you:** Sessions start smart. The right context is already there.

**Estimated time:** 1 session.

---

## Step 4: Memory — Enforcement Engine

**What:** Known-bad actions get blocked before they execute. Not warnings in a markdown file — actual gates.

**Build:**
- `memory.enforce(tool, input)` — check against active enforcement rules
- Three pattern types: regex, command match, semantic intent
- Three action types: block, warn, suggest alternative
- Claude Code `PreToolCall` hook wiring
- Audit logging for every enforcement action

**Done when:**
- `memory-cli enforce --tool Bash --input "pythonw.exe src/main.py"` → blocked
- `memory-cli enforce --tool Bash --input "git push public main"` → blocked
- Legitimate commands pass through in under 100ms
- Audit log records every check
- `pytest tests/` passes

**What changes for you:** The agent physically can't do things it's been told not to do.

**Estimated time:** 1 session.

---

## Step 5: Memory — Correction Capture + Pinning

**What:** Corrections stick automatically. Critical rules survive context compression.

**Build:**
- `memory.capture(user_message, context)` — detect correction patterns
- Pattern detection: "No, do X", "Never use Y", "Always do Z", "I already told you..."
- Deduplication: same correction increments count instead of creating duplicate
- Auto-promotion: 3 occurrences → enforcement rule (with user notification)
- `memory.pin(entry_id)` — write to CLAUDE.md structured section
- `PreCompact` hook: pin critical rules before context compression
- Max 20 pinned entries with LRU eviction

**Done when:**
- "No, never use pythonw.exe" → creates correction entry
- Same correction 3x → auto-promotes to enforcement rule
- Pinned rules appear in CLAUDE.md and survive compression
- `pytest tests/` passes

**What changes for you:** Say something once, it sticks. Say it three times, it becomes a wall.

**Estimated time:** 1 session.

---

## Step 6: Memory — Verification + Semantic Retrieval

**What:** Post-action compliance checking. Mid-session memory querying by meaning.

**Build:**
- `memory.verify(action, result)` — check output against rules
- `PostToolCall` hook wiring
- Violation counting + severity auto-escalation
- `memory.query()` as a tool the agent can call mid-session
- Relevance ranking: similarity × recency × confidence
- Negative retrieval: "what was rejected before?"

**Done when:**
- Writing a file containing `pythonw.exe` triggers verification failure
- Agent can query "what do I know about pywebview drag?" mid-session and get ranked results
- Retrieval under 300ms
- `pytest tests/` passes

**What changes for you:** Memory is fully alive — loads itself, enforces itself, captures corrections, survives compression, verifies compliance, and answers questions. All 6 levels working.

**Estimated time:** 1 session.

---

## Step 7: Credential Management

**What:** Encrypted, scoped credential access. The agent never sees raw API keys.

**Build:**
- Credential broker using `keyring` (Windows Credential Manager backend)
- Scoped access: per-project, per-service credential retrieval
- `cred-cli get <service> --scope <project>` for hook/script use
- Output scanner: grep agent output for key patterns, warn if detected
- Integration with memory enforcement (block actions that would expose keys)

**Done when:**
- `cred-cli get openai` returns the key without any `.env` file existing
- Agent sessions work normally with keys fetched from Credential Manager
- Output containing key-like patterns triggers a warning
- `pytest tests/` passes

**What changes for you:** No more `.env` files. Keys stored encrypted in the OS. Agent gets what it needs without seeing the raw value.

**Estimated time:** 1 session.

---

## Step 8: Daemon — Event Bus + Triage

**What:** A background process that listens for events and decides what's worth acting on.

**Build:**
- Event bus: file watcher (watchdog), webhook listener (Flask/FastAPI), timer/scheduler
- Event types: file change, git push, webhook, timer, manual trigger
- Triage layer: rule-based filters + local small model classification
- Priority assignment: critical (wake agent now) → normal (batch) → low (log only)
- Cost estimation: "is this event worth $X of inference?"
- Event deduplication and batching

**Done when:**
- File change in a watched project creates an event
- Triage correctly filters noise (e.g., `.pyc` changes ignored, `.py` changes flagged)
- Events are logged with priority
- Triage runs locally without API calls
- `pytest tests/` passes

**What changes for you:** The system has ears. It knows when things happen, even when you're not talking to it.

**Estimated time:** 1-2 sessions.

---

## Step 9: Daemon — Persistent State + Authority

**What:** The daemon remembers what it was doing between activations and knows what it's allowed to do.

**Build:**
- Persistent state store (extends memory DB): in-progress tasks, pending approvals, recent actions
- Authority tier system:
  - Tier 1 (autonomous): run tests, clean up artifacts, log events
  - Tier 2 (act then notify): fix lint errors, update dependencies
  - Tier 3 (propose and wait): code changes, PR creation
  - Tier 4 (alert only): production deploys, security changes
- Audit log: every daemon action with full context and reasoning
- Integration with memory and credentials

**Done when:**
- Daemon state persists across restarts
- Tier 1 actions execute without prompting
- Tier 3 actions create proposals and wait
- Audit log captures every decision
- `pytest tests/` passes

**What changes for you:** The daemon is alive. It watches, decides, acts within boundaries, and logs everything.

**Estimated time:** 1-2 sessions.

---

## Step 10: Daemon — Full Loop

**What:** Connect everything: event → triage → reason → act → verify → log.

**Build:**
- Full agent loop: event bus → triage → state check → authority check → action → verification → audit
- Reasoning backend integration: call Claude/Codex/Gemini API for complex decisions, local model for simple triage
- Notification system: critical → immediate, normal → digest, low → log
- Graceful shutdown/restart
- Systemd/Windows Service wrapper for auto-start

**Done when:**
- A file change triggers the full loop: detect → triage → reason → act → log
- Daemon runs as a background service that survives terminal close
- Daily digest summarizes what the daemon did overnight
- `pytest tests/` passes

**What changes for you:** First always-on AI agent. It works while you sleep.

**Estimated time:** 1-2 sessions.

---

## Step 11: Browser Integration

**What:** Web research and interaction from within the agent.

**Build:**
- Browser-Use integration (or Playwright fallback)
- Semantic browsing: search, read, extract
- Programmatic automation: fill forms, click, navigate
- Cookie/session management for authenticated sites

**Done when:**
- Agent can search the web and summarize results
- Agent can navigate to a URL and extract structured data
- `pytest tests/` passes

**What changes for you:** The agent can research, test web apps, and interact with web services.

**Estimated time:** 1 session.

---

## Step 12: Sandbox Integration

**What:** Isolated environments for safe experimentation.

**Build:**
- E2B integration (Firecracker microVMs) for cloud sandboxes
- Local fallback: git worktrees + process isolation
- `sandbox create`, `sandbox run`, `sandbox destroy` commands
- Parallel sandbox support for A/B testing approaches
- Graduated promotion: sandbox → verified → local dev

**Done when:**
- `sandbox create` spins up an isolated environment in under 5 seconds
- Agent can run risky commands in sandbox without affecting real system
- Two parallel sandboxes can test different approaches simultaneously
- `pytest tests/` passes

**What changes for you:** The agent can experiment without risk.

**Estimated time:** 1 session.

---

## Step 13: Interactive PTY

**What:** Back-and-forth with running processes.

**Build:**
- PiloTY integration (or custom PTY multiplexer)
- Persistent terminal sessions that survive across tool calls
- Send input / read output loop
- REPL interaction (Python, Node)
- Debugger attachment (pdb, node --inspect)

**Done when:**
- Agent can start a Python REPL, send commands, read output, iterate
- Agent can attach to a running debugger and inspect state
- Sessions persist across multiple tool calls
- `pytest tests/` passes

**What changes for you:** The agent can debug interactively, not just run one-shot commands.

**Estimated time:** 1 session.

---

## Step 14: Desktop Vision + Control

**What:** See and interact with GUI applications.

**Build:**
- Screenshot capture + vision model analysis
- Windows UI Automation API for accessibility tree reading
- Mouse/keyboard control via pyautogui
- Multi-monitor DPI handling (learned the hard way from WhisperClick)
- Click target identification combining vision + accessibility

**Done when:**
- Agent can take a screenshot and describe what's on screen
- Agent can click a specific UI element by description
- Agent can fill in a desktop app form
- Works correctly across multiple monitors with different DPI
- `pytest tests/` passes

**What changes for you:** The agent can use any desktop app, not just the terminal.

**Estimated time:** 2-3 sessions (hardest integration).

---

## Step 15: Audio I/O

**What:** The agent can hear and speak.

**Build:**
- LiveKit Agents integration for real-time audio
- Microphone input → transcription (Whisper)
- Text-to-speech output (ElevenLabs or local)
- Voice activity detection + turn-taking
- Wake word or push-to-talk activation

**Done when:**
- Agent transcribes spoken input in real-time
- Agent responds with synthesized speech
- Turn-taking works naturally (no overlapping)
- `pytest tests/` passes

**What changes for you:** Talk to the agent. It talks back.

**Estimated time:** 1-2 sessions.

---

## Step 16: Multi-Agent Orchestration

**What:** Multiple agents working as a coordinated team.

**Build:**
- Supervisor agent: task decomposition, delegation, monitoring
- Worker agents: scoped context, bounded autonomy, checkpoint/report
- Shared context store (extends memory DB)
- Communication protocol: structured messages between agents
- Conflict resolution: file-level, design-level, priority-level
- Adaptive replanning when reality doesn't match the plan

**Done when:**
- Supervisor decomposes a multi-file task into worker assignments
- Workers execute independently and report back
- Shared context store reflects combined progress
- Conflicts (two workers editing same file) are detected and resolved
- `pytest tests/` passes

**What changes for you:** One agent becomes a team. Complex tasks get parallelized.

**Estimated time:** 2-3 sessions.

---

## Step Status (updated 2026-03-15)

| Step | Name | Status | Tests | Notes |
|------|------|--------|-------|-------|
| 1 | Quick Wins | **Done** | 30 | Hooks, secret scan, gitignore, credential backend |
| 2 | Memory Foundation | **Done** | 30 | SQLite + FTS5, CRUD, migration from markdown |
| 3 | Context Injection | **Done** | 18 | Embeddings, scope filtering, token budget |
| 4 | Enforcement Engine | **Done** | 22 | Regex/command/semantic matching, block/warn/suggest |
| 5 | Correction Capture + Pinning | **Done** | 32 | Pattern detection, dedup, auto-promote, CLAUDE.md pinning |
| 6 | Verification + Retrieval | **Done** | 22 | Post-action compliance, semantic query, negative retrieval |
| 7 | Credential Management | **Done** | 51 | Keyring broker, 14-pattern scanner, redaction, CLI |
| 8 | Daemon Event Bus + Triage | **Done** | 26 | Thread-safe queue, dedup, noise filtering, priority classification |
| 9 | Daemon State + Authority | **Done** | 17 | SQLite state, 4-tier authority, task CRUD, action log |
| 10 | Daemon Full Loop | **Done** | 12 | Event→triage→authority→execute/propose→audit pipeline |
| 11 | Browser Integration | **Done** | 35 | httpx+BS4 engine with Playwright fallback, DuckDuckGo search |
| 12 | Sandbox Integration | **Done** | 17 | Git worktree isolation, create/run/destroy/diff/promote |
| 13 | Interactive PTY | **Done** | 21 | Subprocess sessions, threaded reads, named session manager |
| 14 | Desktop Vision + Control | **Done** | 26 | mss screenshots, pyautogui control, ctypes UI Automation |
| 15 | Audio I/O | **Done** | 31 | sounddevice capture, Whisper transcribe, pyttsx3 TTS, energy VAD |
| 16 | Multi-Agent Orchestration | **Done** | 30 | Supervisor/worker, shared context, file locking, message passing |

---

## Critical Path

```
Step 1  → Quick wins (current setup)                    ✅
Step 2  → Memory foundation                             ✅
Step 3  → Context injection                             ✅
Step 4  → Enforcement engine                            ✅
Step 5  → Correction capture + pinning                  ✅
Step 6  → Verification + semantic retrieval             ✅
Step 7  → Credential management                         ✅
Step 8  → Daemon event bus + triage                     ✅
Step 9  → Daemon state + authority                      ✅
Step 10 → Daemon full loop                              ✅
Step 11 → Browser (can parallel with 8-10)              ✅
Step 12 → Sandbox (can parallel with 11)                ✅
Step 13 → PTY (can parallel with 11-12)                 ✅
Step 14 → Desktop vision (can parallel with 11-13)              ✅
Step 15 → Audio (can parallel with 11-14)                       ✅
Step 16 → Multi-agent orchestration (needs everything above)    ✅
```

**Hard dependencies:** 2→3→4→5→6 (memory chain), 6→8→9→10 (daemon chain), 10→16 (multi-agent needs daemon)

**Everything else is parallelizable.** Steps 7, 11, 12, 13, 14, 15 can happen whenever there's a session available.

---

## Total Estimate

| Block | Steps | Sessions | Status |
|-------|-------|----------|--------|
| Quick wins | 1 | 1 | **Done** |
| Memory (full 6 levels) | 2-6 | 5 | **Done** |
| Credentials | 7 | 1 | **Done** |
| Daemon (full loop) | 8-10 | 3-5 | **Done** |
| Integrations (browser, sandbox, PTY) | 11-13 | 3 | **Done** |
| Desktop vision + Audio | 14-15 | 3-5 | **Done** |
| Multi-agent | 16 | 2-3 | **Done** |
| **Total** | **1-16** | **18-24 sessions** | **16/16 done** |

---

## Known Gaps — All Resolved

- ~~Daemon is a thread, not a Windows Service~~ — **FIXED**: `src/daemon/service.py`
- ~~No daily digest~~ — **FIXED**: `src/daemon/digest.py`
- ~~No real credential migration~~ — **FIXED**: `scripts/migrate-credentials.py`. No .env files exist to migrate.
- ~~No enforcement rules in database~~ — **FIXED**: `scripts/seed-rules.py` seeds 10 rules. Default DB at `~/.claude/memory/memory.db` populated with 578 entries + 10 rules + embeddings.
- ~~Hooks partially wired~~ — **FIXED**: PreToolUse, PostToolUse, PreCompact, SessionStart all wired in `~/.claude/hooks.json`.
- ~~ROADMAP status stale~~ — **FIXED**: All 16 steps marked done.
- **Browser tests are all mocked** — Accepted tradeoff (prevents flaky CI from external site changes).

---

## What's NOT in This Roadmap

- **Model quality.** If the model reasons wrong, better tools don't fix it. Outside our scope.
- **A standalone product with its own UI.** This is infrastructure that wraps around CLI agents.
- **Mobile app.** Android/Pi support comes from platform-agnostic design, not separate builds.
- **Replacing Claude Code.** We're building on top of it, not instead of it.
