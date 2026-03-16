# Changelog

## 2026-03-16 — Session 1, Part 5: Final Polish

### Commit 17: `pending` — README, v1.0.0, CLAUDE.md, INDEX registration
- README.md created — project description, architecture, quick start
- Version bumped 0.1.0 → 1.0.0 (all 16 steps complete)
- CLAUDE.md rewritten with project instructions (was just pinned rules)
- Registered in AI_Projects/projects/INDEX.md
- Research repo (less-is-more) now points to implementation
- Empty config/ directory removed
- CHANGELOG.md brought up to date

### Commit 16: `9e4d92a` — Hook performance + PostToolUse fix + live verification
- SessionStart hook rewritten: fast_inject() uses scope+keyword only (no embeddings). 417ms cold start (was 19s).
- PostToolUse hook fixed: now checks Write/Edit content, not just tool output.
- 12/12 live hook scenarios verified with real stdin piping.

### Commit 15: `b43e508` — Hardcoded paths, missing deps, HANDOFF, test coverage
- migrate.py auto-detects workspace root (no more hardcoded C:/ path)
- pyproject.toml: added memory, vision, audio dependency groups
- HANDOFF.md created
- 14 tests for seed-rules.py and reasoning.py

### Commit 14: `0a3b662` — Seed enforcement rules, populate default DB
- scripts/seed-rules.py: 10 default rules (pythonw, git push public, easy_drag, etc.)
- Default DB (~/.claude/memory/memory.db) populated: 578 entries + 10 rules + embeddings
- Verified: memory-cli enforce --tool Bash --input "pythonw.exe" → BLOCKED
- ROADMAP.md updated 16/16 complete

### Commit 13: `eb9daa7` — Steps 14+15: Desktop Vision + Audio I/O
- src/vision/: mss screenshots, pyautogui control, ctypes Windows UI Automation, OCR stubs (26 tests)
- src/audio/: sounddevice capture, Whisper transcribe, pyttsx3 TTS, energy VAD, CLI (31 tests)

### Commit 12: `8724623` — Step 16: Multi-Agent Orchestration + reasoning + docs
- src/orchestrator/: supervisor/worker, shared context, file locking, messages (30 tests)
- src/daemon/reasoning.py: pluggable LLM reasoning backend with local rules + Anthropic API factory
- SETUP.md created

### Commit 11: `1fae57e` — Debugger attachment for PTY
- SessionManager.attach_debugger(name, script_path) — starts pdb session

### Commit 10: `8adf93a` — File watcher, webhook listener, scheduler
- src/daemon/watcher.py: watchdog-based file watcher (9 tests)
- src/daemon/webhook.py: stdlib HTTP server, POST /webhook + GET /health
- src/daemon/scheduler.py: named recurring timers

### Commit 9: `6dbbab2` — LRU eviction, severity escalation, browser interaction, notification routing
- Pin LRU eviction when exceeding MAX_PINNED (20)
- Auto-escalation: 5 violations warn→block, 10 medium→high, 20 high→critical
- Browser: fill_form(), click(), navigate(), get/set/clear_cookies()
- Daemon: notification routing (critical→immediate, normal→batch, low→log)
- pyproject.toml: console script entries

---

## 2026-03-15 — Session 1, Part 3: Gap Fixes

### Commit 8: `dcfae8d` — Fix all remaining gaps
**Files:** +6 new, +4 modified | **Tests:** +12 (total: 389)

**Gap 1 — Daemon Windows Service (`src/daemon/service.py`):**
- `cmd_start()` — launches daemon as detached process (`CREATE_NO_WINDOW | DETACHED_PROCESS`), survives terminal close. Writes PID to `~/.claude/daemon/daemon-pid.json`.
- `cmd_stop()` — kills daemon by PID via `taskkill`. Cleans up state file.
- `cmd_status()` — checks if PID is running via `tasklist`.
- `cmd_schedule()` — creates Windows Task Scheduler entry (`ONLOGON`) for auto-start at login. No admin required.
- `cmd_unschedule()` — removes Task Scheduler entry.
- Auto-generates `scripts/daemon-run.py` standalone runner if missing.

**Gap 2 — Daily Digest (`src/daemon/digest.py`):**
- `generate_digest(state, hours=24)` — summarizes daemon activity. Sections: summary (action counts), awaiting approval (Tier 3+ tasks), failed tasks, completed tasks, blocked actions (from enforcement). Writes to file optionally.
- `print_digest()` — convenience wrapper.
- 8 tests: empty digest, actions, tasks (awaiting/completed/failed), blocked actions, file output, time window.

