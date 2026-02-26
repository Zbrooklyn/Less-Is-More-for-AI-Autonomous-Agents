# Personal Agent Stack — Current Setup vs. 10-Component Framework

## Definition

A personalized assessment that maps the user's actual current setup — Claude Code + Codex + Gemini with shared memory, hooks, WhisperClick, Mission Control, and custom scripts — against the 10-component framework. Identifies what's already partially built, what can be improved with existing tools, and what requires new work. Produces a personal roadmap tailored to this specific environment and workflow.

## Purpose

The "Less Is More" document and the Implementation Roadmap are generic — they apply to any AI agent setup. This document is specific. It asks: given exactly what you have right now, on this machine, with these tools, these projects, and this workflow — how close are you to 100%? What are your personal quick wins? What should you build next?

This is the difference between a general fitness plan and a plan written by a trainer who knows your body, your schedule, and your gym equipment.

---

## Current Tool Inventory

### AI Models
| Tool | Model | Role |
|------|-------|------|
| Claude Code | Opus 4.6 | Primary coding agent — file ops, terminal, sub-agents, web search |
| Codex CLI | OpenAI | Secondary agent — plan execution, parallel work |
| Gemini | Google | Third agent — research, alternative perspectives |

### Shared Memory System (cross-model)
| File | Purpose | Auto-loaded? |
|------|---------|-------------|
| `hot-memory.md` | Confirmed rules, bootstrap phrase | Yes (via hook) |
| `context-memory.md` | Domain/project-specific rules | Manual |
| `corrections-log.md` | Correction tracking + repetition counts | Manual |
| `user-preferences.md` | Communication style, coding prefs | Manual |
| `decisions-log.md` | Rejected alternatives + rationale | Manual |
| `environment.md` | Machine specs, tools, versions | Manual |
| `error-solutions.md` | Known errors → proven fixes | Manual |
| `session-summaries.md` | Past session digests | Manual |
| `patterns.md` | Cross-project tech stack patterns | Manual |
| `business-context.md` | Projects, stakeholders, goals | Manual |
| `project-graph.md` | How projects relate to each other | Manual |
| `archive.md` | Old/inactive patterns | Never |
| `bootstrap-receipts.md` | Proof that models loaded memory | Append-only |
| `memory-verification-probes.md` | Bootstrap phrase rotation schedule | Reference |

### Hooks
| Hook | Trigger | What It Does |
|------|---------|-------------|
| SessionStart | Every new conversation | Reads `hot-memory.md` via `cat` — injects confirmed rules |
| SessionStart (compact) | After context compression | Re-injects bootstrap phrase, key rules, environment basics |

### Active Projects
| Project | Stack | Location |
|---------|-------|----------|
| WhisperClick V3 | Python, pywebview, PySide6, pystray, faster-whisper, OpenAI API | `projects/WhisperClick V3/` |
| Mission Control | Python, FastAPI, uvicorn | `projects/mission-control/` |
| HTML Recorder | Browser companion to WhisperClick | `projects/html-recorder/` |
| AI Agent Benchmark | Multi-agent testing framework | `projects/ai-agent-benchmark/` |

### Infrastructure
| Tool | Purpose |
|------|---------|
| rclone bisync | Dropbox sync for AI_Projects |
| PowerShell scripts | rclone management, session cleanup, system automation |
| Node.js scripts | Session renaming, categorization, plan cleanup |
| Git (multi-remote) | Private (origin) + public (public) repos for WhisperClick |
| `sync_public.py` | Strips private files and force-pushes to public repo |
| Playwright (npx) | Browser automation (available, not deeply integrated) |

### Hardware Constraints
| Constraint | Impact |
|-----------|--------|
| Single laptop (i7-1065G7, 15.7GB RAM) | No cloud infrastructure, limited parallel workloads |
| No GPU | Local AI inference limited, relies on API-based models |
| Budget-conscious | Prefer efficient models (Haiku for triage), minimize API costs |

---

## Per-Component Scoring

