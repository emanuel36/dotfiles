#!/bin/bash

BLDLOG_PATH="/localrepo/eangelim/bldlogs/"

repoClean(){
        rm -rf out/
}

buildLunchTarget(){
        LUNCH_TARGET="$1"

        bldlog motorola/build/bin/build_device.bash -b nightly -p $LUNCH_TARGET -g -j22

        BUILD_RESULT=$(zcat $BLDLOG_PATH$(cd $BLDLOG_PATH; find . -type f -printf '%T@ %p\n' | sort -n | tail -1 | awk -F '/' '{print $2}') | tail -n 100 | grep --text "Build Success" | awk '{print $3}')

        echo $BUILD_RESULT

        if [ $BUILD_RESULT -eq 0 ]
        then
                repoClean
                bldlog motorola/build/bin/build_device.bash -b nightly -p $LUNCH_TARGET -g -j22
        fi
}

buildLunchTarget cebu_lenovo
buildLunchTarget cebu_retcn
