#!/usr/bin/env bash
# SessionStart hook: once a day, open a page summarizing the trending repositories not seen yet.
#
# In the background, collects the repositories with trending.py into $workdir/repos.json and
# hands them to an unattended `claude -p` run of the trending-repos skill, which summarizes them
# and runs render_page.py to build the page, open it in Chrome and mark the repos as seen. The
# day only counts as done once render_page.py marks them (it writes $state/last-run), or when no
# source failed and none had anything new, so a day when the network, Claude or the display was
# down is retried at the next session start, at most every 30 minutes. Returns at once and prints
# nothing. The run's log is in $state/run.log.
#
# TRENDING_DRY_RUN=1 runs in the foreground and prints the command instead of starting it.
set -euo pipefail

# The background run starts a session of its own; it must not fire another run.
[[ -n "${TRENDING_RUN:-}" ]] && exit 0

skill="$HOME/.claude/skills/trending-repos"
state="${XDG_STATE_HOME:-$HOME/.local/state}/trending-repos"
workdir=/tmp/trending-repos
today=$(date +%F)
dry="${TRENDING_DRY_RUN:-}"

run() {
    local repos="$workdir/repos.json" summaries="$workdir/summaries.json" prompt
    # The page can only open on a display; without one, fetching and summarizing would be paid
    # for nothing.
    if [[ -z "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]]; then
        echo "== $(date -Is) no display, retrying later"
        return 0
    fi
    python3 "$skill/scripts/trending.py" fetch > "$repos"
    if [[ "$(jq '.repos | length' "$repos")" -eq 0 ]]; then
        echo "== $(date -Is) nothing new: $(jq -c .failed "$repos")"
        [[ -z "$dry" && "$(jq '.failed | length' "$repos")" -eq 0 ]] \
            && echo "$today" > "$state/last-run"
        return 0
    fi
    rm -f "$summaries"

    prompt="Use the trending-repos skill. This is an unattended run from the session-start hook: \
the repositories are already fetched in $repos. Write their summaries to $summaries, then build \
the page with exactly this command: \
python3 $skill/scripts/render_page.py $repos $summaries"
    local command=(
        claude -p "$prompt"
        --permission-mode dontAsk
        --allowedTools
        "Skill(trending-repos)"
        # "//" makes the path absolute; Edit rules also cover the Write tool.
        "Read(/$workdir/**)" "Edit(/$workdir/**)"
        "Bash(python3 $skill/scripts/render_page.py $repos $summaries)"
    )
    if [[ -n "$dry" ]]; then
        printf '%q ' "${command[@]}"
        echo
        return 0
    fi
    echo "== $(date -Is) summarizing $(jq '.repos | length' "$repos") repositories"
    cd "$workdir"
    TRENDING_RUN=1 "${command[@]}" < /dev/null
}

mkdir -p "$state" "$workdir"
if [[ -n "$dry" ]]; then
    run
    exit 0
fi
[[ "$(cat "$state/last-run" 2>/dev/null)" == "$today" ]] && exit 0
# Several sessions often start together: one run at a time, holding the lock until it ends, and
# none within 30 minutes of the last attempt.
exec 9> "$state/lock"
flock -n 9 || exit 0
last_attempt=$(stat -c %Y "$state/last-attempt" 2>/dev/null || echo 0)
(( $(date +%s) - last_attempt < 1800 )) && exit 0
touch "$state/last-attempt"

export -f run
export skill state workdir today dry
setsid bash -c run < /dev/null >> "$state/run.log" 2>&1 &