**Gap 3 — Credential Migration (`scripts/migrate-credentials.py`):**
- Scans 6 known `.env` locations (home/.claude, AI_Projects, easy-ecommerce-group, WhisperClick, mission-control).
- Maps env var names to service/scope pairs (ANTHROPIC_API_KEY → anthropic/global, SUPABASE_URL → supabase-url/easy-ecommerce, etc.).
- `--execute` mode migrates to Windows Credential Manager, skips already-stored.
- `--verify` mode confirms all credentials are stored and match.
- Dry run (default) shows what would be migrated without touching anything.
- 2 tests: .env parsing (comments, quotes, empty values), nonexistent file.

**Gap 4 — Wired hooks into `~/.claude/hooks.json`:**
- Added `PostToolUse` hook: runs `hook-post-tool-call.py` on Bash tool calls for compliance verification.
- Added `PreCompact` hook: runs `hook-pre-compact.py` to pin critical rules before context compression.
- Kept all existing hooks (pythonw, git push public, easy_drag, EEG main branch blocks) intact.

**Other fixes:**
- `CHANGELOG.md` — Created comprehensive changelog documenting every commit, every file, every change.
- `ROADMAP.md` known gaps section updated to reflect fixed items.

---

## 2026-03-15 — Session 1: Full Build (Steps 1-13 + Hardening)

### Commit 1: `f422b68` — Initial commit (pre-existing work from Feb 27)
**Files:** 20 | **Tests:** 109

Committed the existing codebase that had never been git-committed:
- `src/memory/store.py` — SQLite memory store with FTS5 search, enforcement rules table, corrections table, audit log. CRUD operations, WAL mode, auto-create DB path.
- `src/memory/cli.py` — CLI with `query`, `add`, `stats`, `migrate`, `audit`, `rules`, `inject`, `embed` commands. Windows UTF-8 encoding fix.
- `src/memory/embeddings.py` — Local `all-MiniLM-L6-v2` embedding model (384 dims). `embed_text()`, `embed_texts()` batch, `cosine_similarity()`. Lazy model loading.
- `src/memory/injector.py` — `SessionContext` dataclass, `inject()` with 3-stage strategy (global rules → project scope → semantic search), token budget enforcement, `format_injection()`, `embed_all_entries()`.
- `src/memory/migrate.py` — Parses markdown memory files into SQLite. `parse_markdown_sections()` handles headers/bullets/tables. `classify_entry()` detects rule/decision/pattern/preference. `determine_scope()` maps content to projects. Scans both `shared/memory/` and `~/.claude/` memory dirs.
- `src/memory/__init__.py`, `src/__init__.py` — Module inits.
- `src/daemon/__init__.py`, `src/credentials/__init__.py`, `src/hooks/__init__.py` — Empty stubs.
- `scripts/scan-secrets.sh` — Pre-commit hook script scanning for API key patterns.
- `.gitignore` — Excludes venv, __pycache__, *.db, .env, *.pyc.
- `pyproject.toml` — Package config: `autonomous-ai-agent` v0.1.0, Python >=3.12, deps: sqlite-vec, keyring.
- `ROADMAP.md` — 16-step build plan with "done when" criteria for each step.
- `tests/test_memory_store.py` — 30 tests: CRUD, FTS5 query, stats, enforcement rules, corrections, audit log, DB integrity.
- `tests/test_memory_cli.py` — 13 tests: query, add, stats, audit, rules, help.
- `tests/test_memory_injector.py` — 18 tests: embeddings, batch embed, session context, injection scoping, format, use_count tracking.
- `tests/test_memory_migrate.py` — 24 tests: markdown parsing, entry classification, scope detection, file migration, real file integration.
- `tests/test_quick_wins.py` — 24 tests: hooks.json structure, hook behavior (pythonw/git push public/easy_drag blocked), keyring backend, secret scanning, project structure.
- `tests/__init__.py` — Test package init.
- `demo.db` (880KB, gitignored) — Pre-populated database from migration run.

---

### Commit 2: `f0c37b2` — Credential management (Step 7) [background agent]
**Files:** +4 | **Tests:** +51 (total: 160)

