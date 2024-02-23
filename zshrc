# Manual setup
# 1- Install and run zsh
# 2- Change terminal background to #1C1C1C
# 3- Install yazi (https://github.com/sxyazi/yazi)

# First launch setup
if [ ! -d "$HOME/.oh-my-zsh" ];
then
        # Install my packages
        sudo apt update
        sudo apt install -y curl \
                            git \
                            tig \
                            lnav \
                            ripgrep \
                            vim \
                            unzip \
                            build-essential \
                            coreutils \
                            tree \
                            htop \
                            tmux \
                            net-tools \
                            gnome-shell-extensions \
                            gnome-shell-extension-prefs \
                            gnome-tweaks \
                            taskwarrior

        # Setup zsh terminal
        sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh) --keep-zshrc --skip-chsh --unattended"
        git clone --depth=1 https://github.com/romkatv/powerlevel10k.git ${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/themes/powerlevel10k
        wget https://github.com/romkatv/powerlevel10k-media/raw/master/MesloLGS%20NF%20Regular.ttf \
             https://github.com/romkatv/powerlevel10k-media/raw/master/MesloLGS%20NF%20Bold.ttf \
             https://github.com/romkatv/powerlevel10k-media/raw/master/MesloLGS%20NF%20Italic.ttf \
             https://github.com/romkatv/powerlevel10k-media/raw/master/MesloLGS%20NF%20Bold%20Italic.ttf -P ~/.local/share/fonts
        git clone https://github.com/zsh-users/zsh-autosuggestions ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-autosuggestions
        git clone --depth 1 https://github.com/junegunn/fzf.git ~/.fzf && ~/.fzf/install --key-bindings --completion --update-rc
        git clone https://github.com/joshskidmore/zsh-fzf-history-search ${ZSH_CUSTOM:=~/.oh-my-zsh/custom}/plugins/zsh-fzf-history-search
        git clone https://github.com/junegunn/fzf-git.sh ${ZSH_CUSTOM:=~/.oh-my-zsh/custom}/plugins/fzf-git
        chsh -s $(which zsh)

        # End
        clear
fi

export EDITOR=vim
export GIT_EDITOR=vim

zstyle ':omz:update' mode auto
export ZSH="${HOME}/.oh-my-zsh"

ZSH_THEME="powerlevel10k/powerlevel10k"

POWERLEVEL9K_MODE='nerdfont-complete'

POWERLEVEL9K_ICON_PADDING=none
POWERLEVEL9K_ICON_BEFORE_CONTENT=true
POWERLEVEL9K_TRANSIENT_PROMPT=false

POWERLEVEL9K_LEFT_PROMPT_ELEMENTS=(
        #os_icon
        host
        dir
        vcs
)

POWERLEVEL9K_RIGHT_PROMPT_ELEMENTS=(
        status
        #ram
        command_execution_time
        taskwarrior
        time
)

COLOR1='black'
COLOR2='#BBBBBB'
VERDE='#24AF89'
AZUL='#559EF9'

POWERLEVEL9K_FOREGROUND=$COLOR1
POWERLEVEL9K_BACKGROUND=$COLOR2

POWERLEVEL9K_LEFT_PROMPT_FIRST_SEGMENT_START_SYMBOL='▒▓'
POWERLEVEL9K_LEFT_SEGMENT_SEPARATOR='\uE0BC'
POWERLEVEL9K_LEFT_PROMPT_LAST_SEGMENT_END_SYMBOL='\uE0B0'

POWERLEVEL9K_RIGHT_PROMPT_FIRST_SEGMENT_START_SYMBOL='\uE0B6'
POWERLEVEL9K_RIGHT_SEGMENT_SEPARATOR='\uE0BA'
POWERLEVEL9K_RIGHT_SUBSEGMENT_SEPARATOR='\uE0BD'
POWERLEVEL9K_RIGHT_PROMPT_LAST_SEGMENT_END_SYMBOL='\uE0B4'

POWERLEVEL9K_HOST_TEMPLATE="󱐋 emanuel"

