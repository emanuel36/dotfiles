# Global Instructions

## Interaction
- **Chat language:** reply in Portuguese, objective and concise.
- **Ask, don't assume:** when there are multiple valid options, ask.
- **Show options:** for design, layout, or format decisions, present three variants in one
  HTML file with a switcher and let me choose before refining.
- **No artifacts unless asked:** never publish an Artifact unless I ask.

## Files
- **Preview before applying:** anything you show me before it takes effect — drafts, plans,
  file or config changes, layouts, diagrams — goes in an HTML preview under `/tmp`, opened
  with `xdg-open` without asking. Skip it for small edits I spelled out myself.
- **Disposable:** previews, mockups, variants and one-off scripts go under `/tmp`, never in the
  working directory; delete them once I approve, reject or drop them.
- **Kept files:** files I will reuse — reports, docs, scripts — go in the current working
  directory unless I name another place.

## Code
- 100-char line length
- Absolute imports only — no relative (`..`) paths
- Google-style docstrings on non-trivial public APIs
- Use `rg` instead of grep and `fd` instead of find
- Run `/code-review` after a non-trivial implementation and before pushing a fix to a PR;
  fix the findings that hold and report the rejected ones with the reason

## Writing
- **Tone:** plain declarative sentences; a bold lead-in on bullets that carry a claim.

**External** (Jira, Confluence, Slack, PR descriptions/comments, emails, technical reports):
- **Language:** technical, objective English.
- **Content:** facts and evidence only; no speculation, no recommendations unless asked
  (questions and blockers are fine). Prefer tables for evidence; reference Jira tickets
  rather than commit hashes or code detail.
- **Audience:** drop internal app names, acronyms and detail the reader would not recognize.
- **Draft first:** the preview mimics the target platform's look (Jira, Slack, Confluence,
  GitHub, email) and is editable in place; post only after I approve it.
  - **Jira:** use the `jira-comment` skill.
  - **Slack:** save as a draft with `slack_send_message_draft` — never send.

**README:** for users, not developers — what it is, how it's organized, how to use it; tree,
table or list; no code; link to remote repos, never local paths.

## Git
**Before committing:**
- Fold fixes to unpushed work into the commit they belong to (`fold-branch` for larger rewrites)
- Re-read your changes for unnecessary complexity, redundant code, and unclear naming
- Run the tests that cover the changed code, linters and type checker — fix everything

**Commits:**
- Conventional Commits (`<type>[(<scope>)]: <description>`), imperative mood
- Subject ≤50 characters; body lines ≤72 characters
- Body: one-line bullets — what changed and why, no implementation detail
- A repository's own convention (README, AGENTS.md, CLAUDE.md) takes precedence
- Never commit `secrets/` content or credentials — use gitignored `.env` files and env vars

**Branches & remotes:**
- Never merge or close/delete a branch unless I ask; always merge with `--no-ff`
- Never push to remote
- Repos under `github.com/emanuel36` are personal: use the `~/.ssh/id_emanuel36` key
