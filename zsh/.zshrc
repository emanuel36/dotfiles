# Load order matters: env/PATH -> theme -> tools (fzf before omz keeps ^R from
# zsh-fzf-history-search) -> oh-my-zsh -> functions -> machine-local overrides.
# First-time setup on a new machine: ~/.dotfiles/scripts/install.sh

source ~/.zsh/env.zsh
source ~/.zsh/theme.zsh
source ~/.zsh/tools.zsh

export ZSH="$HOME/.oh-my-zsh"
zstyle ':omz:update' mode auto
plugins=(
    git
    extract
    zsh-autosuggestions
    zsh-interactive-cd
    dirhistory
    command-not-found
    zsh-fzf-history-search
)
source $ZSH/oh-my-zsh.sh

source ~/.zsh/functions.zsh

# Work and machine-specific config (not versioned)
[ -f ~/.zshrc.local ] && source ~/.zshrc.local
