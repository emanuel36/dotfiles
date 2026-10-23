#!/usr/bin/env bash
# Encrypt ~/.zsh_history into the repo. Needs only the public key, so it runs anywhere.
set -euo pipefail

repo="$(cd "$(dirname "$0")/.." && pwd)"
age -R "$repo/secrets/recipient.txt" -o "$repo/secrets/zsh_history.age" "$HOME/.zsh_history"
echo "Updated secrets/zsh_history.age — commit it to save the backup."
