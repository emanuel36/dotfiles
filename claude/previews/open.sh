#!/bin/sh
# SessionStart hook: starts the preview server and opens one preview window on the secondary
# monitor. The window follows the latest preview, so new previews need no command to show up.

url=http://localhost:8765/

if ! curl -s -o /dev/null "$url"; then
  setsid -f python3 "$HOME/.dotfiles/claude/previews/serve.py" >/dev/null 2>&1
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    curl -s -o /dev/null "$url" && break
    sleep 0.3
  done
fi

[ -n "$DISPLAY" ] || exit 0
xdotool search --classname '^localhost' >/dev/null 2>&1 && exit 0

# Secondary monitor = first one without the primary mark, e.g. "1080/527x1920/296+0+0".
set -- $(xrandr --listmonitors | awk 'NR > 1 && $2 !~ /\*/ { print $3; exit }' |
  sed -E 's#^([0-9]+)/[0-9]+x([0-9]+)/[0-9]+\+([0-9]+)\+([0-9]+)$#\1 \2 \3 \4#')

if [ $# -eq 4 ]; then
  setsid -f google-chrome --app="$url" --window-position="$3,$4" --window-size="$1,$2" \
    >/dev/null 2>&1
  # Chrome may ignore the position when it is already running, so move the window too.
  setsid -f timeout 15 xdotool search --sync --classname '^localhost' \
    windowmove %@ "$3" "$4" windowsize %@ "$1" "$2" >/dev/null 2>&1
else
  setsid -f google-chrome --app="$url" >/dev/null 2>&1
fi
exit 0
