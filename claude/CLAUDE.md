# Global Instructions

## Interaction
- **Chat language:** reply in Portuguese, objective and concise.
- **Ask, don't assume:** when there are multiple valid options, ask.
- **Show options:** for design, layout, or format decisions, present three variants in one
  HTML preview (see My choices) and let me choose before refining.
- **No artifacts unless asked:** never publish an Artifact unless I ask.
- **Tables in chat:** at most 3 columns and cells of about 40 characters; my terminal is
  narrow and Claude Code turns a table that does not fit into a broken list. Put long text in
  bullets with a bold lead-in instead.

## Files
- **Preview before applying:** anything you show me before it takes effect — drafts, plans,
  file or config changes, layouts, diagrams — goes in one HTML preview per topic under
  `/tmp/previews`, rewritten for each round. Skip it for small edits I spelled out and for short
  plans.
- **Preview window:** a SessionStart hook runs `claude/previews/open.sh` from the dotfiles. It
  serves `/tmp/previews` at `localhost:8765`; each preview has its own window, which opens on
  the secondary monitor when the file is written and reloads when it changes. Writing the file
  is enough — never run a command to open a preview.
- **Topics:** name the file `<topic>.html` (letters, digits, `-`, `_`) and give each decision
  its own topic; never reuse the topic of another decision or session. The server keeps every
  version, so rewriting the file for a new round loses nothing.
- **My choices:** wrap each variant in an element with `data-variant="<id>"` and
  `data-title="<short name>"`; a draft or plan to approve is a single `data-variant`. The server
  adds the switcher, version list, notes field and Confirm button, and sends the variant, my
  notes and the values of named form fields. Never write your own switcher, Confirm button or
  `fetch`; for other data define `window.previewData = variant => ({...})`.
- **Receiving choices:** after showing an option preview, end the turn — never wait for the
  choice with a background command or monitor. A UserPromptSubmit hook adds the choice to my
  next message, with the version it refers to; if that is not the latest, say so before acting.
- **Designs:** design docs stay as Markdown in superpowers' default directory
  (`docs/superpowers/specs/`); no HTML preview for them.
- **Disposable:** previews, mockups, variants and one-off scripts go under `/tmp`, never in the
  working directory; delete them once I approve, reject or drop them.
- **Kept files:** files I will reuse — reports, docs, scripts — go in the current working
  directory unless I name another place.

## Agents
Token cost is not a reason to avoid subagents; delegate whenever it buys accuracy, speed or a
cleaner context.
- **Fan out broad analysis:** when a task covers several independent units — repos, apps,
  documents, tickets, screens, log files — start one subagent per unit in parallel and merge
  their findings; keep only the synthesis in the main context.
- **Side requests:** when I ask for something in parallel, or unrelated to the current task,
  run it in a background agent and keep working on the main thread.
- **Browser work:** delegate multi-step Chrome tasks (inspecting screens, navigating portals,
  collecting data, downloading files) to the `browser` agent.
- **Independent check:** before reporting a non-trivial change or analysis as done, have a fresh
  agent verify it from the code or data alone, without your conclusion; fix what holds.
- **Parallel sessions:** when I say another session is working in the same repo, work in a git
  worktree without asking.

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
  - **Slack:** before drafting, read my recent messages in that channel and write in the same
    language and tone, objectively; this overrides the Language rule above. The draft goes in the
    chat, not in an HTML preview. Once I approve it, save it
    with `slack_send_message_draft` — never send. When I ask to update a saved draft, I have
    already deleted the old one: save the new draft without asking me to delete anything.

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
