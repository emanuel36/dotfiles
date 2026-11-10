"""Layout of /tmp/previews shared by the preview server and hooks.

`<topic>.html` is the current preview and `<topic>.choice.json` a choice not yet delivered.
`.history/<topic>/<n>.html` keeps every version of a preview and `<n>-<ms>.choice.json` each
choice already delivered for version n. `.owners/<topic>` names the session that last wrote the
preview.
"""

import filecmp
import os
import re
import shutil
import time

ROOT = "/tmp/previews"
TOPIC = re.compile(r"[A-Za-z0-9_-]+")


def history(topic):
    return os.path.join(ROOT, ".history", topic)


def versions(topic):
    """Returns the saved version numbers of preview `topic`, oldest first."""
    try:
        names = os.listdir(history(topic))
    except FileNotFoundError:
        return []
    return sorted(int(n.removesuffix(".html")) for n in names
                  if n.endswith(".html") and n.removesuffix(".html").isdigit())


def snapshot(topic, settle=0.0):
    """Saves the current preview `topic` as a new version unless it equals the latest one, and
    returns the current version number.

    Returns None when the preview does not exist or changed less than `settle` seconds ago, so
    a file still being written is not saved as a version.
    """
    src = os.path.join(ROOT, f"{topic}.html")
    try:
        if time.time() - os.stat(src).st_mtime < settle:
            return None
    except FileNotFoundError:
        return None
    saved = versions(topic)
    folder = history(topic)
    if saved and filecmp.cmp(src, os.path.join(folder, f"{saved[-1]}.html"), shallow=False):
        return saved[-1]
    version = saved[-1] + 1 if saved else 1
    os.makedirs(folder, exist_ok=True)
    shutil.copyfile(src, os.path.join(folder, f"{version}.html"))
    return version


def valid_version(topic, version):
    """Returns `version` when it is a saved version of preview `topic`, else None."""
    return version if type(version) is int and version in versions(topic) else None


def owner(topic):
    """Returns the id of the session that last wrote preview `topic`, or None."""
    try:
        with open(os.path.join(ROOT, ".owners", topic)) as f:
            return f.read().strip() or None
    except OSError:
        return None


def set_owner(topic, session):
    os.makedirs(os.path.join(ROOT, ".owners"), exist_ok=True)
    with open(os.path.join(ROOT, ".owners", topic), "w") as f:
        f.write(session)
