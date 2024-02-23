#!/bin/bash

if [ -n "$1" ]; then
    echo "Downloading files..."
    wget -r -np -l 1 -nd -A.txt.gz "$1"
fi

echo "Extracting '*.gz'..."
gunzip *.txt.gz

declare -A files=(["m"]="main" ["s"]="system" ["e"]="events" ["k"]="kernel" ["r"]="radio" ["c"]="crash")

boot_list=$(ls Boot-*.txt | awk -F"[-_]" '{ print $2; }' | uniq)

for boot_num in $boot_list; do
    echo "Concatenating boot $boot_num..."
    boot_dir=Boot-$boot_num
    mkdir $boot_dir
    
    # Concatenate in one file for each stream (main, system, events, kernel, radio, crash)
    for f in "${!files[@]}"; do
        echo "[${files[$f]}]"
        cat $(ls Boot-$boot_num\_*-$f*.txt) > $boot_dir/aplogcat-${files[$f]}.txt
    done
    echo
done

echo "Cleaning up..."
mkdir -p rawfiles
mv Boot-*.txt rawfiles/

echo "Done!"
