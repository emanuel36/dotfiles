# Global Development Standards

## Philosophy
**Use skills proactively:** When skills match the task, suggest relevant ones — don't block on them.  
**No code in plan mode:** When planning, describe steps in plain language — no code blocks until implementation begins.  
**Ask, don't assume:** When facing ambiguity or multiple valid options, ask for clarification instead of speculating or making risky choices.  
**No speculative features:** Don't add features, flags, or configuration options unless users actively need them right now.  
**Replace, don't deprecate:** When a new implementation replaces an old one, delete the old code entirely — no parallel paths.  
**No artifacts unless asked:** Never publish an Artifact (Artifact tool) on my own initiative. Publish only when I explicitly ask. For HTML/markdown deliverables, save a local file and tell me the path.  
**Finish the job:** Handle visible edge cases. If you find broken adjacent code while working, flag it or fix it — don't leave landmines.  

## Code Quality
### Hard limits
1. 100-char line length
2. Absolute imports only — no relative (`..`) paths
3. Google-style docstrings on non-trivial public APIs

## CLI tools
| tool | replaces | usage |
|------|----------|-------|
| `rg` (ripgrep) | grep | `rg "pattern"` - 10x faster regex search |
| `fd` | find | `fd "*.py"` - fast file finder |

## Workflow
**Before committing:**
1. Re-read your changes for unnecessary complexity, redundant code, and unclear naming
2. Run relevant tests — not the full suite
3. Run linters and type checker — fix everything before committing

**Commits:**
- Conventional Commits (`<type>[(<scope>)]: <description>`), imperative mood
- Subject ≤50 characters; body lines ≤72 characters
- Body as bullet points: an objective overview of what changed and why, no implementation detail
- Fold fixes and adjustments to unpushed work on the same branch into the commit they belong to
  (`git commit --fixup` + `git rebase --autosquash`); keep only the commits the branch needs,
  organized (e.g. one pin commit, not one per follow-up)
- A repository's own convention (README, AGENTS.md, CLAUDE.md) takes precedence where it differs
- Never amend/rebase commits already pushed to shared branches
- Never push the commit to remote
- Never commit secrets, API keys, or credentials — use `.env` files (gitignored) and environment variables
