#!/bin/bash
COREID=eangelim
BUILD_SERVER=100.66.32.58
REMOTE=gdrive

function failed(){
        notify-send --icon="/usr/share/icons/Humanity/actions/16/package-purge.svg" "$1"
}

function sucess(){
        notify-send --icon="/usr/share/icons/Humanity/actions/16/package-reinstall.svg" "$1"
}


URL="$1"
FILE=$(echo "$URL" | cut -f 11 -d "/")

ssh $COREID@$BUILD_SERVER bash -c "'
	mkdir -p /localrepo/$(whoami)/.artifacts/

	wget --no-verbose -nc $URL -P /localrepo/$(whoami)/.artifacts/

	if test -e /localrepo/$(whoami)/.artifacts/$FILE; then
		rclone copy /localrepo/$(whoami)/.artifacts/$FILE $REMOTE:artifacts
	fi

	exit
'"

if ssh $COREID@$BUILD_SERVER "test -e /localrepo/$(whoami)/.artifacts/$FILE"; then
	if [ "$(rclone lsf $REMOTE:artifacts/$FILE)" == "$FILE" ]; then
		rclone copy $REMOTE:artifacts/$FILE $(xdg-user-dir DOWNLOAD)
	else
        	failed "Upload to $REMOTE failed"
        	exit
	fi
else
	failed "Download to $BUILD_SERVER failed"
	exit
fi

if test -e "$(xdg-user-dir DOWNLOAD)/$FILE"; then
	sucess "Download to $(hostname) finished"
else
	failed "Download to $(hostname) failed"
	exit
fi
