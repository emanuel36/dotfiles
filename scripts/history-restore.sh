#!/usr/bin/env bash
# Decrypt the backed-up history and put it before the current ~/.zsh_history.
# Meant for a new machine: running it where the history already exists duplicates entries.
set -euo pipefail

repo="$(cd "$(dirname "$0")/.." && pwd)"
key="${AGE_KEY:-$repo/secrets/key.txt}"

tmp="$(mktemp)"
age -d -i "$key" -o "$tmp" "$repo/secrets/zsh_history.age"
[ -f "$HOME/.zsh_history" ] && cat "$HOME/.zsh_history" >> "$tmp"
mv "$tmp" "$HOME/.zsh_history"
echo "Restored history ($(wc -l < "$HOME/.zsh_history") lines)."
