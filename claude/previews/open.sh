#!/bin/sh
# SessionStart hook: starts the preview server unless it is already running. The server opens
# a window on the secondary monitor whenever a preview is written, so no command is needed.

if ! curl -s -o /dev/null http://localhost:8765/; then
  setsid -f python3 "$HOME/.dotfiles/claude/previews/serve.py" >/dev/null 2>&1
fi
exit 0
