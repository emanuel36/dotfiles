#!/usr/bin/env python3
"""Build today's page of trending repositories, open it in Chrome and mark its repos as seen.

Merges the repositories from `trending.py fetch` with Claude's summaries into
WORKDIR/today.json and renders WORKDIR/today.html from assets/page.html, sorted by stars. A
second run on the same day adds its repos to the page; the first run of a day starts it over.
WORKDIR is $TRENDING_WORKDIR, by default /tmp/trending-repos.

The summaries file holds one entry per repository Claude summarized, in Portuguese:

    {"owner/repo": {
      "what": "Two or three sentences on the problem it solves and how.",
      "who": "Who it is for.",
      "alternatives": "Like X, but Y." or null,
      "maturity": one of MATURITIES,
      "translated_from": "chinês" or null     # the README's language, unless pt or en
    }}

A repository with no entry still goes on the page, with its GitHub description. An entry for a
repository that is not in the fetch output, or with a missing field, exits with an error and
writes nothing.

Repos are marked seen only once Chrome was launched: when it cannot be (no display), the page
is written, nothing is marked, and the exit status is 1, so the session-start hook retries.

Usage:
    render_page.py REPOS_JSON SUMMARIES_JSON
    render_page.py --open      reopens today's page
"""

import datetime
import json
import os
import pathlib
import subprocess
import sys

import trending

TEMPLATE = pathlib.Path(__file__).resolve().parent.parent / "assets" / "page.html"
MATURITIES = ("protótipo", "beta", "pronto para uso", "educacional")
TEXT_FIELDS = ("what", "who")
OPTIONAL_FIELDS = ("alternatives", "translated_from")


def workdir():
    return pathlib.Path(os.environ.get("TRENDING_WORKDIR", "/tmp/trending-repos"))


def check(summaries, names):
    """Lists the ways the summaries do not fit the fetched repositories."""
    if not isinstance(summaries, dict):
        return ["the summaries file must be an object keyed by owner/repo"]
    problems = []
    for name, summary in summaries.items():
        if name not in names:
            problems.append(f"{name} is not in the fetched repositories")
            continue
        if not isinstance(summary, dict):
            problems.append(f"{name}: the summary must be an object")
            continue
        problems += [f"{name}: '{field}' must be a non-empty string" for field in TEXT_FIELDS
                     if not isinstance(summary.get(field), str) or not summary[field].strip()]
        problems += [f"{name}: '{field}' must be a string or null" for field in OPTIONAL_FIELDS
                     if not isinstance(summary.get(field), (str, type(None)))]
        if summary.get("maturity") not in MATURITIES:
            problems.append(f"{name}: 'maturity' must be one of {MATURITIES}")
    return problems


def merge(repos, summaries, today, previous):
    """Returns today's page data: the repositories with their summaries, by stars.

    Args:
        repos: the "repos" list printed by `trending.py fetch`.
        summaries: Claude's summaries, by owner/repo.
        today: the day, as YYYY-MM-DD.
        previous: the page data saved by an earlier run, or None.

    Returns:
        {"date": today, "repos": [...]}, each repo without its README and with its summary or
        None, sorted by stars, repos with unknown stars last.
    """
    problems = check(summaries, {repo["name"] for repo in repos})
    if problems:
        sys.exit("Summaries do not match the repositories:\n  " + "\n  ".join(problems))
    page = {}
    if previous and previous.get("date") == today:
        page = {repo["name"]: repo for repo in previous["repos"]}
    for repo in repos:
        entry = {key: value for key, value in repo.items() if key != "readme"}
        page[repo["name"]] = {**entry, "summary": summaries.get(repo["name"])}
    ordered = sorted(page.values(), key=lambda repo: (repo["stars"] is None, -(repo["stars"] or 0)))
    return {"date": today, "repos": ordered}


def write_page(page):
    """Saves the page data and renders today.html; returns the page's path."""
    directory = workdir()
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "today.json").write_text(json.dumps(page, ensure_ascii=False, indent=1))
    # No "<" at all in the injected data: "</script>" would close the page's script tag and
    # "<!--<script" would keep the real closing tag from ending it.
    data = json.dumps(page, ensure_ascii=False).replace("<", "\\u003c")
    path = directory / "today.html"
    path.write_text(TEMPLATE.read_text().replace("/*__DATA__*/null", data))
    return path


def open_page(path):
    """Opens the page in Chrome; returns False when Chrome cannot be launched."""
    if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        return False
    try:
        subprocess.Popen(["google-chrome", str(path)], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
    except OSError:
        return False
    return True


def load_previous():
    try:
        return json.loads((workdir() / "today.json").read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    today = datetime.date.today().isoformat()
    if args == ["--open"]:
        previous = load_previous()
        if not previous or previous.get("date") != today:
            sys.exit("There is no page for today yet.")
        path = workdir() / "today.html"
        if not open_page(path):
            sys.exit(f"Chrome could not be launched; the page is at {path}")
        print(path)
        return
    if len(args) != 2:
        sys.exit(__doc__)
    repos = json.loads(pathlib.Path(args[0]).read_text())["repos"]
    summaries = json.loads(pathlib.Path(args[1]).read_text())
    page = merge(repos, summaries, today, load_previous())
    path = write_page(page)
    if not open_page(path):
        sys.exit(f"Chrome could not be launched, so nothing was marked as seen: {path}")
    trending.mark_seen([repo["name"] for repo in page["repos"]])
    print(path)


if __name__ == "__main__":
    main()