| # | Component | Generic Status | Your Status | Notes |
|---|-----------|---------------|-------------|-------|
| 1 | Terminal + structured tools | **HAVE** | **HAVE** | Claude Code's Read/Write/Edit/Grep/Glob/Bash fully functional. Codex and Gemini have equivalent terminal access. |
| 2 | Web browser | **PARTIAL** | **PARTIAL** | WebFetch/WebSearch available in Claude Code. Playwright installed but not integrated into agent workflow. No MCP browser configured. |
| 3 | Desktop vision + control | **DON'T HAVE** | **DON'T HAVE** | No desktop automation configured. pyautogui/pywinauto not installed. No computer use integration. |
| 4 | Memory with teeth | **PRIMITIVE** | **PRIMITIVE+** | Better than average — 14 memory files, cross-model shared memory, bootstrap verification via hooks, post-compaction re-injection hook. Still manual loading for most files, no semantic retrieval, no automatic capture, no enforcement beyond post-it notes. |
| 5 | Stateful agent daemon | **DON'T HAVE** | **DON'T HAVE** | No daemon. Agent dies when conversation closes. Some infrastructure exists (rclone bisync runs on schedule, PowerShell scripts for monitoring) but nothing AI-driven. |
| 6 | Interactive PTY | **DON'T HAVE** | **DON'T HAVE** | One-shot Bash only. Same as everyone else. |
| 7 | Audio/video I/O | **DON'T HAVE** | **TINY EDGE** | WhisperClick V3 IS an audio tool — it captures microphone audio and transcribes via Whisper/OpenAI. But this capability isn't available to the AI agents themselves. The agents can't hear or speak. |
| 8 | Sandboxed execution | **PRIMITIVE** | **PRIMITIVE** | Git worktrees via Claude Code Task tool. Docker not configured. No instant cloning, no concurrent sandboxes. |
| 9 | Credential management | **PRIMITIVE** | **PRIMITIVE** | API keys in `.env` files and environment variables. No vault, no scoped access, no rotation, no output scanning. |
| 10 | Multi-agent orchestration | **PRIMITIVE** | **PRIMITIVE+** | Better than average — three models (Claude, Codex, Gemini) with shared memory files, shared CLAUDE.md/CODEX.md/GEMINI.md contracts, bootstrap verification. But no real coordination — models work independently, no shared context during sessions, no conflict resolution, no supervisor. |

### Your Score vs. Generic

| Status | Generic Count | Your Count | Difference |
|--------|--------------|------------|------------|
| **HAVE** | 1 | 1 | Same |
| **PARTIAL** | 1 | 1 | Same |
| **PRIMITIVE+** | 0 | 2 | You're ahead on memory and multi-model coordination |
| **PRIMITIVE** | 4 | 2 | Two upgraded to PRIMITIVE+ |
| **TINY EDGE** | 0 | 1 | WhisperClick gives you audio infrastructure others don't have |
| **DON'T HAVE** | 4 | 3 | One upgraded to TINY EDGE |

**You're slightly ahead of the generic baseline**, mainly because of your shared memory system and multi-model setup. But the big gaps (desktop control, daemon, interactive PTY) are the same as everyone else.

---

## Gap Analysis

### Where You're Strongest
1. **Memory system** — 14 structured files, cross-model sharing, bootstrap verification, post-compaction re-injection. Most AI users have zero memory infrastructure. You have the best possible version of the primitive approach.
2. **Multi-model coordination** — Three models reading from shared memory with shared contracts. No one else is doing this. It's manual and fragile, but the architecture is there.
3. **Terminal + tools** — Fully functional. No gaps.

### Where You're Weakest
1. **Credential management** — API keys in `.env` files on a machine running three different AI models. Any model could accidentally expose a key in output. No scoping, no rotation, no scanning. This is your highest-risk gap.
2. **Stateful daemon** — Everything dies when you close the conversation. Your rclone scripts run on schedule but with zero AI intelligence. Massive missed opportunity given the infrastructure you already have.
3. **Desktop vision + control** — Complete blind spot. Can't interact with any GUI app.

### Where You Have Untapped Infrastructure
1. **WhisperClick → Audio I/O** — You already built a microphone-to-transcription pipeline. The infrastructure for audio input exists in your own project. It's just not connected to the AI agents.
2. **Playwright → Browser** — Installed and available via npx. Not configured as an MCP tool or integrated into the agent workflow.
3. **rclone + PowerShell scripts → Daemon foundations** — You have scheduled scripts, monitoring, and sync infrastructure. These could be the event sources for a lightweight daemon.

---

## Quick Wins (this week, no new code)

| # | Action | Component | Effort | Impact |
|---|--------|-----------|--------|--------|
| 1 | **Add MCP browser server** to Claude Code settings | Web browser | 10 min | Upgrades from PARTIAL to near-HAVE for web research |
| 2 | **Add enforcement hooks** for your top 3 dangerous actions (`pythonw.exe`, `git push public main`, committing `.env` files) | Memory | 30 min | Turns 3 post-it notes into actual guardrails |
| 3 | **Move API keys to Windows Credential Manager** and access via `cmdkey` or Python `keyring` | Credentials | 1 hour | Eliminates plaintext credential storage |
| 4 | **Add a pre-commit hook** that scans for exposed secrets | Credentials | 30 min | Prevents accidental key commits |
| 5 | **Create a CLAUDE.md rule** requiring models to check `error-solutions.md` when hitting errors | Memory | 5 min | Makes existing memory file actually get used |

