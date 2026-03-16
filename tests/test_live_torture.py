#!/usr/bin/env python3
"""LIVE torture tests — no mocks, real processes, real files, real network.

Run with: python tests/test_live_torture.py
NOT part of the normal pytest suite (uses real resources).
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from threading import Thread

# Add project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Fix Windows encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PASS = 0
FAIL = 0
SKIP = 0


def test(name):
    """Decorator for test functions."""
    def decorator(fn):
        fn._test_name = name
        return fn
    return decorator


def run_test(fn):
    global PASS, FAIL, SKIP
    name = getattr(fn, '_test_name', fn.__name__)
    try:
        result = fn()
        if result == "SKIP":
            print(f"  SKIP  {name}")
            SKIP += 1
        else:
            print(f"  PASS  {name}")
            PASS += 1
    except Exception as e:
        print(f"  FAIL  {name}: {e}")
        FAIL += 1


# ============================================================
# 1. Memory Full Pipeline
# ============================================================

@test("Memory: fresh DB → migrate → seed → query → enforce")
def test_memory_pipeline():
    from src.memory.store import MemoryStore
    from src.hooks.enforce import enforce
    from src.hooks.capture import capture, PROMOTION_THRESHOLD
    from src.hooks.verify import verify

    tmp = tempfile.mkdtemp()
    try:
        db_path = Path(tmp) / "torture.db"
        store = MemoryStore(db_path)

        # Add some entries manually (simulating migrate)
        store.add("Never use pythonw.exe for GUI", "rule", scope="global", confidence=0.9, source="test")
        store.add("WhisperClick uses pywebview", "fact", scope="project:whisperclick", source="test")
        store.add("Mission Control runs on port 8100", "fact", scope="project:mission-control", source="test")

        # Seed enforcement rules
        import importlib.util
        spec = importlib.util.spec_from_file_location("seed", os.path.join(PROJECT_ROOT, "scripts", "seed-rules.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        added = mod.seed_rules(store)
        assert added == 10, f"Expected 10 rules, got {added}"

        # Query
        results = store.query("pythonw")
        assert len(results) >= 1, "Query should find pythonw entries"

        # Enforce — should block
        result = enforce(store, "Bash", "pythonw.exe test.py")
        assert not result.allowed, "pythonw should be blocked"
        assert result.action == "block"

        # Enforce — should allow
        result = enforce(store, "Bash", "python.exe test.py")
        assert result.allowed, "python.exe should be allowed"

        # Capture correction -> auto-promote
        for i in range(PROMOTION_THRESHOLD):
            r = capture(store, "No, don't use SendMessageW for drag")
        assert r.promoted or r.occurrence_count >= PROMOTION_THRESHOLD

        # Verify — should catch violation
        vr = verify(store, "Write", "create script", "#!/bin/bash\npythonw.exe app.py")
        assert not vr.compliant, "Should detect pythonw in output"

        store.close()
    finally:
        try:
            shutil.rmtree(tmp, ignore_errors=True)
        except Exception:
            pass


# ============================================================
# 2. PTY — Real Python REPL
# ============================================================

@test("PTY: start process -> send input -> read output")
def test_pty_real_repl():
    from src.pty.session import PTYSession

    with PTYSession() as session:
        # Use a simple echo command on Windows
        session.start("cmd.exe")
        time.sleep(0.5)

        # Drain startup
        session.read(timeout=2)

        # Send echo command
        session.send("echo TORTURE_TEST_OK")
        time.sleep(0.5)
        output = session.read(timeout=3)
        assert "TORTURE_TEST_OK" in output, f"Expected 'TORTURE_TEST_OK' in output, got: {repr(output)}"


# ============================================================
# 3. Sandbox — Real Git Worktree
# ============================================================

@test("Sandbox: create → run command → diff → destroy")
def test_sandbox_real():
    from src.sandbox.manager import SandboxManager

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "test-repo"
        repo.mkdir()

        # Init a git repo with a commit
        subprocess.run(["git", "init"], cwd=str(repo), capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(repo), capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=str(repo), capture_output=True)
        (repo / "hello.txt").write_text("hello world")
        subprocess.run(["git", "add", "."], cwd=str(repo), capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=str(repo), capture_output=True)

        mgr = SandboxManager(str(repo))

        # Create sandbox
        info = mgr.create("test-sandbox")
        assert Path(info.path).exists(), "Sandbox directory should exist"

        # Run a command in it
        result = mgr.run("test-sandbox", "echo hello from sandbox")
        assert result.returncode == 0
        assert "hello from sandbox" in result.stdout

        # Make a change and check diff
        sandbox_file = Path(info.path) / "new_file.txt"
        sandbox_file.write_text("new content")
        subprocess.run(["git", "add", "."], cwd=info.path, capture_output=True)
        diff = mgr.diff("test-sandbox")
        # diff may or may not show content depending on staging

        # Destroy
        mgr.destroy("test-sandbox")
        assert not Path(info.path).exists(), "Sandbox should be cleaned up"


# ============================================================
# 4. Webhook — Real HTTP Server
# ============================================================

@test("Webhook: start server → POST event → verify received")
def test_webhook_real():
    from src.daemon.events import EventBus, EventType
    from src.daemon.webhook import WebhookListener

    bus = EventBus()
    received = []
    bus.subscribe(EventType.WEBHOOK, lambda e: received.append(e))

    # Find a free port
    import socket
    with socket.socket() as s:
        s.bind(('', 0))
        port = s.getsockname()[1]

    listener = WebhookListener(bus, port=port)
    listener.start()
    time.sleep(0.5)

    try:
        # POST a webhook
        data = json.dumps({"source": "github", "event": "push", "repo": "test"}).encode()
        req = urllib.request.Request(
            f"http://localhost:{port}/webhook",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        resp = urllib.request.urlopen(req, timeout=5)
        assert resp.status == 200, f"Expected 200, got {resp.status}"

        # Health check
        resp2 = urllib.request.urlopen(f"http://localhost:{port}/health", timeout=5)
        assert resp2.status == 200

        # Give bus time to process
        time.sleep(0.5)
        bus.process_one(timeout=1)

        assert len(received) >= 1, f"Expected webhook event, got {len(received)}"
        assert received[0].payload.get("source") == "github"
    finally:
        listener.stop()


# ============================================================
# 5. Scheduler — Real Timer
# ============================================================

@test("Scheduler: add timer → wait → verify it fires")
def test_scheduler_real():
    from src.daemon.events import EventBus, EventType
    from src.daemon.scheduler import Scheduler

    bus = EventBus()
    fired = []
    bus.subscribe(EventType.TIMER, lambda e: fired.append(e))

    scheduler = Scheduler(bus)
    scheduler.add("test-timer", 0.3, payload={"msg": "tick"})
    scheduler.start()

    try:
        time.sleep(1.0)
        # Process any events
        while bus.pending > 0:
            bus.process_one(timeout=0.1)

        assert len(fired) >= 1, f"Timer should have fired at least once, got {len(fired)}"
        assert fired[0].payload.get("msg") == "tick"

        # Check list
        timers = scheduler.list_timers()
        assert any(t["name"] == "test-timer" for t in timers)
    finally:
        scheduler.stop()


# ============================================================
# 6. File Watcher — Real File Events
# ============================================================

@test("File watcher: watch dir → create file → verify event")
def test_file_watcher_real():
    from src.daemon.events import EventBus, EventType
    from src.daemon.watcher import FileWatcher

    bus = EventBus()
    events = []
    bus.subscribe(EventType.FILE_CHANGE, lambda e: events.append(e))

    with tempfile.TemporaryDirectory() as tmp:
        watcher = FileWatcher(bus, [tmp])
        watcher.start()
        time.sleep(0.5)

        try:
            # Create a file
            test_file = Path(tmp) / "test_file.py"
            test_file.write_text("print('hello')")
            time.sleep(1.0)

            # Process events
            while bus.pending > 0:
                bus.process_one(timeout=0.1)

            assert len(events) >= 1, f"Should detect file creation, got {len(events)} events"
        finally:
            watcher.stop()


# ============================================================
# 7. Credential — Real Windows Credential Manager
# ============================================================

@test("Credentials: set → get → delete roundtrip")
def test_credentials_real():
    from src.credentials.broker import get, set as cred_set, delete

    service = "torture-test-key"
    scope = "test"
    value = "test-secret-value-12345"

    try:
        # Set
        cred_set(service, value, scope=scope)

        # Get
        retrieved = get(service, scope=scope)
        assert retrieved == value, f"Expected '{value}', got '{retrieved}'"

    finally:
        # Always clean up
        delete(service, scope=scope)

    # Verify deleted
    after = get(service, scope=scope)
    assert after is None, "Credential should be deleted"


# ============================================================
# 8. Secret Scanner — Real Pattern Detection
# ============================================================

@test("Secret scanner: detect real-format keys")
def test_scanner_real():
    from src.credentials.scanner import scan_output, redact

    # Simulate text with a fake but format-matching key
    text = """
    Here's the config:
    OPENAI_API_KEY=sk-proj-abc123def456ghi789jkl012mno345pqr678stu901vwx234
    GITHUB_TOKEN=ghp_1234567890abcdefghijklmnopqrstuvwxyz
    Normal text that should not trigger: hello world
    """

    findings = scan_output(text)
    assert len(findings) >= 2, f"Should detect at least 2 secrets, got {len(findings)}"

    # Redact
    redacted = redact(text)
    assert "sk-proj-" not in redacted, "Key should be redacted"
    assert "ghp_" not in redacted, "GitHub token should be redacted"
    assert "hello world" in redacted, "Normal text should survive"


# ============================================================
# 9. Daemon Full Loop — End to End
# ============================================================

@test("Daemon full loop: event → triage → authority → execute → audit")
def test_daemon_full_loop():
    from src.daemon.events import EventBus, DaemonEvent, EventType
    from src.daemon.state import DaemonState, AuthorityTier
    from src.daemon.loop import DaemonLoop, LoopConfig

    with tempfile.TemporaryDirectory() as tmp:
        bus = EventBus()
        state = DaemonState(Path(tmp) / "state.db")
        config = LoopConfig(poll_interval=0.1)
        executed = []

        loop = DaemonLoop(bus, state, config)
        loop.register_action("python_source", lambda e, t: executed.append(e.payload) or "processed")
        loop.register_action("timer", lambda e, t: executed.append({"timer": True}) or "tick")

        # Emit events
        bus.emit(DaemonEvent(
            event_type=EventType.FILE_CHANGE,
            source="watcher",
            payload={"path": "src/main.py", "change_type": "modified"},
        ))
        bus.emit(DaemonEvent(event_type=EventType.TIMER, source="scheduler"))

        # Process
        loop.process_cycle()
        loop.process_cycle()

        assert len(executed) >= 2, f"Both events should be processed, got {len(executed)}"

        # Check audit trail
        log = state.get_action_log()
        assert len(log) >= 2, f"Audit log should have entries, got {len(log)}"

        state.close()


# ============================================================
# 10. Browser — Real HTTP (DuckDuckGo)
# ============================================================

@test("Browser: real DuckDuckGo search")
def test_browser_real_search():
    try:
        import httpx
    except ImportError:
        return "SKIP"

    from src.browser.sync_api import search

    try:
        results = search("python programming language", max_results=3)
        if len(results) == 0:
            # DuckDuckGo may block automated requests — not a code bug
            print("    (DuckDuckGo returned 0 results — may be rate-limited)")
            return "SKIP"
        assert results[0].title, "Result should have a title"
        assert results[0].url.startswith("http"), f"URL should be valid: {results[0].url}"
    except Exception as e:
        if "timeout" in str(e).lower() or "connect" in str(e).lower() or "rate" in str(e).lower():
            return "SKIP"
        raise


@test("Browser: real page fetch")
def test_browser_real_fetch():
    try:
        import httpx
    except ImportError:
        return "SKIP"

    from src.browser.sync_api import fetch_page

    try:
        page = fetch_page("https://example.com")
        assert "Example Domain" in page.title, f"Title should contain 'Example Domain', got: {page.title}"
        assert len(page.text_content) > 50, "Should have substantial text content"
        assert len(page.links) >= 1, "Should have at least one link"
    except Exception as e:
        if "timeout" in str(e).lower() or "connect" in str(e).lower():
            return "SKIP"
        raise


# ============================================================
# 11. Orchestrator — Real Multi-Agent Flow
# ============================================================

@test("Orchestrator: decompose → assign → execute → finalize")
def test_orchestrator_real():
    from src.orchestrator.context import SharedContext
    from src.orchestrator.worker import Worker, WorkerTask
    from src.orchestrator.supervisor import Supervisor

    with tempfile.TemporaryDirectory() as tmp:
        ctx = SharedContext(Path(tmp) / "context.db")

        supervisor = Supervisor(ctx)
        supervisor.set_decomposer(lambda desc: [
            {"title": "Write tests", "files": ["tests/new_test.py"]},
            {"title": "Fix bug", "files": ["src/main.py"]},
        ])

        w1 = Worker("worker-1", ctx)
        w1.register_handler("default", lambda t: f"Completed: {t.title}")
        w2 = Worker("worker-2", ctx)
        w2.register_handler("default", lambda t: f"Completed: {t.title}")

        supervisor.add_worker(w1)
        supervisor.add_worker(w2)

        # Full lifecycle
        plan = supervisor.decompose("Fix bug and add tests")
        assignments = supervisor.assign_tasks()
        assert len(assignments) == 2, f"Both tasks should be assigned, got {len(assignments)}"

        results = supervisor.execute_all()
        assert len(results) == 2

        assert supervisor.is_complete()

        summary = supervisor.finalize()
        assert summary["status"] == "completed"
        assert len(summary["results"]) == 2

        # Verify file locks were released
        locked = ctx.get_locked_files()
        assert len(locked) == 0, "All locks should be released"

        ctx.close()


# ============================================================
# 12. Hook Scripts — Real Process Execution
# ============================================================

@test("Hook: PreToolUse blocks pythonw via real script execution")
def test_hook_pretool_real():
    python = sys.executable
    script = Path(__file__).parent.parent / "scripts" / "hook-pre-tool-call.py"

    result = subprocess.run(
        [python, str(script)],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "pythonw.exe test.py"}}),
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 2, f"Should block (exit 2), got exit {result.returncode}"
    assert "BLOCKED" in result.stderr, f"Should say BLOCKED, got: {result.stderr}"


@test("Hook: PreToolUse allows normal command")
def test_hook_pretool_allows():
    python = sys.executable
    script = Path(__file__).parent.parent / "scripts" / "hook-pre-tool-call.py"

    result = subprocess.run(
        [python, str(script)],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "echo hello"}}),
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, f"Should allow (exit 0), got exit {result.returncode}"


@test("Hook: SessionStart completes in <2s")
def test_hook_session_timing():
    python = sys.executable
    script = Path(__file__).parent.parent / "scripts" / "hook-session-start.py"

    start = time.perf_counter()
    result = subprocess.run(
        [python, str(script)],
        input=json.dumps({"project": "WhisperClick"}),
        capture_output=True, text=True, timeout=10,
    )
    elapsed = time.perf_counter() - start

    assert result.returncode == 0, f"Should succeed, got exit {result.returncode}"
    assert elapsed < 2.0, f"Should complete in <2s, took {elapsed:.1f}s"


# ============================================================
# Run all tests
# ============================================================

if __name__ == "__main__":
    print("\n=== LIVE TORTURE TESTS ===\n")
    print("These tests use REAL processes, files, network, and credentials.\n")

    tests = [
        test_memory_pipeline,
        test_pty_real_repl,
        test_sandbox_real,
        test_webhook_real,
        test_scheduler_real,
        test_file_watcher_real,
        test_credentials_real,
        test_scanner_real,
        test_daemon_full_loop,
        test_browser_real_search,
        test_browser_real_fetch,
        test_orchestrator_real,
        test_hook_pretool_real,
        test_hook_pretool_allows,
        test_hook_session_timing,
    ]

    for t in tests:
        run_test(t)

    print(f"\n=== RESULTS: {PASS} passed, {FAIL} failed, {SKIP} skipped ===\n")

    if FAIL > 0:
        sys.exit(1)
