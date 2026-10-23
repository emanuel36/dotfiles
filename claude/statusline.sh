#!/bin/bash

input=$(cat)

model=$(echo "$input" | jq -r '.model.display_name // .model.id // "Claude"')
cost=$(echo "$input" | jq -r '.cost.total_cost_usd // empty')
cwd=$(echo "$input" | jq -r '.cwd // empty')
ctx_pct=$(echo "$input" | jq -r '.context_window.used_percentage // empty')

# Nerd Font glyphs, all rendered in a single neutral color (no gradient).
ICON_SPINNER=$'\uf110'
ICON_FOLDER_OPEN=$'\uf07c'
ICON_MICROCHIP=$'\uf2db'

NEUTRAL='\033[38;2;150;150;150m'
RESET='\033[0m'

# Renders a 10-segment heavy/light square bar (filled/empty), neutral color.
render_bar() {
  local icon="$1" pct="$2"
  local pct_int=${pct%.*}
  [ "$pct_int" -gt 100 ] 2>/dev/null && pct_int=100

  local segs=10
  local filled=$((pct_int * segs / 100))
  local filled_char=$'▰'
  local empty_char=$'▱'
  local bar="" i
  for ((i = 0; i < segs; i++)); do
    if [ "$i" -lt "$filled" ]; then
      bar+="$filled_char"
    else
      bar+="$empty_char"
    fi
  done

  printf "${NEUTRAL}%s %s  %d%%${RESET}" "$icon" "$bar" "$pct_int"
}

# Lines changed in the working tree of $cwd (uncommitted diff vs HEAD).
git_diff_stat=""
if [ -n "$cwd" ] && git -C "$cwd" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  read -r added removed <<<"$(git -C "$cwd" diff --numstat 2>/dev/null | awk '{a+=$1; r+=$2} END {print a+0, r+0}')"
  [ "$added" -gt 0 ] || [ "$removed" -gt 0 ] && git_diff_stat="+${added} -${removed}"
fi

out="$(printf "${NEUTRAL}%s${RESET} %s" "$ICON_SPINNER" "$model")"

if [ -n "$ctx_pct" ]; then
  ctx_pct_int=${ctx_pct%.*}
  [ "$ctx_pct_int" -gt 100 ] 2>/dev/null && ctx_pct_int=100
  out="$out | $(printf "${NEUTRAL}%s %d%%${RESET}" "$ICON_MICROCHIP" "$ctx_pct_int")"
fi

[ -n "$cost" ] && out="$out | $(printf "${NEUTRAL}\$%.2f${RESET}" "$cost")"

[ -n "$cwd" ] && out="$out | $(printf "${NEUTRAL}%s${RESET} %s" "$ICON_FOLDER_OPEN" "${cwd##*/}")"
[ -n "$git_diff_stat" ] && out="$out | $(printf "${NEUTRAL}%s${RESET}" "$git_diff_stat")"

printf "%s" "$out"