## Medium-Term Builds (1-4 weeks, new code needed)

| # | Action | Component | Effort | Impact |
|---|--------|-----------|--------|--------|
| 1 | **Build a lightweight daemon** using Python + watchdog + scheduled tasks — monitors file changes, runs tests, alerts on failures | Daemon | 1-2 weeks | First always-on AI capability. Start with Tier 1 actions only (tests, cleanup, reporting) |
| 2 | **Connect WhisperClick's audio pipeline to Claude** — pipe transcription results into Claude Code as context | Audio I/O | 1 week | First audio input for an AI agent, using infrastructure you already built |
| 3 | **Build semantic memory retrieval** using embeddings + a small vector store (ChromaDB or similar) over your 14 memory files | Memory | 1 week | Transforms memory from "hope the right file was loaded" to "search by meaning" |
| 4 | **Integrate Playwright as an MCP tool** with common browser automation recipes | Browser | 1 week | Full programmatic browser control from within Claude Code |
| 5 | **Add automatic correction capture** — a hook that detects "No, do it this way" patterns and appends to corrections-log.md | Memory | 2-3 days | Eliminates manual correction logging |

## Long-Term Aspirations (1+ months, significant infrastructure)

| # | Action | Component | Effort | Impact |
|---|--------|-----------|--------|--------|
| 1 | **Full desktop vision + control** via pyautogui + Windows UI Automation API, integrated as Claude Code tools | Desktop | 2-4 weeks | Unlocks all GUI app interaction |
| 2 | **Multi-agent supervisor** that coordinates Claude, Codex, and Gemini on complex tasks with shared context and conflict resolution | Multi-agent | 4-6 weeks | Turns three independent models into a team |
| 3 | **Full daemon with event bus** — file watchers, GitHub webhooks, system metrics, triage layer, authority tiers, audit log | Daemon | 4-6 weeks | Always-on intelligent automation |
| 4 | **Sandboxed execution** using Windows Sandbox or Docker with instant cloning and parallel experiments | Sandbox | 2-3 weeks | Safe experimentation for daemon and manual work |

---

## Cross-Model Coordination Assessment

### What Works Today
- Shared memory files that all three models can read
- Shared contracts (CLAUDE.md, CODEX.md, GEMINI.md) defining behavior
- Bootstrap verification proving memory was loaded
- Post-compaction hook re-injecting critical rules after context compression

### What Doesn't Work
- **No real-time coordination** — models work in separate sessions, no awareness of each other's active work
- **No shared session state** — if Claude is working on a file, Codex doesn't know
- **Memory is still manual** — models are told to read files, not forced to. Skip rate is non-zero
- **No conflict prevention** — Claude and Codex could edit the same file in separate sessions
- **No task handoff protocol** — moving work between models requires the human to copy-paste context

### What Would Fix It
1. A shared task board (markdown file or SQLite DB) that tracks what each model is currently working on
2. File locking — when one model is editing a file, others see "locked by Claude, session X"
3. Automatic context export — when finishing a session, the model writes a handoff summary that the next model auto-loads
4. A lightweight coordinator script that assigns tasks to models based on their strengths (Opus for architecture, Sonnet for routine coding, Haiku for formatting)

---

## Personal Priority Ranking

Based on your actual workflow — freelance web development, WhisperClick product development, multi-model AI setup:

| Priority | Component | Why |
|----------|-----------|-----|
| **1** | Credential management (quick wins) | Highest risk. Three AI models + plaintext keys = disaster waiting to happen. Fix this first. |
| **2** | Memory enforcement hooks | You already have the memory files. Adding 3-5 hooks turns suggestions into guardrails. Highest ROI. |
| **3** | MCP browser integration | You do web development. Full browser access from the agent transforms your daily workflow. |
| **4** | Lightweight daemon | Your rclone and PowerShell scripts already run on schedule. Adding AI intelligence to them is a natural next step. |
| **5** | Semantic memory retrieval | 14 memory files is a lot. Search by meaning instead of hoping the right one was loaded. |
| **6** | Audio pipeline connection | WhisperClick is YOUR product. Connecting its audio to your AI agents is unique to you — no one else has this. |
| **7** | Multi-agent coordination | Three models working as a team instead of three models working alone. Big impact but big build. |
| **8** | Desktop vision + control | Not critical for web development workflow. Nice to have. |
| **9** | Sandboxed execution | Matters more once the daemon is running. Build after daemon. |
| **10** | Interactive PTY | Real but rare need in your workflow. Lowest priority. |
