#!/usr/bin/env bash
# SessionStart hook: once a day, recap the days missing from the work diary in the background.
#
# Picks, among the last 7 days before today, those with no recap yet that were never requested
# before (so empty weekends are not retried every day), and hands them to an unattended
# `claude -p` run of the daily-recap skill. Returns at once and prints nothing, so the session
# that fired it starts as usual. The run's log is in $state/run.log.
#
# DAILY_RECAP_DRY_RUN=1 prints the command instead of starting it and records nothing.
set -euo pipefail

# The background run starts a session of its own; it must not fire another run.
[[ -n "${DAILY_RECAP_RUN:-}" ]] && exit 0

skill="$HOME/.claude/skills/daily-recap"
diary="$HOME/.dotfiles/diary"
state="${XDG_STATE_HOME:-$HOME/.local/state}/daily-recap"
workdir=/tmp/daily-recap
today=$(date +%F)
dry="${DAILY_RECAP_DRY_RUN:-}"

mkdir -p "$state" "$workdir"
[[ -z "$dry" && "$(cat "$state/last-run" 2>/dev/null)" == "$today" ]] && exit 0

days=()
for i in 7 6 5 4 3 2 1; do
    day=$(date -d "$today -$i day" +%F)
    [[ -e "$diary/$day.recap.json" ]] && continue
    grep -qxF "$day" "$state/requested" 2>/dev/null && continue
    days+=("$day")
done

[[ -z "$dry" ]] && echo "$today" > "$state/last-run"
[[ ${#days[@]} -eq 0 ]] && exit 0

prompt="Use the daily-recap skill. This is an unattended run from the session-start hook: \
recap these days, oldest first: ${days[*]}. Skip any day with no activity."
command=(
    claude -p "$prompt"
    --permission-mode dontAsk
    --allowedTools
    "Skill(daily-recap)" "Read" "ToolSearch"
    "Bash(python3 $skill/scripts/extract_day.py *)"
    "Bash(python3 $skill/scripts/render_recap.py *)"
    "Edit(~/.dotfiles/diary/**)" "Edit(/tmp/daily-recap/**)"
    "mcp__plugin_slack_slack__slack_search_public_and_private"
    "mcp__plugin_slack_slack__slack_read_thread"
    "mcp__claude_ai_Slack__slack_search_public_and_private"
    "mcp__claude_ai_Slack__slack_read_thread"
)

if [[ -n "$dry" ]]; then
    printf '%q ' "${command[@]}"
    echo
    exit 0
fi

printf '%s\n' "${days[@]}" >> "$state/requested"
# Runs from /tmp, which the extractor skips, so the run never shows up in a recap of its own.
cd "$workdir"
{
    echo "== $(date -Is) recapping ${days[*]}"
    DAILY_RECAP_RUN=1 setsid "${command[@]}" < /dev/null >> "$state/run.log" 2>&1 &
} >> "$state/run.log"
