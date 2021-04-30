export ZSH="/home/eangelim/.oh-my-zsh"

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

source $ZSH/oh-my-zsh.sh

[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh

[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh

setopt rm_star_silent

alias motorola-vpn='f() { echo $1 | sudo openconnect --protocol=nc --no-dtls https://partnervpn.motorola.com/7119-otp --user eangelim --passwd-on-stdin };f'

mkcd(){
	dir="$*";
	mkdir -p "$dir" && cd "$dir";
}

mservman03(){
	ssh -t eangelim@100.66.32.53 "cd /localrepo/eangelim; bash --login"
}

battery-historian(){
        echo "Historian available at http://localhost:3636"
        sudo docker -- run -p 3636:9999 gcr.io/android-battery-historian/stable:3.0 --port 9999
}

gpload(){
        FILE="$1"
        rclone copy --progress $FILE drive:Shared\ files
}

aplogd(){
	adb root
	adb pull /data/vendor/aplogd /home/eangelim/Downloads/
}

bug2go(){
	adb root
	adb pull /data/vendor/bug2go /home/eangelim/Downloads/
}

export PATH="$PATH:/opt/getlogs"
export PATH="$PATH:/opt/platform-tools"
export PATH="$PATH:/home/eangelim/Android/flutter/bin"

