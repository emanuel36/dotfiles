# dotfiles

Personal Linux (Ubuntu + GNOME) configuration. Each top-level directory groups one tool's files;
`scripts/link.sh` symlinks them to where they belong under `$HOME`.

| Directory | Contents |
|---|---|
| `zsh` | `.zshrc` + modules linked into `~/.zsh/` (env/PATH, p10k theme, tools, functions) |
| `git` | `.gitconfig`, global ignore |
| `vim`, `tmux`, `ghostty` | editor and terminal configs |
| `yazi` | file manager config; plugins and flavor pinned in `package.toml` |
| `devin` | Devin IDE settings and keybindings (VS Code format) |
| `claude` | Claude Code: `CLAUDE.md`, settings, status line, user-level skills in `skills/` |
| `scripts` | install, linking, and shell history backup/restore |
| `secrets` | encrypted shell history and the age public key |
| `previous-jobs` | archived configs from past jobs (not linked) |

## New machine

```sh
git clone git@github.com:emanuel36/dotfiles.git ~/.dotfiles
# Optional, to restore shell history: copy the age key from 1Password to
# ~/.dotfiles/secrets/key.txt
~/.dotfiles/scripts/install.sh
```

`scripts/install.sh` installs the base apt packages, oh-my-zsh and its plugins, fzf, and fonts,
then runs `scripts/link.sh`. yazi isn't installed by it: after `brew install yazi`, run
`ya pkg install` to fetch the plugins and flavor.

`packages/apt.txt` is a snapshot of installed apt packages, for reference:

```sh
xargs sudo apt install -y < packages/apt.txt
```

## Day to day

Files in `$HOME` are symlinks into this repo, so edits show up in `git status` directly.

- New config file: move it into its directory, add a line to the map in `scripts/link.sh`,
  then run `scripts/link.sh`
- New Claude Code skill: move its directory into `claude/skills/`, then run `scripts/link.sh`
  (no map line needed)
- Back up shell history: `scripts/history-backup.sh`, then commit `secrets/zsh_history.age`

## Not versioned

Machine- and work-specific config lives outside the repo and is sourced if present:

- `~/.zshrc.local`: work aliases, VPN, proxy CA bundle, cloud project
- `~/.gitconfig.local`: `[user]` identity
- Claude Code skills installed by other tools (`graphify`) or synced from claude.ai (`synced/`)

## Shell history

`~/.zsh_history` is encrypted with [age](https://age-encryption.org) into
`secrets/zsh_history.age`. Backing up only needs the public key in `secrets/recipient.txt`.
Restoring (`scripts/history-restore.sh`) needs the private key at `secrets/key.txt`,
which is gitignored and kept in 1Password.

## Previous jobs

`previous-jobs/` archives configs from past jobs (Motorola, Samsung). Nothing there is linked
into `$HOME`. Each `zsh_history.age` uses the same key as above:

```sh
age -d -i secrets/key.txt previous-jobs/samsung/zsh_history.age | less
```

Motorola's scripts are archived in `previous-jobs/motorola/scripts.tar.gz`.