POWERLEVEL9K_FOLDER_ICON=''
POWERLEVEL9K_HOME_SUB_ICON=''
POWERLEVEL9K_DIR_HOME_SUBFOLDER_ICON=''
POWERLEVEL9K_DIR_ETC_ICON=''
POWERLEVEL9K_DIR_HOME_ICON=''
POWERLEVEL9K_DIR_FOREGROUND=$COLOR2
POWERLEVEL9K_DIR_BACKGROUND=$COLOR1
POWERLEVEL9K_SHORTEN_STRATEGY='truncate_to_beggining'
POWERLEVEL9K_SHORTEN_DIR_LENGTH=2

POWERLEVEL9K_VCS_GIT_ICON=''
POWERLEVEL9K_VCS_GITHUB_ICON=''
POWERLEVEL9K_VCS_CLEAN_BACKGROUND=$VERDE
POWERLEVEL9K_VCS_UNTRACKED_BACKGROUND=$AZUL
POWERLEVEL9K_VCS_MODIFIED_BACKGROUND=$AZUL

POWERLEVEL9K_STATUS_OK=false
POWERLEVEL9K_STATUS_ERROR=true
POWERLEVEL9K_STATUS_ERROR_BACKGROUND='red3'
POWERLEVEL9K_STATUS_ERROR_FOREGROUND='yellow'
POWERLEVEL9K_STATUS_ERROR_VISUAL_IDENTIFIER_EXPANSION=''

POWERLEVEL9K_COMMAND_EXECUTION_TIME_THRESHOLD=0.5
POWERLEVEL9K_COMMAND_EXECUTION_TIME_PRECISION=1
POWERLEVEL9K_COMMAND_EXECUTION_TIME_FOREGROUND=$COLOR2
POWERLEVEL9K_COMMAND_EXECUTION_TIME_BACKGROUND=$COLOR1

POWERLEVEL9K_TIME_FORMAT='%D{%H:%M}'

[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh

plugins=(
	git
	zsh-autosuggestions
	zsh-interactive-cd
	dirhistory
	command-not-found
    zsh-fzf-history-search
)

source $ZSH/oh-my-zsh.sh

[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh

setopt rm_star_silent

mkcd(){
	DIR="$*";
	mkdir -p "$DIR" && cd "$DIR";
}

rgfzf(){
        RG_PREFIX="rg --column --line-number --no-heading --color=always --smart-case "
        INITIAL_QUERY="${*:-}"
        : | fzf --ansi --disabled --query "$INITIAL_QUERY" \
            --bind "start:reload:$RG_PREFIX {q}" \
            --bind "change:reload:sleep 0.1; $RG_PREFIX {q} || true" \
            --delimiter : \
            --preview 'bat --color=always {1} --highlight-line {2}' \
            --preview-window 'up,60%,border-bottom,+{2}+3/3,~3' \
            --bind 'enter:become(vim {1} +{2})'
}

zle -N rgfzf
bindkey '^f' rgfzf

extract(){
    if [ -f $1 ]; then
        case $1 in
            *.tar.bz2)    tar xjf $1   ;;
            *.tar.gz)     tar xzf $1   ;;
            *.bz2)        bunzip2 $1   ;;
            *.rar)        unrar x $1   ;;
            *.gz)         gunzip $1    ;;
            *.tar)        tar xf $1    ;;
            *.tbz2)       tar xjf $1   ;;
            *.tgz)        tar xzf $1   ;;
            *.zip)        unzip $1     ;;
            *.Z)          uncompress $1;;
            *.7z)         7z x $1      ;;
            *.tar.gz)     tar J $1     ;;
            *.xz)         tar xvf $1   ;;
            *)            echo "'$1' cannot be extracted via ex()" ;;
        esac
    else
        echo "'$1' is not a valid file"
    fi
}

source ${ZSH_CUSTOM}/plugins/fzf-git/fzf-git.sh
export PATH="/usr/local/bin:$PATH"
