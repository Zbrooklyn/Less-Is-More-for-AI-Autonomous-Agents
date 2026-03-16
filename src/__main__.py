"""Entry point for `python -m src` — run any subsystem."""

import sys


USAGE = """
Autonomous AI Agent — Subsystem Launcher

Usage:
  python -m src memory [args]      Run memory-cli (query/add/stats/enforce/capture/verify/pin)
  python -m src cred [args]        Run credential-cli (get/set/delete/list/scan/redact)
  python -m src daemon             Start the daemon event loop
  python -m src sandbox [args]     Run sandbox-cli (create/run/list/diff/destroy)
  python -m src pty [args]         Run PTY session manager (create/send/read/list/close)
  python -m src audio [args]       Run audio-cli (record/transcribe/speak/devices/voices)

Examples:
  python -m src memory stats
  python -m src memory enforce --tool Bash --input "pythonw.exe test.py"
  python -m src memory capture "Don't use pythonw.exe"
  python -m src cred scan "my key is sk-abc123"
  python -m src daemon
  python -m src audio record 5 --output speech.wav
""".strip()


def main():
    if len(sys.argv) < 2:
        print(USAGE)
        return 1

    subsystem = sys.argv[1]
    # Remove the subsystem arg so the sub-CLI sees clean argv
    sub_argv = sys.argv[2:]

    if subsystem == "memory":
        from src.memory.cli import main as memory_main
        return memory_main(sub_argv)

    elif subsystem == "cred":
        from src.credentials.cli import main as cred_main
        return cred_main(sub_argv)

    elif subsystem == "daemon":
        from src.daemon.events import EventBus
        from src.daemon.state import DaemonState
        from src.daemon.loop import DaemonLoop, LoopConfig

        print("Starting daemon...")
        bus = EventBus()
        state = DaemonState()
        config = LoopConfig(
            poll_interval=2.0,
            notification_callback=lambda msg: print(f"[DAEMON] {msg}"),
        )
        loop = DaemonLoop(bus, state, config)
        loop.start()
        print("Daemon running. Press Ctrl+C to stop.")
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping daemon...")
            loop.stop()
            state.close()
            print("Daemon stopped.")
        return 0

    elif subsystem == "sandbox":
        from src.sandbox.cli import main as sandbox_main
        return sandbox_main(sub_argv)

    elif subsystem == "pty":
        from src.pty.cli import main as pty_main
        return pty_main(sub_argv)

    elif subsystem == "audio":
        from src.audio.cli import main as audio_main
        return audio_main(sub_argv)

    else:
        print(f"Unknown subsystem: {subsystem}")
        print(USAGE)
        return 1


if __name__ == "__main__":
    sys.exit(main() or 0)
