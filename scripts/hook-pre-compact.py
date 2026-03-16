#!/usr/bin/env python3
"""Claude Code PreCompact hook — pins critical rules before context compression.

Wire this into ~/.claude/hooks.json:
{
  "hooks": {
    "PreCompact": [{
      "type": "command",
      "command": "python C:/Users/Owner/Documents/autonomous-ai-agent/scripts/hook-pre-compact.py"
    }]
  }
}
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.memory.store import MemoryStore
from src.hooks.pin import pre_compact_pin


def main():
    store = MemoryStore()
    pre_compact_pin(store)
    store.close()


if __name__ == "__main__":
    main()
