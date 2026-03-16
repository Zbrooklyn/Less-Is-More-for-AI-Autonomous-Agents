#!/usr/bin/env python3
"""Claude Code PreToolUse hook — enforces rules before tool execution.

Wire this into ~/.claude/hooks.json:
{
  "hooks": {
    "PreToolUse": [{
      "type": "command",
      "command": "python C:/Users/Owner/Documents/autonomous-ai-agent/scripts/hook-pre-tool-call.py",
      "timeout": 5000
    }]
  }
}

The hook receives JSON on stdin with the tool call details.
Exit code 0 = allow, exit code 2 = block with message on stderr.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.memory.store import MemoryStore
from src.hooks.enforce import enforce, format_enforcement


def main():
    # Read tool call from stdin
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
    tool_input = ""

    # Extract the relevant input based on tool type
    params = data.get("tool_input", {})
    if tool == "Bash":
        tool_input = params.get("command", "")
    elif tool in ("Write", "Edit"):
        tool_input = params.get("content", "") or params.get("new_string", "")
        # Also check file path
        tool_input += " " + params.get("file_path", "")
    else:
        tool_input = json.dumps(params)

    if not tool_input:
        return 0

    store = MemoryStore()
    result = enforce(store, tool, tool_input)
    store.close()

    if not result.allowed:
        # Exit code 2 = block with reason
        print(format_enforcement(result), file=sys.stderr)
        return 2

    if result.action == "warn":
        print(format_enforcement(result), file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
