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
	DIR="$*";
	mkdir -p "$DIR" && cd "$DIR";
}

mservman04(){
	ssh -t eangelim@100.66.32.54 "cd /localrepo/eangelim; bash --login"
}

gpload(){
        FILE="$1"
        rclone copy --progress $FILE gdrive:Shared\ files
}

dwbuild(){
	LINK="$1"
	$HOME/Documents/.scripts/dwbuild.sh "$LINK"
}

getlogs(){
	$HOME/Documents/.scripts/getlogs.sh
}

adbconnect(){
	adb disconnect
	adb tcpip 5555
	sleep 3
	IP=$(adb shell ip addr show wlan0  | grep 'inet ' | cut -d' ' -f6| cut -d/ -f1)
	adb connect $IP
}

flash(){
	FILE="$1"
	FOLDER=$( echo $FILE | cut --complement -f 1 -d "_" | sed -r 's/\.[[:alnum:]]+\.[[:alnum:]]+$//' )
	sudo systemctl stop ModemManager
	sudo systemctl stop fwupd.service
	adb reboot bootloader
	fastboot erase cache
	fastboot erase userdata
	tar -xf $FILE
	rm -rf $FILE
        cd $FOLDER
	if [[ $FILE == *"_12_"* ]]; then
		fastboot oem  ssm_test 3
		fastboot reboot fastboot
		fastboot flash system system.img
		fastboot flash product product.img
		if [[ $FILE != *"_sofiap_"* ]]; then
			fastboot flash system_ext system_ext.img
		fi
		fastboot reboot
	else
		./flashall.sh
	fi
	cd ..
}

export PATH="/home/eangelim/Android/flutter/bin:$PATH"
export PATH="/home/eangelim/Android/Sdk/platform-tools:$PATH"