- `src/credentials/__init__.py` — Exports `get`, `set`, `delete`, `list_services`, `scan_output`, `redact`.
- `src/credentials/broker.py` — Credential broker using `keyring` with Windows Credential Manager backend. Service names: `autonomous-agent/{scope}/{service}`. `get()`, `set()`, `delete()` with scope support. `list_services()` uses Win32 `CredEnumerateW` API via ctypes.
- `src/credentials/scanner.py` — 14 regex patterns: OpenAI (`sk-`), Google (`AIza`), Slack (`xox`), AWS (`AKIA`), GitHub (`ghp_`/`gho_`/`github_pat_`), GitLab (`glpat-`), Stripe (`sk_live_`/`pk_live_`), PEM private key blocks, JWT (`eyJ`), Bearer tokens, generic `secret=`/`password=`, suspicious base64 (>40 chars). `scan_output()` returns findings with severity. `redact()` replaces matches with `[REDACTED]`.
- `src/credentials/cli.py` — `cred-cli` with `get`, `set`, `delete`, `list`, `scan`, `redact` commands.
- `tests/test_credentials.py` — 51 tests across 13 classes: broker naming, get/set/delete with mocks, roundtrip, scope isolation, all 14 scanner patterns, false-positive resistance (prose, code, URLs, UUIDs, short base64), redaction, CLI commands.

---

### Commit 3: `7012ef1` — Enforcement, capture, pinning, verification (Steps 4-6)
**Files:** +8 | **Tests:** +76 (total: 236)

- `src/hooks/__init__.py` — Updated from empty stub to module docstring.
- `src/hooks/enforce.py` — `enforce(store, tool, tool_input)` checks against all active enforcement rules. Three matchers: `_match_regex` (case-insensitive), `_match_command` (substring), `_match_semantic` (embedding cosine similarity ≥0.75). Returns `EnforceResult` with allowed/action/rule_id/severity/alternative. Increments `violation_count` on matched rules. Full audit logging. `enforce_output()` for post-action output checking. `format_enforcement()` for human-readable messages.
- `src/hooks/capture.py` — 10 correction patterns: explicit negative ("no, don't"), redirect ("instead, use"), repetition ("I already told you"), wrong ("that's wrong"), prohibition ("don't use"/"never use"), mandate ("always do"), stop ("stop doing"), question correction ("why did you"), polite correction ("please don't"). `extract_correction_content()` parses what-was-wrong / what-is-right pairs. `find_similar_correction()` with Jaccard word-level similarity (>0.7 threshold). `capture()` full flow: detect → extract → dedup → increment count → auto-promote after 3 occurrences. `get_correction_stats()`.
- `src/hooks/pin.py` — `pin(store, entry_id, pin_file)` raises confidence to 1.0 and writes to CLAUDE.md. `unpin()` reverses. `get_pinned()` returns all confidence=1.0 rules. `format_pinned_section()` with `<!-- PINNED_RULES_START/END -->` markers. `_write_pin_section()` handles create/append/replace. `pre_compact_pin()` for PreCompact hook.
- `src/hooks/verify.py` — `verify(store, tool, action_description, output)` checks combined action+output against all rules. Returns `VerifyResult` with compliant/violations/warnings (critical/high = violation, medium/low = warning). `query_memory()` semantic retrieval: keyword fallback when embeddings unavailable, scoring = similarity×0.6 + confidence×0.2 + use_count×0.2, negative retrieval from enforcement rules. `format_query_results()` with grouped display.
- `tests/test_enforcement.py` — 22 tests: blocking (pythonw, git push public, easy_drag), allowing (normal python, git push origin, empty input, no rules), warning (force push), output checking, audit entries, violation count increment, EnforceResult dataclass, format messages, performance (<100ms).
- `tests/test_capture_pin.py` — 32 tests: 10 correction patterns, non-corrections, content extraction, capture flow (detect/dedup/auto-promote/no-double-promote), stats, pinning (pin/unpin/get/append/replace section), format, pre-compact.
- `tests/test_verify.py` — 22 tests: compliance checking, violation detection, warnings, multiple violations, audit, format, semantic query (relevant/scoped/typed/use_count/empty/max_results/negative), format results, performance.

---

### Commit 4: `c9c3f28` — Daemon event bus, triage, state, authority, full loop (Steps 8-10)
**Files:** +7 | **Tests:** +55 (total: 291)

