[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh

# nvm.sh costs ~1s, so load it on first `nvm` call (node itself is already on PATH)
nvm() {
    unfunction nvm
    source "$NVM_DIR/nvm.sh"
    [ -s "$NVM_DIR/bash_completion" ] && source "$NVM_DIR/bash_completion"
    nvm "$@"
}

[ -s "$BUN_INSTALL/_bun" ] && source "$BUN_INSTALL/_bun"
