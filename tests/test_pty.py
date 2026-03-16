"""Tests for PTY session manager — interactive subprocess sessions."""

import sys
import time

import pytest

from src.pty.session import PTYSession, SessionManager

# Use python.exe for testing — reliable cross-platform subprocess
PYTHON = sys.executable


def _drain_until_ready(session: PTYSession, marker: str = ">>>", timeout: float = 10.0) -> str:
    """Keep reading from session until we see the marker or timeout.

    This ensures the Python REPL banner is fully consumed before we
    start sending commands, even under heavy system load.
    """
    collected = ""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        chunk = session.read(timeout=1.0)
        collected += chunk
        if marker in collected:
            return collected
    return collected


def _send_and_collect(session: PTYSession, command: str, expected: str, timeout: float = 10.0) -> str:
    """Send a command and collect output until expected string appears or timeout.

    Returns all collected output (may include prompt characters).
    """
    session.send(command)
    collected = ""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        chunk = session.read(timeout=1.0)
        collected += chunk
        if expected in collected:
            return collected
    return collected


class TestPTYSessionStartAndAlive:
    def test_start_creates_running_process(self):
        session = PTYSession()
        try:
            session.start(command=f'"{PYTHON}" -i')
            assert session.is_alive()
        finally:
            session.close()

    def test_is_alive_false_before_start(self):
        session = PTYSession()
        assert not session.is_alive()

    def test_start_twice_raises(self):
        session = PTYSession()
        try:
            session.start(command=f'"{PYTHON}" -i')
            with pytest.raises(RuntimeError, match="already running"):
                session.start(command=f'"{PYTHON}" -i')
        finally:
            session.close()


class TestPTYSessionSendAndRead:
    def test_send_and_read_roundtrip(self):
        """Send an echo command and read back the output."""
        session = PTYSession()
        try:
            session.start(command=f'"{PYTHON}" -i')
            _drain_until_ready(session)

            output = _send_and_collect(session, "print('hello_pty_test')", "hello_pty_test")
            assert "hello_pty_test" in output
        finally:
            session.close()

    def test_send_to_dead_process_raises(self):
        session = PTYSession()
        with pytest.raises(RuntimeError, match="No running process"):
            session.send("test")

    def test_multiple_send_read_cycles(self):
        session = PTYSession()
        try:
            session.start(command=f'"{PYTHON}" -i')
            _drain_until_ready(session)

            out1 = _send_and_collect(session, "print('first')", "first")
            assert "first" in out1

            out2 = _send_and_collect(session, "print('second')", "second")
            assert "second" in out2
        finally:
            session.close()


class TestPTYSessionClose:
    def test_close_terminates_process(self):
        session = PTYSession()
        session.start(command=f'"{PYTHON}" -i')
        assert session.is_alive()
        session.close()
        assert not session.is_alive()

    def test_close_idempotent(self):
        """Closing an already-closed session should not raise."""
        session = PTYSession()
        session.start(command=f'"{PYTHON}" -i')
        session.close()
        session.close()  # Should not raise
        assert not session.is_alive()


class TestPTYSessionContextManager:
    def test_context_manager_cleanup(self):
        with PTYSession() as session:
            session.start(command=f'"{PYTHON}" -i')
            assert session.is_alive()
        # After exiting context, process should be terminated
        assert not session.is_alive()

    def test_context_manager_returns_session(self):
        with PTYSession() as session:
            assert isinstance(session, PTYSession)


class TestPTYSessionReadTimeout:
    def test_read_timeout_on_no_output(self):
        """Read should return empty string after timeout when no output."""
        session = PTYSession()
        try:
            session.start(command=f'"{PYTHON}" -i')
            _drain_until_ready(session)

            # Don't send anything — read should time out
            start = time.monotonic()
            output = session.read(timeout=0.5)
            elapsed = time.monotonic() - start
            # Should return quickly-ish (within 3x timeout to tolerate load)
            assert elapsed < 3.0
            # Output may be empty or just a prompt
            # The key test is that it didn't hang
        finally:
            session.close()


class TestSessionManagerCreateGetClose:
    def test_create_and_get(self):
        manager = SessionManager()
        try:
            session = manager.create("test1", command=f'"{PYTHON}" -i')
            assert session.is_alive()
            retrieved = manager.get("test1")
            assert retrieved is session
        finally:
            manager.close_all()

    def test_create_duplicate_raises(self):
        manager = SessionManager()
        try:
            manager.create("dup", command=f'"{PYTHON}" -i')
            with pytest.raises(ValueError, match="already exists"):
                manager.create("dup", command=f'"{PYTHON}" -i')
        finally:
            manager.close_all()

    def test_get_nonexistent_raises(self):
        manager = SessionManager()
        with pytest.raises(KeyError, match="not found"):
            manager.get("nonexistent")

    def test_close_session(self):
        manager = SessionManager()
        manager.create("to_close", command=f'"{PYTHON}" -i')
        manager.close("to_close")
        with pytest.raises(KeyError, match="not found"):
            manager.get("to_close")

    def test_close_nonexistent_raises(self):
        manager = SessionManager()
        with pytest.raises(KeyError, match="not found"):
            manager.close("nonexistent")

    def test_close_all(self):
        manager = SessionManager()
        manager.create("s1", command=f'"{PYTHON}" -i')
        manager.create("s2", command=f'"{PYTHON}" -i')
        assert len(manager.list_sessions()) == 2
        manager.close_all()
        assert len(manager.list_sessions()) == 0

    def test_send_and_read_through_manager(self):
        """Send/read via manager with robust collection."""
        manager = SessionManager()
        try:
            manager.create("echo_test", command=f'"{PYTHON}" -i')
            session = manager.get("echo_test")
            _drain_until_ready(session)

            output = _send_and_collect(session, "print('managed_output')", "managed_output")
            assert "managed_output" in output
        finally:
            manager.close_all()


class TestSessionManagerListSessions:
    def test_list_empty(self):
        manager = SessionManager()
        assert manager.list_sessions() == []

    def test_list_with_sessions(self):
        manager = SessionManager()
        try:
            manager.create("a", command=f'"{PYTHON}" -i')
            manager.create("b", command=f'"{PYTHON}" -i')
            sessions = manager.list_sessions()
            names = {s["name"] for s in sessions}
            assert names == {"a", "b"}
            assert all(s["status"] == "alive" for s in sessions)
        finally:
            manager.close_all()

    def test_list_shows_dead_status(self):
        manager = SessionManager()
        try:
            manager.create("mortal", command=f'"{PYTHON}" -i')
            # Send exit() to make it terminate
            manager.send("mortal", "exit()")
            # Wait for the process to die
            deadline = time.monotonic() + 10.0
            while time.monotonic() < deadline:
                sessions = manager.list_sessions()
                if sessions and sessions[0]["status"] == "dead":
                    break
                time.sleep(0.2)
            sessions = manager.list_sessions()
            assert len(sessions) == 1
            assert sessions[0]["name"] == "mortal"
            assert sessions[0]["status"] == "dead"
        finally:
            manager.close_all()