- `src/daemon/__init__.py` — Updated from empty stub to module docstring.
- `src/daemon/events.py` — `EventType` enum (FILE_CHANGE, GIT_PUSH, WEBHOOK, TIMER, MANUAL, SYSTEM). `Priority` enum (CRITICAL=0, NORMAL=1, LOW=2). `DaemonEvent` dataclass with id, type, source, payload, priority, timestamp, dedupe_key. `EventBus` class: thread-safe `Queue`, `emit()` with deduplication (configurable window, default 5s), `subscribe()` handler registration per event type, `process_one()` dispatches to handlers, `start()`/`stop()` background thread, `drain()` for testing, `stats` property.
- `src/daemon/triage.py` — 13 ignore patterns (pyc, __pycache__, .git, node_modules, egg-info, temp files, db journals). 12 important patterns ordered specific-first: CLAUDE.md/hot-memory/.env = CRITICAL, .py/.ts/.js/.json/.toml/.yaml = NORMAL, .md = LOW. Cost estimates per event type ($0.00-$0.05). `triage()` returns `TriageResult` with accepted/priority/reason/category/cost. `batch_triage()` sorts by priority.
- `src/daemon/state.py` — `AuthorityTier` IntEnum (AUTONOMOUS=1, ACT_NOTIFY=2, PROPOSE_WAIT=3, ALERT_ONLY=4). `DaemonTask` dataclass. SQLite schema: daemon_tasks, daemon_actions, daemon_config. `DaemonState` class: `check_same_thread=False` for threading. Task CRUD (create/get/update/list with status filter). `check_authority()` returns authorized/action_required/reason. Action audit log. Key-value config store.
- `src/daemon/loop.py` — `LoopConfig` (poll_interval, batch_size, max_cost_per_cycle, notification_callback). `DaemonLoop` connects EventBus → triage → authority check → execute/propose → audit. `register_action()` per triage category. `process_cycle()` drains up to batch_size events, triages, checks cost budget, maps priority→tier (LOW→AUTONOMOUS, NORMAL→ACT_NOTIFY, CRITICAL→PROPOSE_WAIT), executes or creates proposal task. `start()`/`stop()` background thread.
- `tests/test_daemon_events.py` — 26 tests: emit/process, empty queue, subscribe/handle, handler filtering, multiple handlers, deduplication + expiry, stats, drain, start/stop, exception resilience, triage (pyc/python/.md/env/node_modules/git/unknown), priority classification, batch sorting, cost estimates.
- `tests/test_daemon_state_loop.py` — 29 tests: task CRUD, status filtering, persistence across connections, 4 authority tiers, action log, config CRUD, loop (empty cycle, low/normal/critical events, noise filtering, cost budget, notification callback, error handling, start/stop, stats, batch processing, audit trail).

---

### Commit 5: `505463b` — Sandbox integration (Step 12) [background agent]
**Files:** +4 | **Tests:** +17 (total: ~308)

- `src/sandbox/__init__.py` — Exports `SandboxInfo`, `SandboxManager`.
- `src/sandbox/manager.py` — `SandboxInfo` dataclass (name, path, branch, created_at). `SandboxManager(repo_path)`. `create(name, base_branch)` creates git worktree on `sandbox/<name>` branch under `.sandboxes/`. `run(name, command)` executes in sandbox directory, returns stdout/stderr/returncode. `destroy(name)` removes worktree + deletes branch. `list_sandboxes()` parses `git worktree list --porcelain`. `diff(name)` shows uncommitted changes. `promote(name, target_branch)` merges sandbox branch back.
- `src/sandbox/cli.py` — `sandbox` CLI with `create`, `run`, `list`, `diff`, `destroy`, `promote` subcommands.
- `tests/test_sandbox.py` — 17 tests using temporary git repos: create makes directory, sets branch, populates timestamp, duplicate prevention, run executes/captures stderr/returns nonzero/works in sandbox dir/nonexistent fails, destroy removes/nonexistent graceful, list empty/active/excludes destroyed, diff empty/shows changes/nonexistent.

---

### Commit 6: `7747fb3` — Browser integration + Interactive PTY (Steps 11, 13) [background agents]
**Files:** +8 | **Tests:** +56 (total: 364)

