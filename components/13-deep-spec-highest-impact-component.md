# Deep Spec — Memory With Teeth

## Why Memory

The Implementation Roadmap (doc 11) identifies Memory With Teeth as the highest impact-to-effort component in the entire framework. The Agent Framework Scorecard (doc 12) confirms it — only 3 of 12 tools reach even PARTIAL on memory, making it the most underserved high-impact component in the market.

Memory is the foundation:
- The **stateful agent daemon** depends on it — a daemon without persistent state is a cron job
- **Multi-agent orchestration** depends on it — the shared context store is memory applied to teams
- **Every other component benefits from it** — learned patterns, error avoidance, user preferences

Building memory first means every session after it ships is better. Every component built after it is stronger. There is no competing candidate for "build this first."

## What This Document Is

Not "what memory should do" — that's in the component doc (04-memory-with-teeth.md). This is **how to build it.** Architecture, data models, API design, tech stack, implementation phases, integration points, testing strategy, and estimated effort.

A developer — or an AI agent — should be able to pick up this spec and start building.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     AGENT SESSION                            │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │  Agent    │  │ Context  │  │ Enforce  │  │ Correction │  │
│  │  Action   │──│ Injector │  │ Engine   │  │ Detector   │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └─────┬──────┘  │
│       │              │              │               │         │
└───────┼──────────────┼──────────────┼───────────────┼─────────┘
        │              │              │               │
        ▼              ▼              ▼               ▼
┌─────────────────────────────────────────────────────────────┐
│                    MEMORY API LAYER                           │
│                                                              │
│  query()  inject()  enforce()  capture()  verify()  pin()   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    MEMORY STORE                               │
│                                                              │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐               │
│  │  SQLite   │  │  Vector   │  │  Pinned   │               │
│  │  (entries,│  │  Index    │  │  Rules    │               │
│  │   rules,  │  │  (embeds) │  │  (CLAUDE  │               │
│  │   logs)   │  │           │  │   .md)    │               │
│  └───────────┘  └───────────┘  └───────────┘               │
└─────────────────────────────────────────────────────────────┘
```

### Six Subsystems

| # | Subsystem | Role | Maps to Level |
|---|-----------|------|---------------|
| 1 | **Context Injector** | Loads relevant memory before the agent starts reasoning | Level 1: Automatic Injection |
| 2 | **Enforcement Engine** | Intercepts actions and blocks known-bad patterns | Level 2: Enforcement Hooks |
| 3 | **Semantic Retriever** | Finds relevant past experience by meaning, not filename | Level 3: Semantic Retrieval |
| 4 | **Correction Detector** | Watches conversation for corrections and extracts rules | Level 4: Automatic Capture |
| 5 | **Pin Manager** | Keeps critical rules outside the conversation context | Level 5: Compression-Proof |
| 6 | **Verification Checker** | Confirms the agent followed its own rules after acting | Level 6: Behavioral Verification |

---

## Data Models

### Memory Entry

The atomic unit of memory. Everything stored — rules, corrections, preferences, facts, patterns — is a memory entry.

```sql
CREATE TABLE memory_entries (
    id          TEXT PRIMARY KEY,        -- UUID
    content     TEXT NOT NULL,           -- The actual memory (human-readable)
    type        TEXT NOT NULL,           -- 'rule' | 'correction' | 'preference' | 'fact' | 'pattern' | 'decision'
    scope       TEXT NOT NULL DEFAULT 'global',  -- 'global' | 'project:<name>' | 'file:<path>'
    source      TEXT NOT NULL,           -- Where it came from: 'user_correction' | 'auto_detected' | 'manual' | 'promoted'
    confidence  REAL NOT NULL DEFAULT 0.5,  -- 0.0 to 1.0 — how certain this rule is
    tags        TEXT,                    -- JSON array of tags for filtering
    created_at  TEXT NOT NULL,           -- ISO 8601 timestamp
    updated_at  TEXT NOT NULL,           -- ISO 8601 timestamp
    last_used   TEXT,                    -- Last time this memory was injected or queried
    use_count   INTEGER DEFAULT 0,      -- How many times this has been injected
    violation_count INTEGER DEFAULT 0,  -- How many times this rule was violated (for rules)
    superseded_by TEXT,                 -- ID of the entry that replaced this one (null if current)
    embedding   BLOB                    -- Vector embedding for semantic search
);

