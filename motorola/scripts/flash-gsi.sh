#!/bin/bash

boot_gsi()
{
    adb shell "gsi_tool enable"
    adb reboot
}

ask()
{
    while true; do
        read -p "$1 ([y]es or [n]o): " ans
        lower=$(echo $ans | tr '[A-Z]' '[a-z]')
        case "$lower" in
            y|yes) return 0 ;;
            n|no) return 1 ;;
            *) echo "Unknown input $lower" ;;
        esac
    done
}

[ $# -ne 1 ] && echo "Error: please specify img file or img zip. Run $(basename $0) -h for help" && exit 0

if [ "$1" == "-h" ]; then
    cat <<- xx
$(basename $0)

Usage: $(basename $0) [-r|-w|-h|<file>]

Options:
  <file>    File containing the system.img. Can be the image itself or a zip containing it.
  -r        Return to Moto image
  -w        Wipe installed system.img and return to Moto image.
  -g        Boot into Google's system.img
  -h        Show this help message
xx
    exit 0
fi

adb wait-for-device

[ "$1" == "-r" ] && (([ "$(adb shell 'gsi_tool status' | tail -n 1)" != "disabled" ] && adb shell "gsi_tool disable" && adb reboot) || echo "Image is already disabled!") && exit 0
[ "$1" == "-w" ] && adb shell "gsi_tool wipe" && adb reboot && exit 0
[ "$1" == "-g" ] && (([ "$(adb shell 'gsi_tool status' | tail -n 1)" != "enabled" ] && boot_gsi) || echo "Image is already enabled!" ) && exit 0


if ask "Flash boot-debug.img?"; then
    imgpath=""
    if [ -f "boot-debug.img" ]; then
        imgpath="./boot-debug.img"
    elif hash zenity &> /dev/null; then
        imgpath=$(zenity --file-selection --file-filter='*.img' 2> /dev/null)
    fi
        [ ! -z "$imgpath" ] && adb reboot bootloader && fastboot flash boot "$imgpath" && fastboot reboot && adb wait-for-device
fi

tmpfolder=""
if [ ${1: -4} == ".zip" ];
then
    tmpfolder="/tmp/${1%.*}"
    if [ ! -d "/tmp/${1%.*}" ];
    then
        echo "Unzipping folder and getting system.img..."
        mkdir -p "$tmpfolder"
        unzip "$1" -d $tmpfolder
    fi
    sysimg="$tmpfolder/system.img"
elif [ ${1: -4} == ".img" ];
then
    echo "Getting system.img"
    sysimg="$1"
else
    echo "Error: Unknown specified $1 extension. Please specify img or zip file!"
    exit 0
fi

if [ -z "$tmpfolder" ] || [ ! -f "$tmpfolder/system.raw.gz" ];
then
    echo "Extracting system.img..."
    gzip -c "$sysimg" > "$tmpfolder/system.raw.gz"
    echo $(ls -lh system.raw.gz)
fi

echo "Pushing system.img to device..."
adb root
adb push "$tmpfolder/system.raw.gz" /storage/emulated/0/Download

echo "Setting persist.sys.fflag.override.settings_dynamic_system as true..."
adb shell setprop persist.sys.fflag.override.settings_dynamic_system true

adb shell am start-activity \
    -n com.android.dynsystem/com.android.dynsystem.VerificationActivity \
    -a android.os.image.action.START_INSTALL \
    -d file:///storage/emulated/0/Download/system.raw.gz \
    --el KEY_SYSTEM_SIZE $(du -b "$sysimg"|cut -f1) \
    --el KEY_USERDATA_SIZE 8589934592
echo "Installing image, please check device and tap 'Restart' when it finishes!"
