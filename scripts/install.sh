#!/usr/bin/env bash
# Bootstrap a fresh Ubuntu machine with these dotfiles.
# Afterwards: set terminal background to #1C1C1C and select the MesloLGS NF font.
set -euo pipefail

repo="$(cd "$(dirname "$0")/.." && pwd)"

sudo apt update
sudo apt install -y curl git tig lnav ripgrep bat vim unzip build-essential coreutils tree \
    htop tmux net-tools gnome-shell-extensions gnome-shell-extension-prefs gnome-tweaks \
    taskwarrior zsh age

sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" \
    "" --keep-zshrc --skip-chsh --unattended

ZSH_CUSTOM="$HOME/.oh-my-zsh/custom"
git clone --depth=1 https://github.com/romkatv/powerlevel10k.git \
    "$ZSH_CUSTOM/themes/powerlevel10k"
git clone https://github.com/zsh-users/zsh-autosuggestions "$ZSH_CUSTOM/plugins/zsh-autosuggestions"
git clone https://github.com/joshskidmore/zsh-fzf-history-search \
    "$ZSH_CUSTOM/plugins/zsh-fzf-history-search"
git clone https://github.com/junegunn/fzf-git.sh "$ZSH_CUSTOM/plugins/fzf-git"
git clone --depth 1 https://github.com/junegunn/fzf.git ~/.fzf
~/.fzf/install --key-bindings --completion --no-update-rc

media=https://github.com/romkatv/powerlevel10k-media/raw/master
wget -P ~/.local/share/fonts \
    "$media/MesloLGS%20NF%20Regular.ttf" \
    "$media/MesloLGS%20NF%20Bold.ttf" \
    "$media/MesloLGS%20NF%20Italic.ttf" \
    "$media/MesloLGS%20NF%20Bold%20Italic.ttf"

"$repo/scripts/link.sh"

if [ -f "$repo/secrets/key.txt" ]; then
    "$repo/scripts/history-restore.sh"
else
    echo "Skipping history: copy the age key from 1Password to $repo/secrets/key.txt," \
        "then run $repo/scripts/history-restore.sh"
fi

chsh -s "$(command -v zsh)"
