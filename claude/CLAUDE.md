# Global Development Standards

## Principles
- **Ask, don't assume:** when facing ambiguity or multiple valid options, ask instead of
  speculating or making risky choices.
- **Show options:** for design, layout, or format decisions, present several variants (e.g. 3)
  side by side — for UI, one HTML file with a switcher — and let me choose before refining.
- **No artifacts unless asked:** never publish an Artifact (Artifact tool) on your own
  initiative; for HTML/markdown deliverables, save a local file and tell me the path.
- **Open HTML automatically:** after saving an HTML file (mockups, variants, reports), open it
  in the default browser right away with `xdg-open`, without asking.
- **Disposable files:** write throwaway files I only look at — mockups, design variants,
  previews, example pages, one-off scripts — under `/tmp`, never in the working directory.
  Delete them yourself once I have chosen or dropped them.
- **Location:** save files I will edit, copy from, run or keep — reports, markdown, HTML,
  scripts, command lists, drafts — in the current working directory unless I name another place.

## Code
- 100-char line length
- Absolute imports only — no relative (`..`) paths
- Google-style docstrings on non-trivial public APIs
- Use `rg` instead of grep and `fd` instead of find

## Writing
**External** (Jira, Confluence, Slack, PR descriptions/comments, emails, technical reports):
- **Language:** technical, objective English — even when I write to you in Portuguese.
- **Content:** state facts and evidence only; no speculation, and no recommendations unless asked.
  Prefer tables for evidence; reference Jira tickets rather than commit hashes or code detail.
- **Audience:** write for what the reader knows — drop internal app names, acronyms and detail
  that an external team or non-developer would not recognize.
- **Draft first:** never create a markdown draft file unless the rule below calls for one.
  - **Jira ticket comments:** use the `jira-comment` skill; post only after I approve it.
  - **Slack:** show the message in the chat; after I approve it, save it as a Slack draft
    (`slack_send_message_draft`) — never send directly.
  - **Everything else** (Confluence, PR descriptions/comments, emails, reports): show the text in
    the chat; post only after I approve it.

**Project docs:**
- **README:** written for users, not developers.
  - Cover what it is, how it's organized, and how to use it.
  - Pick the format that fits: tree, table, or list.
  - No code or implementation detail; link to deeper docs.
  - Link to remote repos (GitHub, Bitbucket), never local paths.
- **Tone:** plain declarative sentences; a bold lead-in on bullets that carry a claim.

## Git
**Before committing:**
- Fold fixes and adjustments to unpushed work on the same branch into the commit they belong to
- Re-read your changes for unnecessary complexity, redundant code, and unclear naming
- Run relevant tests — not the full suite
- Run linters and type checker — fix everything before committing

**Commits:**
- Conventional Commits (`<type>[(<scope>)]: <description>`), imperative mood
- Subject ≤50 characters; body lines ≤72 characters
- Body as one line bullet points: an objective overview of what changed and why, no implementation detail
- A repository's own convention (README, AGENTS.md, CLAUDE.md) takes precedence where it differs
- Never commit secrets, API keys, or credentials — use gitignored `.env` files and env vars

**Before opening a pull request:**
- Run `/code-review` on the pull request's own commits, on its branch
- Fix the findings that hold; report the rejected ones to me with the reason
- Run it again before pushing substantial changes to an open pull request

**Branches & remotes:**
- Never merge or close/delete a branch unless I ask
- Always merge with `--no-ff` — never fast-forward
- Never push to remote
- Never amend/rebase commits already pushed to shared branches
- Repos under `github.com/emanuel36` are personal: use the `~/.ssh/id_emanuel36` key
