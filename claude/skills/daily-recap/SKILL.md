---
name: daily-recap
description: >-
  Build an overview of one day of work from the user's Claude Code sessions and their own Slack
  messages: what each initiative delivered, split into work and own projects, with tickets,
  statuses, lines of code, commits and a timeline of the day, added to a searchable work diary
  page in ~/Documents/diario and ready to read out at the daily standup. Also runs unattended
  from a session-start hook to catch up on missing days. Use this whenever the user asks
  what they did today, yesterday or on a given date, wants a daily summary, diary, journal, recap
  or log of their work or of their Claude sessions, or wants material for their daily report
  ("o que eu fiz hoje", "resumo do dia", "resumo de ontem", "meu diário", "o que falo na daily",
  "daily recap", "what did I work on yesterday"), even if they do not say "recap". Not for
  posting a standup to Slack, sprint or Jira status reports, or summaries of a single
  conversation or channel.
---

# Daily recap

An overview of one day: where the time went and what came out of it. The user reads it at the
daily standup and weeks later to remember the day, so every line names an outcome ("Shipped Away
Mode") rather than an activity ("Worked on Away Mode"), and detail stops at what a teammate
would want to hear.

Write the page content in **English**. Talk to the user in their own language.

## Inputs and outputs

- **Days**: today unless the user names others ("ontem", "sexta", "2026-10-20", "a semana
  passada"). Resolve each to `YYYY-MM-DD` in local time and run steps 1-4 for each, oldest first.
  Skip a day with no Claude Code sessions and no Slack messages: nothing gets written for it.
- **Diary folder**: `~/Documents/diario/` keeps, per day, `<day>.notes.json` (your notes) and
  `<day>.recap.json` (what the page shows), plus `index.html`, the one page with every day.
  Re-running a day overwrites its files.
- **Digest**: `/tmp/daily-recap/<day>.json`. It holds the raw prompts, which can contain pasted
  passwords or tokens, so it stays out of the diary folder. Never copy a secret into the notes.
- **Unattended runs**: when the request says it comes from the session-start hook, nobody is
  there to answer. Ask nothing, decide ambiguous cases with the rules below, and do not open the
  browser.

## 1. Extract the sessions

```bash
python3 <skill-dir>/scripts/extract_day.py --date <day> --out /tmp/daily-recap/<day>.json
```

The script reads every transcript under `~/.claude/projects` (subagents included) and writes a
digest grouped by repository. Its docstring explains the rules; the ones that shape your reading:

- A session belongs to the repository of its working directory or, when it was started outside
  any repository, to the repository it edited and committed to.
- Commits come from the transcripts and from `git log` of that day, each assigned to one session.
- `actions` are writes to other tools (Jira, Slack, Bitbucket, GitHub…), `documents` the files
  Claude pointed the user to, `skills` the skills and slash commands used. They help you
  understand a session; the page does not list them.
- Sessions started in `/tmp`, skill-creator eval workspaces and scratch files are already left out.

Read the whole digest. The prompts and `last_reply` of each session say what was asked and how it
ended; `title` is Claude Code's label and may be in Portuguese or missing.

## 2. Read the user's Slack messages of the day

Slack shows work that never went through Claude: discussions, investigations, reviews requested,
decisions. Use it as content and as a map of what the sessions were for.

Search with `slack_search_public_and_private` (the tool description gives the user's id):

- `filters`: `from:<@USER_ID> on:<day>`, `natural_language_query`: `""`
- `sort`: `timestamp`, `sort_dir`: `asc`, `response_format`: `concise`, `limit`: 20
- Follow the `cursor` until there are no more pages.

Drop the messages in the user's DM with themselves ("DM with <their own name>"): those are notes
and shares to self, not conversations.

Many messages are short replies ("aprovado", "vou ver"). Read the thread (`slack_read_thread`) only
when such a message seems to carry a decision or outcome you cannot place otherwise; reading every
thread costs a lot and adds little. Keep the others as timeline ticks with a topic as plain as
"reply". Summarize only what the user said or did; never quote other
people. If the Slack tools are unavailable, skip this step and say so in your reply.

## 3. Write the notes

Write `~/Documents/diario/<day>.notes.json`. Its schema is in the docstring of
`scripts/render_recap.py`; the renderer rejects notes that leave a visible session ungrouped,
group it twice, or use an unknown activity or status.

**Leave out personal, non-development work**: personal documents, finances, studies, household
matters (for example, humanizing a personal PDF). Mark those sessions `hide: true`. Tools the
user builds for themselves are not personal; they go under "Own projects".

Also hide noise: probe or test prompts ("Use the AskUserQuestion tool to ask me…"), sessions with
nothing but a slash command that did nothing, accidental duplicates.

**Per session** (`sessions`): `activity` is required for every visible session, by what the
session was mostly about:
- `build`: writing or changing code, configuration or tooling, including debugging a fix
- `review`: reviewing code, tickets or PRs, including leaving review comments
- `plan`: design, specs, research, investigation and diagnosis without a fix
- `other`: writing documents, admin, packaging and anything else

Give `title` (2-5 words, English) and a one-line `summary`; they show in the timeline tooltips.

**Groups** (`groups`): divide the day by initiative, the goal the work served, not by folder. A
ticket and its reviews, or two repositories serving one feature, are one initiative. Aim for 3-7
groups with names a teammate would recognize ("K265 PSVI messages", "Ticket reviews"). A
session that served two goals goes in the group of its main one; its other outcome can still be
an item in the group it belongs to.
Each group has a `section`:
- `"Work"`: anything for the employer, including Claude Code skills and tooling used at work
- `"Own projects"`: tools and projects the user builds for themselves

Whenever the user sent Slack messages that day, add one Slack group in Work, `{"name": "Slack
messages", "section": "Work", "slack": true, "sessions": []}`: its timeline row shows the
messages. Its items are what the user did only in Slack (an incident looked into, a colleague
helped, a decision argued); leave `items` empty when Slack added nothing beyond the sessions.

Group by what the work was for: improving a tool used for reviews (a skill, a bot, a report)
is tooling, not a review, even when it happened while reviewing.

For each group write `items`: one entry per piece of work, as the user would say it at the
standup. Fold reruns and retries of the same task into one item. Say what was reviewed or built,
not only its ticket: "Reviewed the VTP Runner changes; 5 comments drafted", not "Reviewed
VP-649". Each item is one line on the page: at most 64 characters, counting 9 for each ticket
badge, and group names at most 24. The renderer rejects longer ones and says by how much;
shorten them rather than cutting words. Put the ticket keys in `tickets` (shown as badges) and
always a `status`:
- `merged`: merged into its target branch, even if only locally
- `approved`: the PR was approved and is not merged yet
- `in review`: a PR is open and waiting for review
- `in progress`: unfinished, or finished on a branch that is not merged or opened as a PR
- `done`: finished with nothing pending, such as a submitted review or a diagnosis
- `blocked`: cannot move on until something outside the user's control changes
- `discussed`: a conversation with no deliverable (helping a colleague debug, arguing a decision)

No links, file names or PR numbers on the page. Stick to facts from the digest and Slack; when an
outcome is unclear (the session ended mid-task), use `in progress` instead of guessing.

**`slack`**: one entry per message kept, `{"time": "HH:MM", "channel": "#name" or "DM",
"topic": "a few words"}`. They become the ticks of the Slack messages row.

## 4. Render and open

```bash
python3 <skill-dir>/scripts/render_recap.py /tmp/daily-recap/<day>.json \
  ~/Documents/diario/<day>.notes.json ~/Documents/diario
```

It writes `<day>.recap.json` and rebuilds `index.html` from every day in the folder. If it rejects
the notes, fix what it lists and run it again. When the run is not unattended, open the last day
rendered: `xdg-open "file://$HOME/Documents/diario/index.html#<day>"`.

The page lists the days on the left, newest first, with a search box over all of them, and shows
one day at a time: its figures (Claude Code sessions, first to last activity, lines, commits,
Slack messages), lines per language, a timeline with one row per group coloured by activity, and
one row per group with its numbers and its items.

## 5. Reply

Give the page's path and, in two or three lines per day, the shape of the day (the main
outcomes, nothing more). Mention anything skipped, such as a day with no activity or Slack being
unavailable.
