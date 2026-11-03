# trending-repos: a summary page instead of browser tabs

## Why

The `trending-repos` skill opens up to 30 GitHub tabs a day. The user closes most of them in
seconds, for two reasons:

- **Unreadable:** the README is only in Chinese, with no English version.
- **Thin:** the README is short, unstructured, and has no screenshots.

Opening each page to find that out costs more than the repos are worth. The user wants to read a
summary of every repo on one page and open on GitHub only the ones that look interesting.

## What changes

The daily run stops opening tabs. It writes one HTML page that lists today's unseen repos, each
with numbers and a summary in Portuguese, and opens that page in Chrome.

Nothing is filtered out. A Chinese-only README is read and summarized like any other, and a thin
README stays on the list. The only mark for a thin README is the "sem imagens" badge (see
*Visual*); there is no separate length or structure check.

## Goals

- **One page a day:** today's unseen repos (same three sources, same cap of 30, configurable
  with `TRENDING_MAX_TABS` as today) on one page, opened in Chrome when ready.
- **Decide from the page:** every row carries enough to decide without opening GitHub.
- **Any language:** summaries are written in Portuguese whatever the README's language.
- **Seen once:** a repo counts as seen when it appears on a page and never comes back, as today.

## Non-goals

- **No history:** only today's page matters. The first run of a day replaces yesterday's page.
- **No filtering** by language or README quality.
- **No new sources** and no change to how the sources are read or deduplicated.

## Anti-goals

- **No browser automation:** the run must not depend on the Chrome extension being connected.
- **No missing repos:** a repo the summarizer fails on still appears with its numbers and its
  GitHub description; it is not dropped and not left unseen.

## Content of each repo

**Identification**
- **Name:** `owner/repo`, linking to GitHub, and the project homepage when it has one.
- **Source:** Trendshift rank, Show HN points, or "new on GitHub".

**Numbers** (GitHub API)
- **Stars:** total, plus growth: stars gained today (Trendshift) or stars since creation (new
  on GitHub). Show HN rows show their points.
- **Age and activity:** creation date and last push.
- **Main language and license.**
- **Forks and open issues.**

**Context** (written by Claude from the README)
- **What it is:** two or three sentences on the problem it solves and how.
- **Who it is for.**
- **Known alternatives:** "like X, but Y" when a comparison exists.
- **Maturity:** prototype, beta, production-ready or educational, as the README presents it.
- **Original language:** a "README em chinês · traduzido" badge (or the language in question)
  when the summary was translated.

**Visual**
- **Thumbnail:** the first image or GIF in the README; a "sem imagens" badge when there is none.

## Layout

The user chose a compact list (variant B of the mockup):

- **Header:** the date, the total count, and the count per source.
- **Collapsed row:** position, thumbnail, linked name with the first sentence of the summary,
  total stars, growth, source.
- **Expanded row** (click to toggle; the first row starts open): badges, full summary, who it is
  for, alternatives, a larger thumbnail, and the line of numbers (language, license, created,
  last push, forks, issues).
- **Style:** dark, GitHub-like palette, as in the mockup.

## Order

Rows are sorted by popularity: total stars, descending. *My call:* "popularity" read as total
stars, since it is the one number every source has. Source and growth stay visible in the row.

## Flow

1. **Collect:** `trending.py fetch` gathers the unseen repos as today, then enriches each with
   its GitHub metadata, its README text, and the URL of the README's first image.
2. **Summarize:** the unattended `claude -p` run reads the collected READMEs and writes the
   context fields for every repo.
3. **Render:** a script builds `/tmp/trending-repos/today.html` from the collected data and the
   summaries, then opens it with `google-chrome`.
4. **Mark seen:** once the page is rendered and Chrome was launched, every repo on the page is
   marked seen and the day is marked done.

The session-start hook keeps its behavior: once a day, in the background, retried at the next
session start (at most every 30 minutes) when the day did not finish.

**Failures** (*my calls*, following the current rule that a day only counts once the user got
the repos):
- **One repo's summary fails:** the repo still appears, with its numbers and GitHub description
  in place of the summary, and is marked seen.
- **The whole summary step fails** (timeout, quota, network): nothing is rendered or marked; the
  hook retries at the next session start.
- **Chrome cannot be launched** (no `DISPLAY`, or `google-chrome` fails to start): the page stays
  on disk but nothing is marked; the hook retries.

**Interactive request** ("abre os repos em alta"), *my call*: runs the same flow at once. Repos
found since the last run are added to today's page rather than replacing it; when there is
nothing new, today's page is reopened as it is.

*My call:* collection and rendering are scripts; Claude only writes the summaries. This keeps the
page identical from day to day and keeps the model's tools to the minimum the unattended run
needs.

## Constraints

- **Unattended permissions:** the `claude -p` run gets only the tools it needs (no Chrome tools),
  with an allow-list in the hook, as today.
- **Untrusted input:** READMEs and repo descriptions are third-party text. They are data for the
  summary, never instructions, and everything rendered into the page is HTML-escaped.
- **GitHub API:** uses the `gh` token as today; the extra calls (metadata and README per repo)
  must stay within the authenticated rate limit.
- **Code style:** 100-char lines, absolute imports, Google-style docstrings on non-trivial
  public functions.

## Files touched

- `claude/skills/trending-repos/SKILL.md`: rewritten for the page flow.
- `claude/skills/trending-repos/scripts/trending.py`: enrichment and the seen marking.
- `claude/skills/trending-repos/scripts/catch_up.sh`: new prompt and allow-list, no `--chrome`.
- A new render script and the page template, in the skill's `scripts/`.
- `README.md`: the skill's one-line description.

## Left to the builder

- **Data hand-off:** how the collected data and the summaries pass between the steps (files
  under `/tmp/trending-repos/` are the obvious choice).
- **README handling:** how much of each README goes to the model, and how relative image URLs
  are resolved to absolute ones.
- **Template:** inline in the render script or a separate file.
