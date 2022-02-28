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

alias motorola-vpn2='f() { echo "https://partnervpn.motorola.com/7119-otp" | /opt/pulsesecure/bin/pulselauncher -u eangelim -p $1 -r motorola };f'

alias motorola-vpn='f() { echo $1 | sudo openconnect --protocol=nc --no-dtls https://partnervpn.motorola.com/7119-otp --user eangelim --passwd-on-stdin };f'

mkcd(){
	DIR="$*";
	mkdir -p "$DIR" && cd "$DIR";
}

mservman08(){
	ssh -t eangelim@100.66.32.58 "cd /localrepo/eangelim; bash --login"
}

gpload(){
        FILE="$1"
        rclone copy --progress $FILE gdrive:Shared\ files
}

adbconnect(){
	adb disconnect
	adb tcpip 5555
	sleep 3
	IP=$(adb shell ip addr show wlan0  | grep 'inet ' | cut -d' ' -f6| cut -d/ -f1)
	adb connect $IP
}

flash(){
        sudo systemctl stop ModemManager
        sudo systemctl stop fwupd.service
        if [[ "$1" == *"tar.gz" ]]; then
		FILE="$1"
                FOLDER=$(echo $FILE | cut --complement -f 1 -d "_" | sed -r 's/\.[[:alnum:]]+\.[[:alnum:]]+$//' )
		tar -xvf $FILE
                rm -rf $FILE
        else
                FOLDER="$1"
        fi
        adb reboot bootloader
        fastboot erase cache
        fastboot erase userdata
        cd $FOLDER
        if [[ -f flash-msi.sh ]]; then
		./flash-msi.sh
	else
		./flashall.sh
	fi
        cd ..
}

b2g(){
	if [ "$#" -lt 1 ]; then
		echo "Illegal number of parameters"
		return 1
	elif [ "$#" -lt 2 ]; then
		FILE="$1"
		DIR=${RANDOM:0:2}
	else
		FILE="$1"
		DIR="$2"
	fi
	unzip $FILE -d $DIR
	rm -rf $FILE
	cd $DIR
	lnav aplogcat-main.txt
}

export PATH="/home/eangelim/Android/flutter/bin:$PATH"
export PATH="/home/eangelim/Android/Sdk/platform-tools:$PATH"
export PATH="/home/eangelim/.local/bin:$PATH"
export PATH="/usr/local/bin:$PATH"
export PATH="/home/eangelim/Documents/scripts:$PATH"
