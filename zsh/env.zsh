export EDITOR=vim

export BUN_INSTALL="$HOME/.bun"
export NVM_DIR="$HOME/.config/nvm"
export LD_LIBRARY_PATH="$HOME/.local/lib:$LD_LIBRARY_PATH"

# Sets HOMEBREW_* and MANPATH; its PATH entries are reordered below
[ -x /home/linuxbrew/.linuxbrew/bin/brew ] && eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv zsh)"

# -U drops duplicates (first occurrence wins); (N) drops dirs that don't exist.
# Default node bin is on PATH directly so global npm CLIs work without loading nvm.
typeset -U path PATH
path=(
    $NVM_DIR/versions/node/*/bin(Nn[-1])
    $HOME/.npm-global/bin(N)
    $HOME/.local/bin
    /home/linuxbrew/.linuxbrew/{bin,sbin}(N)
    $BUN_INSTALL/bin(N)
    $HOME/workspace/scripts/.venv/bin(N)
    /usr/local/bin
    $HOME/workspace/scripts/utils(N)
    $path
)
