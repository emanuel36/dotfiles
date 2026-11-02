---
name: trending-repos
description: >-
  Open in a Chrome tab group the GitHub repositories that are trending or newly launched today
  and that the user has not seen yet: the Trendshift daily ranking, Show HN posts that link a
  GitHub repo, and repositories created this week that already gathered stars. Remembers every
  repo it opened so a repo trending for several days shows up only once. Runs unattended once a
  day from a session-start hook. Use this whenever the user wants to see what is trending on
  GitHub, catch up on new repositories or open-source projects, open today's trending repos, or
  asks about the trending list or the seen history ("o que está em alta hoje", "abre os repos
  em alta", "repos novos", "trending do GitHub", "Trendshift", "já vi esse repo?"), even if they
  do not name the skill. Not for searching GitHub for a specific library, reviewing a repo's
  code, or managing the user's own repositories or stars.
---

# Trending repositories

The user keeps up with new open-source projects by reading the repository pages themselves.
This skill saves the two chores around that: hopping from a ranking site to each GitHub page, and
noticing only on the GitHub page that a repo was already read yesterday. So it opens GitHub pages
directly, in one tab group the user closes when done, and never opens the same repo twice.

## Tools

- `scripts/trending.py fetch` prints `{"repos": [{name, reason, url}], "left_for_later": N,
  "failed": [...]}`: the unseen repos, Trendshift first by rank, then Show HN, then new on
  GitHub, capped at 30 (`TRENDING_MAX_TABS`). Fetching records nothing.
- `scripts/trending.py mark-seen owner/repo …` records repos as seen in
  `~/.local/state/trending-repos/seen.json` and marks the day as done for the hook.
- `scripts/catch_up.sh` is the session-start hook. It fetches the list and starts an
  unattended run of this skill with it, once a day; a day that did not finish is retried at the
  next session start.

## Opening the repositories

1. **Get the list.** An unattended run receives it in the prompt. Otherwise run
   `python3 ~/.claude/skills/trending-repos/scripts/trending.py fetch`. If `repos` is empty, say
   there is nothing new and stop.
2. **Open the tab group.** Load the Chrome tools with one `ToolSearch` call
   (`tabs_context_mcp`, `tabs_create_mcp`, `navigate`, `browser_batch`). Call
   `tabs_context_mcp` with `createIfEmpty: true`, which opens a new window holding this run's
   tab group with one empty tab. If the extension is not connected, stop here without marking
   anything: the repos stay unseen and the hook retries later.
3. **Open every repo.** Navigate the empty tab to the first URL, then for each other repo create
   a tab and navigate it. Batch the calls with `browser_batch` to save round trips. Leave the
   tabs open: the user reads them and closes the group. Do not read or screenshot the pages.
4. **Mark what opened.** Run `trending.py mark-seen` with the names of the repos whose tabs
   actually opened, in one call. In an unattended run, use the exact command the prompt gives:
   only that form is allowed. A repo that failed to open stays unseen, so it can come back
   tomorrow.
5. **Report** in one short paragraph: how many opened, from which sources, and anything in
   `failed` or `left_for_later`. A source in `failed` usually means its page or API changed;
   say which, so the user knows the list was partial.

In an unattended run nobody is there to answer: ask nothing and finish after step 5.

## Other requests

- **"Já vi esse repo?"**: look the name up in `seen.json`; it holds the first day each was seen.
- **More tabs than the cap, or fewer**: pass `TRENDING_MAX_TABS=<n>` to `fetch`.
- **Open again today**: the hook runs once a day; an interactive request runs steps 1-5 at any
  time and opens only what is still unseen.