CREATE INDEX idx_entries_type ON memory_entries(type);
CREATE INDEX idx_entries_scope ON memory_entries(scope);
CREATE INDEX idx_entries_confidence ON memory_entries(confidence DESC);
```

### Enforcement Rule

A subset of memory entries with enforcement metadata. Rules are memory entries of type 'rule' with additional structured data.

```sql
CREATE TABLE enforcement_rules (
    id              TEXT PRIMARY KEY,     -- Same as memory_entry ID
    pattern         TEXT NOT NULL,        -- What to match: regex, command pattern, or intent description
    pattern_type    TEXT NOT NULL,        -- 'regex' | 'command' | 'intent'
    action          TEXT NOT NULL,        -- 'block' | 'warn' | 'suggest_alternative'
    severity        TEXT NOT NULL,        -- 'critical' | 'high' | 'medium' | 'low'
    alternative     TEXT,                 -- What to do instead (shown when blocked)
    active          INTEGER DEFAULT 1,   -- 0 = disabled, 1 = active
    FOREIGN KEY (id) REFERENCES memory_entries(id)
);
```

### Correction Log

Raw corrections before they're processed into memory entries. The intake queue.

```sql
CREATE TABLE corrections (
    id              TEXT PRIMARY KEY,     -- UUID
    session_id      TEXT,                 -- Which conversation this happened in
    user_message    TEXT NOT NULL,        -- The user's corrective statement
    what_was_wrong  TEXT NOT NULL,        -- Extracted: what the agent did wrong
    what_is_right   TEXT NOT NULL,        -- Extracted: what should happen instead
    context         TEXT,                 -- What was being worked on when the correction happened
    detected_at     TEXT NOT NULL,        -- ISO 8601 timestamp
    detection_type  TEXT NOT NULL,        -- 'explicit' | 'implicit' | 'repeated'
    promoted_to     TEXT,                 -- memory_entry ID if promoted to a rule
    occurrence_count INTEGER DEFAULT 1   -- How many times this correction has been made
);
```

### Audit Log

Every memory system action gets logged. Essential for debugging and trust.

```sql
CREATE TABLE memory_audit_log (
    id          TEXT PRIMARY KEY,
    timestamp   TEXT NOT NULL,
    action      TEXT NOT NULL,            -- 'inject' | 'enforce_block' | 'enforce_warn' | 'capture' | 'verify_pass' | 'verify_fail' | 'query' | 'pin' | 'unpin' | 'promote' | 'decay'
    entry_id    TEXT,                     -- Which memory entry was involved
    context     TEXT,                     -- What was happening when this action occurred
    result      TEXT,                     -- Outcome of the action
    details     TEXT                      -- JSON blob with additional data
);
```

---

## API Design

The memory system exposes a single API layer that all subsystems use. Other components (daemon, multi-agent) will use the same API.

### Core Operations

```
memory.query(text, scope?, type?, limit?) → MemoryEntry[]
    Semantic search over all entries. Returns ranked results.
    Used by: Context Injector, Semantic Retriever, Verification Checker

memory.inject(session_context) → MemoryEntry[]
    Given the current working context (project, file, task), returns
    all relevant memories that should be loaded into the agent's context.
    Used by: Context Injector (at session start and on context change)

memory.enforce(action) → {allowed: bool, reason?: string, alternative?: string}
    Checks a proposed action against all active enforcement rules.
    Returns whether the action is allowed and why/why not.
    Used by: Enforcement Engine (before every tool call)

memory.capture(user_message, agent_response, context) → Correction?
    Analyzes a user message for corrections. If found, extracts the
    correction and stores it. Returns the correction if one was detected.
    Used by: Correction Detector (after every user message)

memory.verify(action, result) → {passed: bool, violations: Rule[]}
    After an action completes, checks whether the result violates any rules.
    Used by: Verification Checker (after every tool call)

memory.pin(entry_id) → void
    Promotes a memory entry to the pinned layer (CLAUDE.md or equivalent).
    Pinned entries survive context compression.
    Used by: Pin Manager

memory.add(content, type, scope, source, tags?) → MemoryEntry
    Manually add a memory entry.
    Used by: User, Correction Detector, any component

