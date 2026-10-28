#!/usr/bin/env python3
"""Add one day to the work diary and rebuild the diary page; print the page's path.

Merges the day's digest with Claude's notes into DIARY_DIR/<day>.recap.json, then rebuilds
DIARY_DIR/index.html from every *.recap.json in the folder: one page with the days on the
left and one day at a time on the right. With --rebuild only the page is rebuilt.

The digest groups sessions by repository; the page groups them by initiative, which only a
reader of the sessions can decide. The notes file says how:

    {
      "sessions": {"<session id>": {
        "title": "...", "summary": "...", "activity": "build", "hide": false
      }},
      "groups": [{
        "name": "K265 PSVI messages",
        "section": "Work",                      # optional heading above a run of groups
        "items": [{"text": "Built the PSVI position messages", "tickets": ["VP-589"],
                   "status": "approved"}],
        "sessions": ["<session id>", "..."]
      }, {
        "name": "Slack messages",               # work seen only in Slack
        "section": "Work",
        "slack": true,                          # its timeline row shows the Slack messages
        "items": [...],
        "sessions": []
      }],
      "slack": [{"time": "07:32", "channel": "#team", "topic": "..."}]
    }

"items" are one entry per piece of work (reruns of the same task are one item), each with a
status from STATUSES. Group names over MAX_NAME characters, and items whose text plus
BADGE_WIDTH characters per ticket badge is over MAX_ITEM, are rejected: they would not fit on
one line.

The recap and the page carry only what the page shows: no prompts, replies or file paths,
which can hold pasted secrets.

Every visible session needs an activity from ACTIVITIES and belongs to exactly one group;
hidden sessions belong to none. Unknown session ids exit with an error instead of silently
dropping a note.

Usage:
    render_recap.py DIGEST_JSON NOTES_JSON DIARY_DIR
    render_recap.py --rebuild DIARY_DIR
"""

import json
import pathlib
import sys
from collections import Counter

TEMPLATE = pathlib.Path(__file__).resolve().parent.parent / "assets" / "diary.html"
ACTIVITIES = ("build", "review", "plan", "other")
STATUSES = ("merged", "approved", "in review", "in progress", "done", "blocked", "discussed")
# Longest texts that still fit on one line of the page, so nothing wraps or gets cut.
MAX_NAME = 24
MAX_ITEM = 64
BADGE_WIDTH = 9


def merge(digest, notes):
    """Returns the day's recap: the notes' groups filled with the digest's sessions."""
    sessions = {s["id"]: s for p in digest["projects"] for s in p["sessions"]}
    session_notes = notes.get("sessions", {})
    problems = [f"unknown session {k}" for k in session_notes if k not in sessions]

    for session_id, session in sessions.items():
        note = session_notes.get(session_id, {})
        session["hidden"] = bool(note.get("hide"))
        session["summary"] = note.get("summary")
        session["title"] = note.get("title") or session["title"]
        session["activity"] = note.get("activity")
        if not session["hidden"] and session["activity"] not in ACTIVITIES:
            problems.append(f"session {session_id} needs an activity from {ACTIVITIES}")

    groups = notes.get("groups", [])
    problems += check_groups(groups, sessions)
    if problems:
        sys.exit("Notes do not match the digest:\n  " + "\n  ".join(problems))
    return {"date": digest["date"], "groups": fill(groups, sessions),
            "slack": notes.get("slack", [])}


def check_groups(groups, sessions):
    """Lists the ways the groups fail to place each visible session exactly once."""
    placed = Counter(sid for group in groups for sid in group["sessions"])
    items = [item for group in groups for item in group.get("items", [])]
    problems = [f"item '{item.get('text')}' needs a status from {STATUSES}"
                for item in items if item.get("status") not in STATUSES]
    problems += [f"group name '{group['name']}' is over {MAX_NAME} characters"
                 for group in groups if len(group["name"]) > MAX_NAME]
    problems += [f"item '{item.get('text')}' is too long: remove at least "
                 f"{width(item) - MAX_ITEM} of its characters"
                 for item in items if width(item) > MAX_ITEM]
    for session_id, count in placed.items():
        if session_id not in sessions:
            problems.append(f"unknown session {session_id}")
        elif sessions[session_id]["hidden"]:
            problems.append(f"hidden session {session_id} is grouped")
        elif count > 1:
            problems.append(f"session {session_id} is in {count} groups")
    problems += [f"session {sid} is in no group" for sid, s in sessions.items()
                 if not s["hidden"] and sid not in placed]
    return problems


def width(item):
    """Returns how many characters an item takes on its line, its ticket badges included."""
    return len(item.get("text", "")) + BADGE_WIDTH * len(item.get("tickets", []))


def public(session):
    """Returns the fields of a session the page shows, and nothing else."""
    languages = {}
    for f in session["files"]:
        languages[f["language"]] = languages.get(f["language"], 0) + f["added"] + f["removed"]
    return {
        "title": session["title"] or "Untitled session",
        "summary": session["summary"],
        "activity": session["activity"],
        "start": session["start"],
        "end": session["end"],
        "lines_added": session["lines_added"],
        "lines_removed": session["lines_removed"],
        "commit_count": len(session["commits"]),
        "languages": languages,
    }


def fill(groups, sessions):
    """Replaces session ids with sessions, keeping sections together and in time order."""
    filled = [{
        "name": group["name"],
        "section": group.get("section"),
        "slack": bool(group.get("slack")),
        "items": group.get("items", []),
        "sessions": sorted((public(sessions[sid]) for sid in group["sessions"]),
                           key=lambda s: s["start"]),
    } for group in groups if group["sessions"] or group.get("slack")]
    sections = list(dict.fromkeys(g["section"] for g in filled))

    # The Slack group goes last in its section: it is the context around the sessions.
    def order(group):
        start = group["sessions"][0]["start"] if group["sessions"] else ""
        return sections.index(group["section"]), group["slack"], start

    return sorted(filled, key=order)


def build_page(diary):
    """Writes diary/index.html with every recap in the folder and returns its path."""
    recaps = {}
    for path in sorted(diary.glob("*.recap.json")):
        recap = json.loads(path.read_text())
        recaps[recap["date"]] = recap
    # Keep "</script>" inside strings from closing the page's script tag.
    data = json.dumps(recaps, ensure_ascii=False).replace("</", "<\\/")
    page = diary / "index.html"
    page.write_text(TEMPLATE.read_text().replace("/*__DIARY__*/null", data))
    return page


def main():
    args = sys.argv[1:]
    if len(args) == 2 and args[0] == "--rebuild":
        diary = pathlib.Path(args[1]).expanduser().resolve()
    elif len(args) == 3:
        digest = json.loads(pathlib.Path(args[0]).read_text())
        notes = json.loads(pathlib.Path(args[1]).read_text())
        recap = merge(digest, notes)
        diary = pathlib.Path(args[2]).expanduser().resolve()
        diary.mkdir(parents=True, exist_ok=True)
        text = json.dumps(recap, ensure_ascii=False, indent=1)
        (diary / f"{recap['date']}.recap.json").write_text(text)
    else:
        sys.exit(__doc__)
    print(build_page(diary))


if __name__ == "__main__":
    main()
