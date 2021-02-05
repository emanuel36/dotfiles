export ZSH="/home/epereira/.oh-my-zsh"

ZSH_THEME="powerlevel10k/powerlevel10k"

POWERLEVEL9K_MODE='nerdfont-complete'

#LEFT PROMPT
POWERLEVEL9K_LEFT_PROMPT_ELEMENTS=(os_icon host dir vcs)
POWERLEVEL9K_OS_ICON_BACKGROUND=233
POWERLEVEL9K_OS_ICON_FOREGROUND=220
POWERLEVEL9K_HOST_TEMPLATE="eangelim@eldorado"
POWERLEVEL9K_HOST_BACKGROUND=233
POWERLEVEL9K_HOST_FOREGROUND=28
POWERLEVEL9K_DIR_FOREGROUND=16
POWERLEVEL9K_DIR_BACKGROUND=4

#RIGHT PROMPT
POWERLEVEL9K_RIGHT_PROMPT_ELEMENTS=(status command_execution_time time)
POWERLEVEL9K_STATUS_BACKGROUND=233
POWERLEVEL9K_STATUS_OK_FOREGROUND=28
POWERLEVEL9K_STATUS_ERROR_BACKGROUND=160
POWERLEVEL9K_STATUS_ERROR_FOREGROUND=11
POWERLEVEL9K_COMMAND_EXECUTION_TIME_THRESHOLD=0
POWERLEVEL9K_COMMAND_EXECUTION_TIME_FOREGROUND=28
POWERLEVEL9K_COMMAND_EXECUTION_TIME_BACKGROUND=233
POWERLEVEL9K_TIME_FOREGROUND=16
POWERLEVEL9K_TIME_BACKGROUND=28

plugins=(
	git
	zsh-autosuggestions
	zsh-interactive-cd
	dirhistory
	)

function mkcd
{
  dir="$*";
  mkdir -p "$dir" && cd "$dir";
}

source $ZSH/oh-my-zsh.sh

[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh

[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh

setopt rm_star_silent

alias motorola-vpn='f() { echo $1 | sudo openconnect --protocol=pulse --no-dtls https://br-partnervpn.motorola.com/7119-otp --user eangelim --passwd-on-stdin };f'

export PATH="$PATH:/home/epereira/Android/flutter/bin"
export PATH="$PATH:/home/epereira/Android/Sdk/platform-tools/"
export PATH="$PATH:/opt/getlogs/"
export PATH="$PATH:/home/epereira/Android/Sdk/build-tools/30.0.2/"
