setopt rm_star_silent

source $ZSH_CUSTOM/plugins/fzf-git/fzf-git.sh

mkcd() {
    mkdir -p "$*" && cd "$*"
}

# Live ripgrep search with preview; Enter opens the match in vim
rgfzf() {
    local rg_prefix="rg --column --line-number --no-heading --color=always --smart-case "
    : | fzf --ansi --disabled --query "${*:-}" \
        --bind "start:reload:$rg_prefix {q}" \
        --bind "change:reload:sleep 0.1; $rg_prefix {q} || true" \
        --delimiter : \
        --preview 'batcat --color=always {1} --highlight-line {2}' \
        --preview-window 'up,60%,border-bottom,+{2}+3/3,~3' \
        --bind 'enter:become(vim {1} +{2})'
}

zle -N rgfzf
bindkey '^f' rgfzf
bindkey '^P' fzf-file-widget