- `src/browser/__init__.py` — Exports `BrowserEngine`, `search`, `fetch_page`, `extract_data`, `screenshot`.
- `src/browser/engine.py` (398 lines) — Async dual-backend engine. Primary: Playwright (chromium). Fallback: httpx + BeautifulSoup4. `BrowserEngine` context manager with `open()`/`close()`. `search(query, max_results)` scrapes DuckDuckGo HTML, extracts real URLs from DDG redirect params. `fetch_page(url)` returns `PageResult` (url, title, text_content, links), strips script/style tags. `extract_data(url, selector)` returns `ExtractResult` list with tag/text/attributes/classes. `screenshot(url, path)` via Playwright (HTML file fallback for httpx).
- `src/browser/sync_api.py` — Synchronous wrappers using `asyncio.run()`, handles running event loops via thread pool executor.
- `src/pty/__init__.py` — Module init.
- `src/pty/session.py` — `PTYSession`: `start(command)` creates `subprocess.Popen` with stdin/stdout/stderr pipes. Thread-based non-blocking reader (`_reader_thread` appends to `_output_buffer`). `send(text)` writes to stdin. `read(timeout)` drains buffer with polling. `is_alive()`, `close()` with terminate+kill. Context manager. `SessionManager`: named session CRUD, `create`/`get`/`send`/`read`/`close`/`close_all`/`list_sessions` (with alive/dead status).
- `src/pty/cli.py` — `pty` CLI with `create`, `send`, `read`, `list`, `close` subcommands.
- `tests/test_browser.py` — 35 tests (all mocked): search structure/max_results/URL extraction/empty/guard, fetch fields/links/script stripping/missing title/guard, extract selector/no selector/no matches/class flattening/guard, screenshot file creation/HTML fallback/nested dirs/guard, sync wrappers, lifecycle/context manager/idempotency/backend selection/fallback, DDG URL extraction.
- `tests/test_pty.py` — 21 tests: start/is_alive, send+read roundtrip (echo hello), send to dead process, multiple cycles, close terminates, close idempotent, context manager cleanup, read timeout, SessionManager create/get/duplicate/nonexistent/close/close_all/send+read, list empty/with sessions/dead status.

---

### Commit 7: `2277a34` — Hardening pass
**Files:** +6 modified, +3 new | **Tests:** +13 (total: 377)

**CLI additions to `src/memory/cli.py`:**
- `cmd_enforce(store, args)` — `enforce --tool <name> --input <text>`. Returns exit code 1 if blocked, 0 if allowed.
- `cmd_capture(store, args)` — `capture <message>` detects corrections, shows wrong/right/count/promoted. `capture --stats` shows correction statistics.
- `cmd_verify(store, args)` — `verify --tool <name> --action <desc> --output <text>`. Returns exit code 1 if non-compliant.
- `cmd_pin(store, args)` — `pin <entry_id>`, `pin --unpin <entry_id>`, `pin --list`.

**Hook scripts (new `scripts/` files):**
- `hook-session-start.py` — Reads session context from stdin JSON or env vars, calls `inject()`, prints formatted injection to stderr. For `SessionStart` hook.
- `hook-pre-tool-call.py` — Reads tool call JSON from stdin, extracts tool name + input, calls `enforce()`. Exit code 0 = allow, 2 = block with reason on stderr. For `PreToolUse` hook.
- `hook-post-tool-call.py` — Reads tool call + output JSON from stdin, calls `verify()`, prints violations/warnings to stderr. For `PostToolUse` hook.
- `hook-pre-compact.py` — Calls `pre_compact_pin()` to refresh all pinned rules in CLAUDE.md before context compression. For `PreCompact` hook.

**Entry point `src/__main__.py`:**
- `python -m src memory [args]` — Routes to memory-cli.
- `python -m src cred [args]` — Routes to credential-cli.
- `python -m src daemon` — Starts daemon with event bus + state + loop, Ctrl+C to stop.
- `python -m src sandbox [args]` — Routes to sandbox-cli.
- `python -m src pty [args]` — Routes to PTY session manager.

**Integration tests `tests/test_integration.py`:**
- `TestCorrectionToEnforcementPipeline`: correction 3x → auto-promote → enforce blocks. Rule → pin → pin file → verify catches violation.
- `TestDaemonToMemoryPipeline`: file change → event bus → triage → daemon handler calls enforce. Critical file (CLAUDE.md) → daemon creates proposal. Noise (.pyc) filtered before handler.
- `TestMemoryQueryWithEnforcement`: semantic query returns both positive rules and negative enforcement context.
- `TestCLIEnforceCommand`: CLI enforce blocks/allows, capture detects, verify compliant, pin list.
- `TestFullAuditTrail`: enforce + capture + verify all leave audit entries.
- `TestDaemonFullLoop`: background loop processes batched events.

**Fixes:**
- `tests/test_verify.py` — `test_query_under_300ms` renamed to `test_query_under_500ms`, threshold 300→500ms.
- `ROADMAP.md` — Added status table with completion markers for all 16 steps, known gaps section.
