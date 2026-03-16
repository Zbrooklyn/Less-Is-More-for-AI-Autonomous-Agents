"""Interactive PTY session manager using subprocess pipes.

Windows-compatible: uses subprocess.Popen with stdin/stdout/stderr pipes
and a background reader thread for non-blocking output collection.
"""

import subprocess
import sys
import threading
import time
from typing import Dict, List, Optional


class PTYSession:
    """Manages an interactive subprocess session with piped I/O.

    Uses a background thread to continuously read stdout/stderr into a
    buffer, enabling non-blocking reads with timeout.
    """

    def __init__(self) -> None:
        self._process: Optional[subprocess.Popen] = None
        self._output_buffer: List[str] = []
        self._buffer_lock = threading.Lock()
        self._reader_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self, command: str = "cmd.exe") -> None:
        """Start a subprocess with piped stdin/stdout/stderr.

        Args:
            command: The command to execute. Defaults to cmd.exe on Windows.
        """
        if self._process is not None and self._process.poll() is None:
            raise RuntimeError("Session already running. Close it first.")

        # Reset state
        self._output_buffer = []
        self._stop_event.clear()

        self._process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,  # line-buffered
            shell=True,
        )

        # Start background reader thread
        self._reader_thread = threading.Thread(
            target=self._read_loop, daemon=True
        )
        self._reader_thread.start()

    def _read_loop(self) -> None:
        """Background thread that reads process stdout into the buffer."""
        assert self._process is not None
        assert self._process.stdout is not None
        try:
            for line in iter(self._process.stdout.readline, ""):
                if self._stop_event.is_set():
                    break
                with self._buffer_lock:
                    self._output_buffer.append(line)
        except (ValueError, OSError):
            # Pipe closed or process terminated
            pass

    def send(self, text: str) -> None:
        """Send input text to the running process.

        Args:
            text: Text to send. A newline is appended if not present.

        Raises:
            RuntimeError: If no process is running.
        """
        if self._process is None or self._process.poll() is not None:
            raise RuntimeError("No running process to send input to.")
        if self._process.stdin is None:
            raise RuntimeError("Process stdin is not available.")

        if not text.endswith("\n"):
            text += "\n"
        self._process.stdin.write(text)
        self._process.stdin.flush()

    def read(self, timeout: float = 5.0) -> str:
        """Read available output from the process buffer.

        Waits up to `timeout` seconds for output to appear, then returns
        all buffered lines. Returns empty string if no output within timeout.

        Args:
            timeout: Maximum seconds to wait for output. Defaults to 5.0.

        Returns:
            Collected output as a string.
        """
        deadline = time.monotonic() + timeout
        # Wait for at least some output or timeout
        while time.monotonic() < deadline:
            with self._buffer_lock:
                if self._output_buffer:
                    break
            time.sleep(0.05)

        # Small extra delay to collect more output that may still be streaming
        time.sleep(0.1)

        with self._buffer_lock:
            output = "".join(self._output_buffer)
            self._output_buffer.clear()
        return output

    def is_alive(self) -> bool:
        """Check if the subprocess is still running.

        Returns:
            True if the process is running, False otherwise.
        """
        if self._process is None:
            return False
        return self._process.poll() is None

    def close(self) -> None:
        """Terminate the subprocess and clean up resources."""
        self._stop_event.set()
        if self._process is not None:
            if self._process.stdin:
                try:
                    self._process.stdin.close()
                except OSError:
                    pass
            if self._process.poll() is None:
                try:
                    self._process.terminate()
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._process.kill()
                    self._process.wait(timeout=5)
            self._process = None
        if self._reader_thread is not None:
            self._reader_thread.join(timeout=3)
            self._reader_thread = None

    def __enter__(self) -> "PTYSession":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


class SessionManager:
    """Manages multiple named PTY sessions."""

    def __init__(self) -> None:
        self._sessions: Dict[str, PTYSession] = {}

    def create(self, name: str, command: str = "cmd.exe") -> PTYSession:
        """Create and start a new named session.

        Args:
            name: Unique name for the session.
            command: Command to run. Defaults to cmd.exe.

        Returns:
            The created PTYSession.

        Raises:
            ValueError: If a session with this name already exists.
        """
        if name in self._sessions:
            raise ValueError(f"Session '{name}' already exists.")
        session = PTYSession()
        session.start(command)
        self._sessions[name] = session
        return session

    def get(self, name: str) -> PTYSession:
        """Get an existing session by name.

        Args:
            name: Session name.

        Returns:
            The PTYSession.

        Raises:
            KeyError: If no session with this name exists.
        """
        if name not in self._sessions:
            raise KeyError(f"Session '{name}' not found.")
        return self._sessions[name]

    def send(self, name: str, text: str) -> None:
        """Send input to a named session.

        Args:
            name: Session name.
            text: Text to send.
        """
        self.get(name).send(text)

    def read(self, name: str, timeout: float = 5.0) -> str:
        """Read output from a named session.

        Args:
            name: Session name.
            timeout: Read timeout in seconds.

        Returns:
            Output string from the session.
        """
        return self.get(name).read(timeout=timeout)

    def close(self, name: str) -> None:
        """Close and remove a named session.

        Args:
            name: Session name.

        Raises:
            KeyError: If no session with this name exists.
        """
        if name not in self._sessions:
            raise KeyError(f"Session '{name}' not found.")
        self._sessions[name].close()
        del self._sessions[name]

    def close_all(self) -> None:
        """Close all sessions."""
        for session in self._sessions.values():
            session.close()
        self._sessions.clear()

    def list_sessions(self) -> List[Dict[str, str]]:
        """List all sessions with their status.

        Returns:
            List of dicts with 'name' and 'status' keys.
        """
        result = []
        for name, session in self._sessions.items():
            status = "alive" if session.is_alive() else "dead"
            result.append({"name": name, "status": status})
        return result

    def attach_debugger(self, name: str, script_path: str, debugger: str = "pdb") -> PTYSession:
        """Start a debugging session for a Python script.

        Args:
            name: Unique name for the debug session.
            script_path: Path to the Python script to debug.
            debugger: Debugger to use ("pdb" or "breakpoint"). Defaults to "pdb".

        Returns:
            The created PTYSession running the debugger.
        """
        python = sys.executable
        if debugger == "pdb":
            command = f"{python} -m pdb {script_path}"
        else:
            # Use default breakpoint() behavior
            command = f"{python} -m pdb {script_path}"
        return self.create(name, command)
