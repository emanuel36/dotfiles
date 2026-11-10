#!/usr/bin/env python3
"""UserPromptSubmit hook: hand the session the choices confirmed in its previews.

A choice belongs to the session that last wrote the preview (see own.py); previews written
before ownership was recorded fall back to the session whose transcript names the file. A
delivered choice moves to the preview's history, so it is delivered once and never mistaken
for a later round's choice. stdout becomes context for the prompt.
"""

import json
import os
import sys

import store


def mentioned(transcript, topic):
    try:
        with open(transcript, encoding="utf-8", errors="replace") as f:
            return f"{store.ROOT}/{topic}.html" in f.read()
    except (OSError, TypeError):
        return False


def deliver(topic):
    """Moves the pending choice of `topic` to its history and returns the text to hand over."""
    path = os.path.join(store.ROOT, f"{topic}.choice.json")
    with open(path, encoding="utf-8") as f:
        text = f.read().strip()
    try:
        version = store.valid_version(topic, json.loads(text).get("version"))
    except (ValueError, AttributeError):
        version = None
    saved = store.versions(topic)
    folder = store.history(topic)
    os.makedirs(folder, exist_ok=True)
    stamp = int(os.stat(path).st_mtime * 1000)
    os.replace(path, os.path.join(folder, f"{version or 'unversioned'}-{stamp}.choice.json"))
    if version and saved and version != saved[-1]:
        state = f"for version {version}; the preview is now at version {saved[-1]}"
    else:
        state = f"for version {version}" if version else "unversioned"
    return f"Choice confirmed in preview `{topic}` ({state}):\n{text}"


def main():
    hook = json.load(sys.stdin)
    session, transcript = hook.get("session_id"), hook.get("transcript_path")
    if not session or not os.path.isdir(store.ROOT):
        return
    delivered = []
    for name in sorted(os.listdir(store.ROOT)):
        topic = name.removesuffix(".choice.json")
        if not name.endswith(".choice.json") or not store.TOPIC.fullmatch(topic):
            continue
        owner = store.owner(topic)
        if owner != session and (owner or not mentioned(transcript, topic)):
            continue
        try:
            delivered.append(deliver(topic))
        except OSError:
            continue
    if delivered:
        print("\n\n".join(delivered))


if __name__ == "__main__":
    main()
