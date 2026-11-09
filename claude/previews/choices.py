#!/usr/bin/env python3
"""UserPromptSubmit hook: hand the session the choices confirmed in its previews.

A choice belongs to the session whose transcript mentions the preview's file, so a session
never receives another session's choice. Each choice is delivered once per version; stdout
becomes context for the prompt.
"""

import json
import os
import sys

ROOT = "/tmp/previews"
SEEN = os.path.join(ROOT, ".seen")


def main():
    hook = json.load(sys.stdin)
    session, transcript = hook.get("session_id"), hook.get("transcript_path")
    if not session or not transcript or not os.path.isdir(ROOT):
        return
    try:
        with open(transcript, encoding="utf-8", errors="replace") as f:
            history = f.read()
    except OSError:
        return
    seen_path = os.path.join(SEEN, session)
    try:
        with open(seen_path) as f:
            seen = json.load(f)
    except (OSError, ValueError):
        seen = {}

    delivered = []
    for name in sorted(os.listdir(ROOT)):
        if not name.endswith(".choice.json"):
            continue
        topic = name.removesuffix(".choice.json")
        path = os.path.join(ROOT, name)
        try:
            mtime = os.stat(path).st_mtime
            if seen.get(name) == mtime or f"{ROOT}/{topic}.html" not in history:
                continue
            with open(path, encoding="utf-8") as f:
                choice = f.read().strip()
        except OSError:
            continue
        seen[name] = mtime
        delivered.append(f"Choice confirmed in preview `{topic}` ({path}):\n{choice}")

    if delivered:
        print("\n\n".join(delivered))
        os.makedirs(SEEN, exist_ok=True)
        with open(seen_path, "w") as f:
            json.dump(seen, f)


if __name__ == "__main__":
    main()
