# dotfiles

Personal Linux (Ubuntu + GNOME) configuration. Each top-level directory groups one tool's files,
and the link script places them where they belong in the home directory as symlinks, so edits
in place show up in the repository right away.

## Layout

| Directory | Contents |
|---|---|
| `zsh` | `.zshrc` and its modules: environment and PATH, p10k theme, tools, functions |
| `git` | global git config and ignore list |
| `vim`, `tmux`, `ghostty` | editor and terminal configs |
| `yazi` | file manager config; plugins and flavor pinned in `package.toml` |
| `devin` | Devin IDE settings and keybindings (VS Code format) |
| `claude` | Claude Code: global instructions, settings, status line, hooks, preview server, skills, agents |
| `scripts` | install, linking, and shell history backup and restore |
| `packages` | the apt packages chosen for this machine, for reference |
| `secrets` | encrypted shell history and the age public key |
| `previous-jobs` | archived configs from past jobs (not linked) |

## Claude Code

| Part | What it does |
|---|---|
| `CLAUDE.md` | Global instructions: language, previews, subagents, code style, writing and git rules |
| `agents` | Subagents; `browser` runs multi-step Chrome tasks and reports back in writing |
| `settings.json` | Permissions, hooks and plugins; the model and effort picked in a session stay local |
| `statusline.sh` | Status line with model, effort, context use, cost, prompts, duration, lines changed and folder |
| `hooks` | Blocks commit messages that break the commit rules |
| `previews` | Local server for HTML previews, started with each session; a written preview opens a window on the secondary monitor, and confirming a choice closes it |

### Skills

| # | Skill | What it does |
|---|---|---|
| 1 | [`daily-recap`](https://github.com/emanuel36/dotfiles/tree/master/claude/skills/daily-recap) | Daily work summary for the standup, kept in a local work diary |
| 2 | [`fold-branch`](https://github.com/emanuel36/dotfiles/tree/master/claude/skills/fold-branch) | Folds a branch's fixes into clean commits |
| 3 | [`jira-comment`](https://github.com/emanuel36/dotfiles/tree/master/claude/skills/jira-comment) | Drafts a Jira comment in three formats to edit and approve before posting |
| 4 | [`trending-repos`](https://github.com/emanuel36/dotfiles/tree/master/claude/skills/trending-repos) | Writes a page summarizing the GitHub repositories trending today that were not seen yet |

## New machine

1. Clone the repository into `~/.dotfiles`.
2. Optional, to restore shell history: copy the age key from 1Password into `secrets/key.txt`.
3. Run `scripts/install.sh`. It installs the base apt packages, oh-my-zsh and its plugins, fzf
   and fonts, links the files, restores the history when the key is present, and sets zsh as
   the login shell.
4. Set the terminal background to `#1C1C1C` and the font to MesloLGS NF.
5. yazi is not installed by the script: install it with Homebrew, then fetch its plugins and
   flavor with `ya pkg install`.

`packages/apt.txt` lists extra apt packages to install by hand when needed.

## Day to day

- **New config file:** move it into its directory, add a line to the map in `scripts/link.sh`,
  then run the script.
- **New Claude Code skill:** move its directory into `claude/skills/`, then run
  `scripts/link.sh`; no map line is needed.
- **Shell history backup:** run `scripts/history-backup.sh`, then commit
  `secrets/zsh_history.age`.

## Not versioned

| Item | Where it lives |
|---|---|
| Work aliases, VPN, proxy CA bundle, cloud project | `~/.zshrc.local`, sourced if present |
| Git identity | `~/.gitconfig.local` |
| Claude Code model, effort and thinking choice | Removed from `settings.json` on commit by a git filter that `scripts/link.sh` sets up |
| Work diary written by `daily-recap` | `diary/`, gitignored |
| Claude Code skills synced from claude.ai | `synced/` |

## Shell history

The shell history is encrypted with [age](https://age-encryption.org) into
`secrets/zsh_history.age`. Backing up needs only the public key in `secrets/recipient.txt`.
Restoring with `scripts/history-restore.sh` needs the private key at `secrets/key.txt`, which is
gitignored and kept in 1Password.

## Previous jobs

`previous-jobs/` archives configs from past jobs (Motorola, Samsung); nothing there is linked.
Each `zsh_history.age` there uses the same key as above and can be decrypted with age. Motorola's
