#!/usr/bin/env python3
"""Merge a day digest with Claude's notes into the recap page and print the page's path.

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

To compare ways of dividing the day, "groupings" may replace "groups":
{"<label>": [group, ...], ...}; the page then offers a switch between them.

"items" are one entry per piece of work (reruns of the same task are one item), each with a
status from STATUSES. Group names and item texts longer than MAX_NAME and MAX_ITEM characters
are rejected: they would not fit on one line.

The page carries only what it shows: no prompts, replies or file paths, which can hold pasted
secrets, end up in its source.

Every visible session needs an activity from ACTIVITIES and belongs to exactly one group;
hidden sessions belong to none. Unknown session ids exit with an error instead of silently
dropping a note.

Usage:
    render_recap.py DIGEST_JSON NOTES_JSON OUTPUT_HTML
"""

import json
import pathlib
import sys
from collections import Counter

TEMPLATE = pathlib.Path(__file__).resolve().parent.parent / "assets" / "recap.html"
ACTIVITIES = ("build", "review", "plan", "other")
STATUSES = ("merged", "approved", "in review", "in progress", "done", "blocked", "discussed")
# Longest texts that still fit on one line of the page, so nothing wraps or gets cut.
MAX_NAME = 24
MAX_ITEM = 64


def merge(digest, notes):
    """Returns the page data: the notes' groups filled with the digest's sessions."""
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

    groupings = notes.get("groupings") or {"": notes.get("groups", [])}
    for label, groups in groupings.items():
        problems += check_groups(label, groups, sessions)
    if problems:
        sys.exit("Notes do not match the digest:\n  " + "\n  ".join(problems))
    return {
        "date": digest["date"],
        "groupings": {label: fill(groups, sessions) for label, groups in groupings.items()},
        "slack": notes.get("slack", []),
    }


def check_groups(label, groups, sessions):
    """Lists the ways a grouping fails to place each visible session exactly once."""
    where = f" in grouping '{label}'" if label else ""
    placed = Counter(sid for group in groups for sid in group["sessions"])
    problems = [f"item '{item.get('text')}' needs a status from {STATUSES}{where}"
                for group in groups for item in group.get("items", [])
                if item.get("status") not in STATUSES]
    problems += [f"group name '{group['name']}' is over {MAX_NAME} characters{where}"
                 for group in groups if len(group["name"]) > MAX_NAME]
    problems += [f"item '{item.get('text')}' is over {MAX_ITEM} characters{where}"
                 for group in groups for item in group.get("items", [])
                 if len(item.get("text", "")) > MAX_ITEM]
    for session_id, count in placed.items():
        if session_id not in sessions:
            problems.append(f"unknown session {session_id}{where}")
        elif sessions[session_id]["hidden"]:
            problems.append(f"hidden session {session_id} is grouped{where}")
        elif count > 1:
            problems.append(f"session {session_id} is in {count} groups{where}")
    problems += [f"session {sid} is in no group{where}" for sid, s in sessions.items()
                 if not s["hidden"] and sid not in placed]
    return problems


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


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    digest = json.loads(pathlib.Path(sys.argv[1]).read_text())
    notes = json.loads(pathlib.Path(sys.argv[2]).read_text())
    recap = merge(digest, notes)

    # Keep "</script>" inside strings from closing the page's script tag.
    data = json.dumps(recap, ensure_ascii=False).replace("</", "<\\/")
    page = TEMPLATE.read_text().replace("/*__RECAP__*/null", data)
    output = pathlib.Path(sys.argv[3]).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page)
    print(output)


if __name__ == "__main__":
    main()
