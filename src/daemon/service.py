"""Windows Service wrapper — runs the daemon as a persistent background service.

Install:   python -m src.daemon.service install
Start:     python -m src.daemon.service start
Stop:      python -m src.daemon.service stop
Remove:    python -m src.daemon.service remove
Status:    python -m src.daemon.service status

Alternatively, use Task Scheduler (no admin required):
  python -m src.daemon.service schedule    — creates a Task Scheduler entry
  python -m src.daemon.service unschedule  — removes the Task Scheduler entry
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
VENV_PYTHON = PROJECT_ROOT / "venv" / "Scripts" / "python.exe"
TASK_NAME = "AutonomousAIAgentDaemon"
STATE_FILE = Path.home() / ".claude" / "daemon" / "daemon-pid.json"


def _write_state(pid: int, status: str):
    """Write daemon state to a file for status checks."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({
        "pid": pid,
        "status": status,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "python": str(VENV_PYTHON),
    }), encoding="utf-8")


def _read_state() -> dict:
    """Read daemon state."""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}


def _is_running(pid: int) -> bool:
    """Check if a process with the given PID is running."""
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True, text=True, timeout=5,
        )
        return str(pid) in result.stdout
    except Exception:
        return False


def cmd_start():
    """Start the daemon as a background process."""
    state = _read_state()
    if state.get("pid") and _is_running(state["pid"]):
        print(f"Daemon already running (PID {state['pid']})")
        return

    # Launch the daemon script as a detached process
    daemon_script = PROJECT_ROOT / "scripts" / "daemon-run.py"
    if not daemon_script.exists():
        _create_daemon_runner(daemon_script)

    proc = subprocess.Popen(
        [str(VENV_PYTHON), str(daemon_script)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
    )
    _write_state(proc.pid, "running")
    print(f"Daemon started (PID {proc.pid})")


def cmd_stop():
    """Stop the running daemon."""
    state = _read_state()
    pid = state.get("pid")
    if not pid:
        print("No daemon running.")
        return

    if not _is_running(pid):
        print(f"Daemon PID {pid} is not running (stale state).")
        STATE_FILE.unlink(missing_ok=True)
        return

    try:
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/F"],
            capture_output=True, timeout=10,
        )
        print(f"Daemon stopped (PID {pid})")
    except Exception as e:
        print(f"Failed to stop daemon: {e}")

    STATE_FILE.unlink(missing_ok=True)


def cmd_status():
    """Check daemon status."""
    state = _read_state()
    pid = state.get("pid")

    if not pid:
        print("Daemon: not running")
        return

    if _is_running(pid):
        started = state.get("started_at", "unknown")
        print(f"Daemon: running (PID {pid}, started {started})")
    else:
        print(f"Daemon: dead (PID {pid} not found, stale state)")
        STATE_FILE.unlink(missing_ok=True)


def cmd_schedule():
    """Create a Windows Task Scheduler entry to start the daemon at login."""
    daemon_script = PROJECT_ROOT / "scripts" / "daemon-run.py"
    if not daemon_script.exists():
        _create_daemon_runner(daemon_script)

    try:
        subprocess.run([
            "schtasks", "/Create",
            "/TN", TASK_NAME,
            "/TR", f'"{VENV_PYTHON}" "{daemon_script}"',
            "/SC", "ONLOGON",
            "/RL", "LIMITED",
            "/F",
        ], check=True, capture_output=True, text=True)
        print(f"Task Scheduler entry created: {TASK_NAME}")
        print("Daemon will start automatically at login.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to create scheduled task: {e.stderr}")


def cmd_unschedule():
    """Remove the Task Scheduler entry."""
    try:
        subprocess.run(
            ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
            check=True, capture_output=True, text=True,
        )
        print(f"Task Scheduler entry removed: {TASK_NAME}")
    except subprocess.CalledProcessError as e:
        print(f"Failed to remove scheduled task: {e.stderr}")


def _create_daemon_runner(path: Path):
    """Create the standalone daemon runner script."""
    path.write_text(f'''#!/usr/bin/env python3
"""Standalone daemon runner — launched by service.py or Task Scheduler."""
import sys
sys.path.insert(0, r"{PROJECT_ROOT}")

from src.daemon.events import EventBus
from src.daemon.state import DaemonState
from src.daemon.loop import DaemonLoop, LoopConfig

def main():
    bus = EventBus()
    state = DaemonState()
    config = LoopConfig(poll_interval=5.0)
    loop = DaemonLoop(bus, state, config)
    loop.start()
    try:
        import time
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        loop.stop()
        state.close()

if __name__ == "__main__":
    main()
''', encoding="utf-8")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    cmd = sys.argv[1]
    commands = {
        "start": cmd_start,
        "stop": cmd_stop,
        "status": cmd_status,
        "schedule": cmd_schedule,
        "unschedule": cmd_unschedule,
    }

    if cmd in commands:
        commands[cmd]()
        return 0
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        return 1


if __name__ == "__main__":
    sys.exit(main() or 0)
