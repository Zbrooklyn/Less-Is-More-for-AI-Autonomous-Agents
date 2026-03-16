#!/usr/bin/env python3
"""Claude Code PostToolUse hook — verifies tool output for compliance.

Wire this into ~/.claude/hooks.json:
{
  "hooks": {
    "PostToolUse": [{
      "type": "command",
      "command": "python C:/Users/Owner/Documents/autonomous-ai-agent/scripts/hook-post-tool-call.py",
      "timeout": 5000
    }]
  }
}

Receives JSON on stdin with tool call + output. Logs violations but doesn't block.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.memory.store import MemoryStore
from src.hooks.verify import verify, format_verification


def main():
    try:
        if not sys.stdin.isatty():
            raw = sys.stdin.read()
            if raw.strip():
                data = json.loads(raw)
            else:
                return 0
        else:
            return 0
    except (json.JSONDecodeError, OSError):
        return 0

    tool = data.get("tool_name", "")
    params = data.get("tool_input", {})
    output = data.get("tool_output", "")

    # Build action description — include content for Write/Edit so violations are caught
    if tool == "Bash":
        action = params.get("command", "")
    elif tool == "Write":
        action = f"write to {params.get('file_path', '')}: {params.get('content', '')[:500]}"
    elif tool == "Edit":
        action = f"edit {params.get('file_path', '')}: {params.get('new_string', '')[:500]}"
    else:
        action = json.dumps(params)[:200]

    if not output and not action:
        return 0

    store = MemoryStore()
    result = verify(store, tool, action, str(output)[:2000])
    store.close()

    if not result.compliant or result.warnings:
        print(format_verification(result), file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
