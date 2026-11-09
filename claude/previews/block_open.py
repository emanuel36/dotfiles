#!/usr/bin/env python3
"""PreToolUse hook: block a Bash command that opens a preview from localhost:8765.

The SessionStart hook opens a window on the secondary monitor for every written preview, so a
command opening one only duplicates it. Exit 2 blocks the call.
"""

import json
import re
import sys

OPENS_PREVIEW = re.compile(r"\b(google-chrome\S*|chromium\S*|xdg-open)\b[^\n]*localhost:8765")

command = json.load(sys.stdin).get("tool_input", {}).get("command", "")
if OPENS_PREVIEW.search(command):
    print("The preview server opens a window for every file written to /tmp/previews; writing the "
          "file is enough. Do not open previews with a command.", file=sys.stderr)
    sys.exit(2)
