# Global Development Standards

## Principles
- **Ask, don't assume:** when facing ambiguity or multiple valid options, ask instead of
  speculating or making risky choices.
- **Show options:** for design, layout, or format decisions, present several variants (e.g. 3)
  side by side — for UI, one HTML file with a switcher — and let me choose before refining.
- **No artifacts unless asked:** never publish an Artifact (Artifact tool) on your own
  initiative; for HTML/markdown deliverables, save a local file and tell me the path.
- **Location:** save generated files (reports, markdown, HTML, scripts) in the current working
  directory unless I name another place.

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
- **Draft first:** write a markdown draft in the current directory for my review; post to the
  external service only after I approve it. For Slack, create a draft — never send directly.

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

**Branches & remotes:**
- Never merge or close/delete a branch unless I ask
- Always merge with `--no-ff` — never fast-forward
- Never push to remote
- Never amend/rebase commits already pushed to shared branches
- Repos under `github.com/emanuel36` are personal: use the `~/.ssh/id_emanuel36` key
