#!/usr/bin/env python3
"""PostToolUse hook: record the session that wrote a preview, so its choice reaches it.

A preview belongs to the session whose tool call names its file in /tmp/previews and changed it
in the last minute, whether the call was a Write, an Edit or a shell command.
"""

import json
import os
import re
import sys
import time

import store

RECENT = 60  # Seconds since a preview changed for a call naming it to count as its writer.


def written(tool_input, now):
    """Returns the topics of previews named in `tool_input` that changed recently."""
    text = json.dumps(tool_input)
    topics = []
    for name in os.listdir(store.ROOT):
        topic = name.removesuffix(".html")
        if not name.endswith(".html") or not store.TOPIC.fullmatch(topic):
            continue
        # A bare name counts only in a call that also names the folder, as after `cd`.
        full = f"{store.ROOT}/{name}" in text
        if not full and not (store.ROOT in text
                             and re.search(rf"(?<![A-Za-z0-9_./-]){re.escape(name)}", text)):
            continue
        try:
            if now - os.stat(os.path.join(store.ROOT, name)).st_mtime <= RECENT:
                topics.append(topic)
        except FileNotFoundError:
            pass
    return topics


def main():
    hook = json.load(sys.stdin)
    session = hook.get("session_id")
    if not session or not os.path.isdir(store.ROOT):
        return
    for topic in written(hook.get("tool_input", {}), time.time()):
        store.set_owner(topic, session)


if __name__ == "__main__":
    main()
