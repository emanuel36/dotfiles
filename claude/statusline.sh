#!/bin/bash

input=$(cat)

IFS=$'\x1f' read -r model effort ctx_pct cwd transcript duration_ms lines_added lines_removed \
  cost <<<"$(echo "$input" | jq -r '[
    .model.display_name // .model.id // "Claude",
    .effort.level // "",
    .context_window.used_percentage // "",
    .cwd // "",
    .transcript_path // "",
    .cost.total_api_duration_ms // "",
    .cost.total_lines_added // 0,
    .cost.total_lines_removed // 0,
    .cost.total_cost_usd // ""
  ] | map(tostring) | join("\u001f")')"
[ -z "$effort" ] && effort=$(jq -r '.effortLevel // empty' ~/.claude/settings.json 2>/dev/null)

# Nerd Font glyphs, all rendered in a single neutral color (no gradient).
ICON_SPINNER=$'\uf110'
ICON_FOLDER_OPEN=$'\uf07c'
ICON_MICROCHIP=$'\uf2db'
ICON_COMMENT=$'\uf075'
ICON_CLOCK=$'\uf017'

NEUTRAL='\033[38;2;150;150;150m'
WARN='\033[38;2;232;178;96m'
HOT='\033[38;2;232;116;116m'
RESET='\033[0m'
SEP="$(printf "${NEUTRAL} | ${RESET}")"

# Prints the alert color for percentage $1: WARN from $2, HOT from $3, empty below.
alert_color() {
  if [ "$1" -ge "$3" ]; then
    printf "%s" "$HOT"
  elif [ "$1" -ge "$2" ]; then
    printf "%s" "$WARN"
  fi
}

# Formats milliseconds as 42m, 2h15m or 1d10h.
format_duration() {
  local m=$(($1 / 60000))
  if [ "$m" -lt 60 ]; then
    printf "%dm" "$m"
  elif [ "$m" -lt 1440 ]; then
    printf "%dh%02dm" $((m / 60)) $((m % 60))
  else
    printf "%dd%dh" $((m / 1440)) $((m % 1440 / 60))
  fi
}

out="$(printf "${NEUTRAL}%s${RESET} %s" "$ICON_SPINNER" "$model")"
[ -n "$effort" ] && out+=" $(printf "${NEUTRAL}· %s${RESET}" "$effort")"

if [ -n "$ctx_pct" ]; then
  ctx_pct_int=${ctx_pct%.*}
  [ "$ctx_pct_int" -gt 100 ] 2>/dev/null && ctx_pct_int=100
  # Context percentage turns amber at 70% and red at 85% (from claude-code-usage-bar).
  ctx_color=$(alert_color "$ctx_pct_int" 70 85)
  out+="$SEP$(printf "${NEUTRAL}%s ${ctx_color:-$NEUTRAL}%d%%${RESET}" \
    "$ICON_MICROCHIP" "$ctx_pct_int")"
fi

[ -n "$cost" ] && out+="$SEP$(printf "${NEUTRAL}\$%.2f${RESET}" "$cost")"

# Prompts typed by the user (tool results, meta and system entries are not "human").
if [ -f "$transcript" ]; then
  prompts=$(rg '"kind":"human"' "$transcript" 2>/dev/null |
    jq -c 'select(.type == "user" and .origin.kind == "human")' 2>/dev/null | wc -l)
  out+="$SEP$(printf "${NEUTRAL}%s %d${RESET}" "$ICON_COMMENT" "$prompts")"
fi

[ -n "$duration_ms" ] &&
  out+="$SEP$(printf "${NEUTRAL}%s %s${RESET}" \
    "$ICON_CLOCK" "$(format_duration "${duration_ms%.*}")")"

[ "$lines_added" -gt 0 ] || [ "$lines_removed" -gt 0 ] &&
  out+="$SEP$(printf "${NEUTRAL}+%d -%d${RESET}" "$lines_added" "$lines_removed")"

[ -n "$cwd" ] && out+="$SEP$(printf "${NEUTRAL}%s${RESET} %s" "$ICON_FOLDER_OPEN" "${cwd##*/}")"

printf "%s" "$out"
