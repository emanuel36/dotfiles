#!/usr/bin/env bash
# Symlink repo files into $HOME, replacing whatever is there. Safe to re-run.
set -euo pipefail

repo="$(cd "$(dirname "$0")/.." && pwd)"

while read -r src dest; do
    mkdir -p "$(dirname "$HOME/$dest")"
    ln -sfn "$repo/$src" "$HOME/$dest"
done <<'EOF'
claude/CLAUDE.md                .claude/CLAUDE.md
claude/settings.json            .claude/settings.json
claude/statusline.sh            .claude/statusline.sh
devin/keybindings.json          .config/Devin/User/keybindings.json
devin/settings.json             .config/Devin/User/settings.json
ghostty/config                  .config/ghostty/config
ghostty/github-dark             .config/ghostty/themes/github-dark
git/.gitconfig                  .gitconfig
git/ignore                      .config/git/ignore
tmux/.tmux.conf                 .tmux.conf
vim/.vimrc                      .vimrc
yazi/init.lua                   .config/yazi/init.lua
yazi/keymap.toml                .config/yazi/keymap.toml
yazi/package.toml               .config/yazi/package.toml
yazi/theme.toml                 .config/yazi/theme.toml
yazi/yazi.toml                  .config/yazi/yazi.toml
zsh/.zshrc                      .zshrc
zsh/env.zsh                     .zsh/env.zsh
zsh/functions.zsh               .zsh/functions.zsh
zsh/theme.zsh                   .zsh/theme.zsh
zsh/tools.zsh                   .zsh/tools.zsh
EOF