memory.update(entry_id, changes) → MemoryEntry
    Update an existing entry (content, confidence, tags, etc.)
    Used by: Correction Detector (when same correction repeats)

memory.decay() → {decayed: int, archived: int}
    Run decay pass: reduce confidence on entries not accessed in 30+ days,
    archive entries below threshold. Run on schedule or at session boundaries.
    Used by: Maintenance routine
```

### Integration Points

```
Hook: SessionStart
    → memory.inject(session_context)
    → Relevant memories loaded into agent context

Hook: PreToolCall
    → memory.enforce(proposed_action)
    → Block or allow the action

Hook: PostToolCall
    → memory.verify(action, result)
    → Log violations, strengthen rules if violated

Hook: UserMessage
    → memory.capture(message, previous_response, context)
    → Extract and store corrections automatically

Hook: PreCompact (before context compression)
    → memory.pin(critical_entries)
    → Ensure critical rules survive compression

Hook: SessionEnd
    → memory.decay()
    → Run maintenance pass
```

---

## Tech Stack

### Storage: SQLite

**Why SQLite:**
- Zero infrastructure — single file, no server, no daemon
- Runs everywhere (Windows, macOS, Linux) with no setup
- Fast enough for the query patterns needed (hundreds of entries, not millions)
- Supports full-text search natively (FTS5)
- The agent can read and write it with existing tools
- Portable — copy the file to a new machine and everything comes with

**Why not PostgreSQL:** Overkill for a local agent's memory. Adds infrastructure, setup, and a running server process. Would only make sense if the daemon needs distributed storage (Phase 2 concern, not Phase 1).

**Why not flat files (current system):** No querying, no indexing, no structured data, no concurrent access, no transactional safety. The current MEMORY.md system is flat files and it's exactly why memory doesn't have teeth.

**File location:** `~/.claude/memory/memory.db`

### Vector Index: sqlite-vec

**Why sqlite-vec:**
- SQLite extension — stays in the same database, no separate service
- Supports cosine similarity search over float32 vectors
- Fast enough for the scale needed (thousands of entries, not millions)
- Pure C, compiles on all platforms
- No Python dependency — can be loaded as a SQLite extension

**Alternative considered:** Chroma, Qdrant, Pinecone. All require separate processes. For a local agent's memory, the overhead isn't justified. sqlite-vec keeps everything in one file.

### Embeddings: Model-provided or local

**Primary:** Use the same model's embedding capability if available (Claude's embeddings via API, OpenAI's text-embedding-3-small).

**Fallback:** Local embedding model via sentence-transformers (all-MiniLM-L6-v2 — 384 dimensions, 80MB, runs on CPU in <100ms per embedding). This ensures memory works offline and doesn't require API calls for every query.

**Embedding dimensions:** 384 (MiniLM) or 1536 (OpenAI) depending on provider. Store as BLOB in SQLite, index via sqlite-vec.

### Hooks: Claude Code hooks system

The enforcement engine integrates directly with Claude Code's existing hooks:

```json
// ~/.claude/hooks.json
{
  "hooks": {
    "SessionStart": [
      {
        "command": "memory-cli inject --session-context \"$SESSION_CONTEXT\"",
        "description": "Load relevant memories at session start"
      }
    ],
    "PreToolCall": [
      {
        "command": "memory-cli enforce --tool \"$TOOL_NAME\" --input \"$TOOL_INPUT\"",
        "description": "Check proposed actions against enforcement rules"
      }
    ],
    "PostToolCall": [
      {
        "command": "memory-cli verify --tool \"$TOOL_NAME\" --input \"$TOOL_INPUT\" --output \"$TOOL_OUTPUT\"",
        "description": "Verify actions followed rules"
      }
    ],
    "PreCompact": [
      {
        "command": "memory-cli pin --critical",
        "description": "Pin critical rules before context compression"
      }
    ]
  }
}
```

### CLI: `memory-cli`

A standalone command-line tool that wraps the memory API. Written in Python (fast development, works with existing ecosystem) or Rust (fast execution, single binary).

**Python is the pragmatic choice for v0.1-v0.3.** Rewrite in Rust for v1.0 if performance matters.

```
memory-cli query "pywebview drag" --scope project:whisperclick --limit 5
memory-cli inject --session-context '{"project": "WhisperClick V3", "file": "src/main.py"}'
memory-cli enforce --tool Bash --input "pythonw.exe src/main.py"
memory-cli capture --user-message "No, never use pythonw.exe" --context "launching GUI"
memory-cli add --type rule --content "Never use pythonw.exe" --scope global --confidence 1.0
memory-cli stats
memory-cli decay --dry-run
```

---

## Implementation Phases

### Phase 0: Structured Foundation (3 days)

**Goal:** Replace flat markdown memory files with a queryable SQLite database, preserving all existing content.

**What to build:**
1. Create SQLite database schema (all four tables above)
2. Write a migration script that reads existing memory files (MEMORY.md, hot-memory.md, corrections-log.md, context-memory.md, decisions-log.md) and imports every entry into the database with appropriate type, scope, and tags
3. Write `memory-cli query` — full-text search over entries
4. Write `memory-cli add` — add new entries
5. Write `memory-cli stats` — show entry counts by type, scope, and age

**What changes for the user:** Nothing yet. Memory files still exist. The database is a parallel system being populated.

**Success criteria:**
- All existing memory content is in the database
- `memory-cli query "pywebview"` returns relevant entries from the imported data
- `memory-cli stats` shows accurate counts

**Effort: 3 days.**

---

### Phase 1: Context Injection (1 week)

**Goal:** Relevant memories load automatically based on what the agent is working on.

**What to build:**
1. Add vector embeddings to all entries (batch embedding on import, incremental on new entries)
2. Implement `memory.inject(session_context)` — given project name, file path, and task description, return the top N most relevant entries via semantic similarity + scope filtering
3. Wire into Claude Code's SessionStart hook — at session start, inject relevant memories into the system prompt or initial context
4. Implement scope-aware filtering — global rules always load, project rules load for that project, file rules load for that file
5. Implement relevance threshold — don't inject memories below a similarity score of 0.6

**What changes for the user:** The agent starts sessions with relevant context already loaded. No more "read MEMORY.md" bootstrap dance. The right memories appear automatically.

**Success criteria:**
- Opening a WhisperClick file injects WhisperClick-specific rules
- Opening a random project doesn't inject WhisperClick rules
- Global rules (like "never use pythonw.exe") inject everywhere
- Injection takes less than 500ms

**Effort: 1 week.**

---

### Phase 2: Enforcement Engine (1 week)

**Goal:** Known-bad actions are blocked before they execute.

**What to build:**
1. Implement `memory.enforce(action)` — check a proposed action against all active enforcement rules
2. Support three pattern types:
   - **Regex:** Match against the command string (`pythonw\.exe`, `git push public main`)
   - **Command:** Match against tool name + input pattern (`Bash` + contains `pythonw`)
   - **Intent:** Semantic similarity between the action description and the rule (for rules that can't be expressed as patterns)
3. Wire into Claude Code's PreToolCall hook — before every Bash command, Edit, or Write, check enforcement rules
4. Implement three response types:
   - **Block:** Stop the action, show the rule and alternative
   - **Warn:** Allow the action but show a warning
   - **Suggest:** Allow but suggest a better approach
5. Log every enforcement action to the audit log

**What changes for the user:** The agent can't do things it's been told not to do. `pythonw.exe` gets blocked. `git push public main` gets blocked. These are actual gates, not suggestions.

**Success criteria:**
- `pythonw.exe` in any Bash command is blocked with explanation
- `git push public main` is blocked with the correct alternative (sync_public.py)
- Enforcement check adds less than 100ms to each tool call
- Audit log shows every blocked and warned action

**Effort: 1 week.**

---

### Phase 3: Automatic Correction Capture (1 week)

**Goal:** When the user corrects the agent, the correction is extracted and stored without manual logging.

**What to build:**
1. Implement `memory.capture(user_message, agent_response, context)` — analyze user messages for correction patterns
2. Pattern detection (rule-based first, model-assisted later):
   - Explicit: "No, do it this way", "Never use X", "Always do Y", "Stop doing Z"
   - Implicit: "I already told you...", "Again, ...", "Like I said..."
   - Repeated: Same instruction given 3+ times across sessions
3. Extraction: From a detected correction, extract:
   - What was wrong (what the agent did)
   - What is right (what should happen instead)
   - Context (what was being worked on)
   - Confidence (explicit corrections = high, implicit = medium, inferred = low)
4. Deduplication: If a correction matches an existing one, increment occurrence_count instead of creating a duplicate
5. Auto-promotion: When occurrence_count reaches 3, automatically promote to an enforcement rule and notify the user

**What changes for the user:** Corrections stick. Say "never use pythonw.exe" once, it gets captured. Say it three times across different sessions, it gets promoted to an enforcement rule that blocks the action. No manual memory file editing.

**Success criteria:**
- "No, use python.exe not pythonw.exe" creates a correction entry with correct extraction
- Same correction appearing 3 times triggers auto-promotion to enforcement rule
- Duplicate corrections increment count instead of creating new entries
- User is notified when a correction is promoted

**Effort: 1 week.**

---

### Phase 4: Compression-Proof Pinning (3 days)

**Goal:** Critical rules survive context window compression.

**What to build:**
1. Implement `memory.pin(entry_id)` — mark an entry as pinned
2. Pinned entries are written to CLAUDE.md (the file that's always loaded) in a structured section
3. Wire into PreCompact hook — before context compression, ensure all pinned entries are present in CLAUDE.md
4. Implement a sync mechanism — CLAUDE.md's pinned section stays in sync with the database's pinned entries
5. Limit: Maximum 20 pinned entries to prevent CLAUDE.md bloat. If you try to pin more, the least-recently-used pinned entry gets unpinned.

**What changes for the user:** The most important rules never get lost, no matter how long the session runs. Even after context compression at turn 50, the pinned rules are still at full fidelity.

**Success criteria:**
- Pinned rules appear in CLAUDE.md's structured section
- After context compression, pinned rules are still present and at full text (not summarized)
- Pin limit of 20 is enforced with LRU eviction
- Pinning/unpinning syncs between database and CLAUDE.md within 1 second

**Effort: 3 days.**

---

### Phase 5: Behavioral Verification (3 days)

**Goal:** After the agent acts, check whether it followed its own rules.

**What to build:**
1. Implement `memory.verify(action, result)` — check the output of a completed action against relevant rules
2. Wire into PostToolCall hook — after every tool call completes, run verification
3. Detection patterns:
   - Text matching: Did the output contain a forbidden pattern? (e.g., `pythonw.exe` in a file that was written)
   - Semantic: Does the action's result contradict a known rule?
4. On violation:
   - Log to audit log with full context
   - Increment the rule's violation_count
   - If violation_count > 3: auto-promote rule severity (medium → high → critical)
   - Notify the user of the violation
5. Keep verification lightweight — most checks are regex/text matching, not model calls

**What changes for the user:** Rules don't just block actions before they happen — they catch violations after the fact. If the agent writes a file that contains `pythonw.exe` despite the rule, the verification checker catches it.

**Success criteria:**
- Writing a file containing `pythonw.exe` triggers a verification failure
- Violation count increments correctly
- Rules auto-escalate in severity after repeated violations
- Verification adds less than 200ms per tool call

**Effort: 3 days.**

---

### Phase 6: Semantic Retrieval Integration (1 week)

**Goal:** The agent can query its own memory by meaning during work, not just at session start.

**What to build:**
1. Expose `memory.query()` as a tool the agent can call mid-session
2. When the agent encounters an error, automatically query memory for past solutions to similar errors
3. When the agent is about to make an architecture decision, automatically surface relevant past decisions and rejected alternatives
4. Implement relevance ranking: combine semantic similarity (embedding distance) with recency (recent entries rank higher) and confidence (high-confidence entries rank higher)
5. Implement negative retrieval: "what did I decide NOT to do here before?" — surface rejected alternatives

**What changes for the user:** The agent actively uses its memory while working. It doesn't just start with memories loaded — it queries them throughout the session when relevant. "I hit this error before, the fix was X" happens automatically.

**Success criteria:**
- Agent encountering a pywebview error automatically surfaces past pywebview corrections
- Architecture decisions surface relevant rejected alternatives
- Retrieval latency under 300ms
- Results are ranked by relevance × recency × confidence

**Effort: 1 week.**

---

## Phase Summary

| Phase | What | Effort | Cumulative | Level Unlocked |
|-------|------|--------|------------|----------------|
| 0 | Structured foundation (SQLite, migration, CLI) | 3 days | 3 days | — (infrastructure) |
| 1 | Context injection (embeddings, auto-load, hooks) | 1 week | 10 days | Level 1: Automatic Injection |
| 2 | Enforcement engine (block/warn/suggest, audit) | 1 week | 17 days | Level 2: Enforcement Hooks |
| 3 | Correction capture (detect, extract, promote) | 1 week | 24 days | Level 4: Automatic Capture |
| 4 | Compression-proof pinning (CLAUDE.md sync) | 3 days | 27 days | Level 5: Compression-Proof |
| 5 | Behavioral verification (post-action checks) | 3 days | 30 days | Level 6: Behavioral Verification |
| 6 | Semantic retrieval (mid-session queries) | 1 week | 37 days | Level 3: Semantic Retrieval |

**Total: ~37 working days (~7.5 weeks) from zero to all six levels.**

Phases 0-2 (foundation + injection + enforcement) deliver the most value and take 17 days. That's the critical path. Everything after that is iterative improvement on a working system.

---

## Directory Structure

```
~/.claude/memory/
├── memory.db              # SQLite database (entries, rules, corrections, audit log)
├── memory-cli             # CLI binary (or memory-cli.py)
├── config.json            # Configuration (embedding model, thresholds, limits)
├── embeddings/            # Cached embeddings (if using local model)
│   └── model/             # Local embedding model files
└── backups/               # Automated daily backups of memory.db
```

## Configuration

```json
{
  "database_path": "~/.claude/memory/memory.db",
  "embedding": {
    "provider": "local",
    "model": "all-MiniLM-L6-v2",
    "dimensions": 384,
    "fallback_provider": "openai",
    "fallback_model": "text-embedding-3-small"
  },
  "injection": {
    "max_entries": 15,
    "similarity_threshold": 0.6,
    "always_include_scopes": ["global"],
    "max_tokens": 2000
  },
  "enforcement": {
    "enabled": true,
    "max_latency_ms": 100,
    "default_action": "warn"
  },
  "capture": {
    "enabled": true,
    "auto_promote_threshold": 3,
    "detection_mode": "rule_based"
  },
  "pinning": {
    "max_pinned": 20,
    "sync_target": "CLAUDE.md"
  },
  "verification": {
    "enabled": true,
    "max_latency_ms": 200
  },
  "decay": {
    "inactive_days": 30,
    "decay_rate": 0.1,
    "archive_threshold": 0.1
  },
  "backup": {
    "enabled": true,
    "frequency": "daily",
    "max_backups": 7
  }
}
```

---

## Testing Strategy

### Unit Tests

| Subsystem | Test Cases |
|-----------|-----------|
| Memory Store | CRUD operations, FTS5 search, embedding insert/query, concurrent access, migration from flat files |
| Context Injector | Scope filtering (global vs project vs file), relevance ranking, token budget enforcement, empty results |
| Enforcement Engine | Regex matching, command matching, block/warn/suggest responses, rule priority ordering, disabled rules |
| Correction Detector | Explicit correction detection, implicit detection, deduplication, auto-promotion at threshold |
| Pin Manager | Pin/unpin operations, CLAUDE.md sync, LRU eviction at limit, sync conflict resolution |
| Verification Checker | Text pattern detection, violation counting, severity auto-escalation, false positive handling |

### Integration Tests

| Scenario | What to Verify |
|----------|---------------|
| Full session lifecycle | SessionStart → inject → work → enforce → verify → SessionEnd → decay |
| Correction to enforcement | User corrects → captured → repeated 3x → promoted to rule → rule blocks action |
| Cross-session persistence | Memory created in session 1 → available in session 2 without manual loading |
| Context compression survival | Pin a rule → trigger compression → verify rule still present at full fidelity |
| Performance under load | 1000 entries in database → injection still under 500ms, enforcement under 100ms |

### Smoke Tests

```bash
# Does injection work?
memory-cli inject --session-context '{"project": "WhisperClick V3"}' | grep -q "pythonw"

