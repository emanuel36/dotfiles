---
name: jira-comment
description: >-
  Use when the user wants to write, draft, post or update a comment on a Jira ticket: a progress
  update, test results, the tests that approve a pull request, a question or blocker for another
  team, or a closing summary ("vamos fazer um comentário na task", "comenta no ticket",
  "atualiza o ticket com o progresso", "registra no Jira os testes que fiz", a
  pltsci.atlassian.net/browse link with a request to report on it). Not for creating or editing
  tickets, transitioning status, or reviewing a ticket's pull requests.
---

# Jira comment

The shape of a comment depends on the ticket and on what the comment is for, so the user picks
it: three variants open side by side in an editor page, the user edits and saves one, and only
that saved text is posted.

## 1. Gather

- **Ticket:** fetch it with `getJiraIssue` (cloudId `8b1d485a-fc8f-45c4-a6e3-7e16f7731943` for
  pltsci; otherwise `getAccessibleAtlassianResources`): type, status, description, acceptance
  criteria or test cases, and the existing comments, so the new one continues them instead of
  repeating them.
- **Material:** what the user gave in the conversation (test results, a Slack or Teams thread,
  logs), and the work on the current branch when it is a code ticket.
- **Purpose:** progress update, test results, approval of a pull request, question or blocker,
  closing summary. Ask when the material does not make it clear.

## 2. Write three variants

Each variant changes **both the structure and the level of detail**, so the three read
differently, for example:

| Variant | Structure | Detail |
|---|---|---|
| A | Outcome sentence and a results table | Short: what a reader scanning the ticket needs |
| B | One bold-titled block per item (test case, finding, task) with bullets | Medium |
| C | Outcome, then context, evidence table and open items | Full: everything with its evidence |

Pick the three that fit this ticket and purpose; the table is a starting point, not a fixed set.
Every variant follows the external writing rules in the user's CLAUDE.md, plus:

- The first sentence states the outcome.
- When an earlier comment left items open, say which ones this comment resolves.
- Name exact versions, builds, firmware and dates, as they appear in the material.
- Status tables close with a legend line, e.g. `**Legend:** ✅ Completed · ⏳ Pending · 🚫 N/A`.
- Markdown only: headings, bold, lists, tables, code blocks, links. No HTML.

## 3. Open the editor

Write the variants as JSON to `/tmp/jira-comment-<KEY>.json`:

```json
{
  "key": "VP-431",
  "title": "Ticket summary",
  "url": "https://pltsci.atlassian.net/browse/VP-431",
  "purpose": "Test results from the truck session",
  "variants": [
    {"name": "Results table", "detail": "Short", "why": "Readers only need the status",
     "markdown": "..."}
  ]
}
```

```bash
python3 <skill-dir>/scripts/render_editor.py /tmp/jira-comment-<KEY>.json /tmp/jira-comment-<KEY>.html
xdg-open /tmp/jira-comment-<KEY>.html
```

Tell the user the page is open: it shows each variant as Jira will render it, they switch
variants, edit the text in place, and press **Save** to download `<KEY>-comment.md` to
`~/Downloads`. Ask them to say when it is
saved, or to request changes, and regenerate the page when they ask for new variants.

## 4. Post

1. Read the newest `~/Downloads/<KEY>-comment*.md` (the browser appends ` (1)` when the name is
   taken). Ignore files older than the page.
2. Show the text in the chat and ask for approval. Post nothing without an explicit yes.
3. Post exactly that text with `addOrEditJiraIssueComment` (`contentFormat: markdown`); to update
   a comment, pass its `commentId`.
4. Give the user the ticket link, then delete the `/tmp/jira-comment-<KEY>.*` files and the
   posted draft in `~/Downloads`.

## Common mistakes

- **Posting a variant instead of the saved file.** The user's edits live only in the download.
- **Three variants that differ only in wording.** Vary the structure and the depth.
- **Repeating the ticket description or earlier comments.** Add only what is new.