# Does enforcement work?
memory-cli enforce --tool Bash --input "pythonw.exe src/main.py" | grep -q "blocked"

# Does capture work?
memory-cli capture --user-message "No, never use pythonw.exe" | grep -q "correction"

# Does query work?
memory-cli query "drag window" --scope project:whisperclick | grep -q "WM_APP_DRAGSTART"
```

---

## Known Risks and Mitigations

### 1. Embedding quality determines retrieval quality

**Risk:** If embeddings are poor, semantic search returns irrelevant results. The agent gets injected with wrong context.

**Mitigation:** Start with rule-based injection (scope + tag matching) in Phase 1. Add semantic search as a ranking boost, not the only signal. Always include exact-match FTS5 results alongside embedding results. Use a proven embedding model (MiniLM or OpenAI), not an untested one.

### 2. Over-injection wastes context window

**Risk:** If too many memories are injected at session start, they crowd out the actual conversation. The agent's useful context window shrinks.

**Mitigation:** Hard limit of 15 entries and 2000 tokens for injected memories. Relevance threshold of 0.6 filters out marginal matches. Injected memories are formatted concisely (one line per entry, not full paragraphs). The user can tune these limits via config.

### 3. False positive enforcement blocks legitimate actions

**Risk:** A rule meant to block `pythonw.exe` accidentally blocks a legitimate command that contains that string (e.g., checking if the process is running).

**Mitigation:** Enforcement rules have three action levels (block, warn, suggest). New rules start at "warn" and only get promoted to "block" after the user confirms. Regex patterns can be narrowed. Intent-based matching (Phase 2+) reduces false positives by understanding context, not just string matching.

### 4. Auto-captured corrections are wrong

**Risk:** The correction detector misinterprets a user message as a correction when it wasn't one, or extracts the wrong lesson.

**Mitigation:** Auto-captured corrections start at low confidence (0.3). They don't become enforcement rules until repeated 3 times. The user is notified on promotion and can reject. A `memory-cli review` command lets users see and approve/reject pending corrections.

### 5. Database corruption or loss

**Risk:** SQLite file gets corrupted, accidentally deleted, or lost.

**Mitigation:** Automated daily backups (7 rolling). WAL mode for crash resistance. The migration script can re-import from flat files as a fallback. The flat files (MEMORY.md etc.) continue to exist as a degraded backup.

### 6. Hook latency slows down the agent

**Risk:** If enforcement checks take too long, every tool call feels sluggish.

**Mitigation:** Strict latency budgets: 100ms for enforcement, 200ms for verification, 500ms for injection. If a check exceeds its budget, it returns "allow" with a warning in the audit log rather than blocking the agent. The database is local SQLite — queries are fast. Embedding computation is the slowest part and is cached.

---

## Migration Path From Current System

The current system has ~14 markdown files with accumulated rules, preferences, corrections, and context. The migration preserves all of this.

### Step 1: Import

```
memory-cli migrate --source shared/memory/ --source ~/.claude/projects/*/memory/
```

This reads every markdown file, parses sections and bullet points, classifies each entry (rule, preference, fact, decision, correction), assigns scope based on file location, and inserts into the database.

### Step 2: Parallel operation

For the first 2 weeks, both systems run in parallel. The database handles injection and enforcement. The flat files continue to be loaded by CLAUDE.md instructions. This lets us validate that the database version matches the flat file version without risking loss.

### Step 3: Cutover

Once validated, update CLAUDE.md to read from the memory system instead of flat files. Flat files move to archive but aren't deleted. The pinned rules section in CLAUDE.md is now managed by the Pin Manager.

### Step 4: Flat file deprecation

After 30 days of database-only operation, flat files are archived. New sessions no longer reference them. The database is the single source of truth.

---

## What This Enables Next

With memory built, the next components become dramatically easier:

**Stateful Agent Daemon (doc 05):** The daemon's persistent state store IS the memory database. The event bus logs to the same audit log. The authority tiers reference the same enforcement rules. Memory isn't just a prerequisite — it's the same system, extended.

**Multi-Agent Orchestration (doc 10):** The shared context store IS the memory database, scoped to the project. Workers read and write to the same store. Interface contracts, architecture decisions, and discovered constraints are all memory entries with type 'fact' and scope 'project'.

**Credential Management (doc 09):** The enforcement engine can block actions that contain credential patterns in their output (output scanning). The audit log tracks credential-adjacent actions.

**Sandboxed Execution (doc 08):** Memory entries with type 'pattern' inform sandbox configuration — "this project needs Node 22, Python 3.12, and these environment variables" is a queryable memory.

Memory with teeth isn't just one component. It's the substrate that every other component grows on. That's why it's built first.
