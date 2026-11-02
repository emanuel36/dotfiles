#!/usr/bin/env python3
"""Collect today's trending and new GitHub repositories the user has not seen yet.

Sources, in the order their repositories are listed:
  - Trendshift: the daily ranking, read from the JSON embedded in its home page.
  - Show HN: posts of the last two days that link a GitHub repository and got some votes.
  - GitHub search: repositories created in the last week that already gathered stars.

Usage:
  trending.py fetch            prints the unseen repositories as JSON, without recording them
  trending.py mark-seen NAME…  records owner/repo names as seen, so they never come back

The seen list is $XDG_STATE_HOME/trending-repos/seen.json ({"owner/repo": "first seen day"});
mark-seen also writes the day to last-run there, which tells the session-start hook it is done.
"""

import datetime
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

STATE = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "trending-repos"
SEEN = STATE / "seen.json"
MAX_TABS = int(os.environ.get("TRENDING_MAX_TABS", "30"))
HN_MIN_POINTS = 10
SEARCH_MIN_STARS = 100
SEARCH_LIMIT = 15
# Names and descriptions that mark the bought-star and malware repos the search turns up.
SPAM = re.compile(
    r"\b(miner|crack(ed)?|cheats?|keygen|aimbot|injector|spoofer|executor|robux|unlocker)\b",
    re.IGNORECASE,
)
REPO_URL = re.compile(r"^https?://(?:www\.)?github\.com/([\w.-]+)/([\w.-]+)")
# The names go into the prompt of an unattended run, so anything else is dropped.
VALID_NAME = re.compile(r"[\w.-]+/[\w.-]+")
NOT_OWNERS = {"orgs", "sponsors", "features", "topics", "collections", "marketplace", "apps"}


def get(url, headers=None):
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", **(headers or {})})
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read().decode()


def repo_name(url):
    """Returns owner/repo for a github.com repository URL, or None."""
    match = REPO_URL.search(url or "")
    if not match or match[1].lower() in NOT_OWNERS:
        return None
    return f"{match[1]}/{match[2].removesuffix('.git')}"


def trendshift():
    page = get("https://trendshift.io/").replace('\\"', '"')
    matches = list(re.finditer(r'"rank":(\d+),"score":\d+,"full_name":"([^"]+)"', page))
    repos = []
    for match, after in zip(matches, matches[1:] + [None]):
        # The entry ends where the next one starts, so its star count is never the next one's.
        entry = page[match.end() : after.start() if after else match.end() + 2000]
        gained = re.search(r'"repository_stars_gained":(\d+)', entry)
        reason = f"Trendshift #{match[1]}"
        if gained:
            reason += f", +{gained[1]} stars"
        repos.append({"rank": int(match[1]), "name": match[2], "reason": reason})
    if not repos:
        raise ValueError("no ranking found, the page format may have changed")
    repos.sort(key=lambda repo: repo.pop("rank"))
    return repos


def show_hn():
    since = int(time.time()) - 2 * 86400
    query = urllib.parse.urlencode(
        {
            "tags": "show_hn",
            "numericFilters": f"created_at_i>{since},points>={HN_MIN_POINTS}",
            "hitsPerPage": 200,
        }
    )
    hits = json.loads(get(f"https://hn.algolia.com/api/v1/search_by_date?{query}"))["hits"]
    repos = []
    for hit in sorted(hits, key=lambda hit: -hit["points"]):
        name = repo_name(hit.get("url"))
        if name:
            repos.append({"name": name, "reason": f"Show HN, {hit['points']} points"})
    return repos


def github_token():
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    try:
        result = subprocess.run(
            ["gh", "auth", "token"], check=False, capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() or None


def new_on_github():
    since = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    query = urllib.parse.urlencode(
        {
            "q": f"created:>{since} stars:>{SEARCH_MIN_STARS} fork:false archived:false",
            "sort": "stars",
            "order": "desc",
            "per_page": 50,
        }
    )
    headers = {"Accept": "application/vnd.github+json"}
    token = github_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    items = json.loads(get(f"https://api.github.com/search/repositories?{query}", headers))["items"]
    repos = []
    for item in items:
        description = item.get("description") or ""
        if not description or SPAM.search(f"{item['full_name']} {description}"):
            continue
        created = item["created_at"][:10]
        reason = f"New on GitHub, {item['stargazers_count']} stars since {created}"
        repos.append({"name": item["full_name"], "reason": reason})
    return repos[:SEARCH_LIMIT]


def load_seen():
    try:
        return json.loads(SEEN.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def fetch():
    seen = {name.lower() for name in load_seen()}
    repos, failed = [], []
    for source in (trendshift, show_hn, new_on_github):
        # One source down must not hide the others.
        try:
            found = source()
        except Exception as error:  # noqa: BLE001
            failed.append(f"{source.__name__}: {error!r}")
            continue
        for repo in found:
            if VALID_NAME.fullmatch(repo["name"]) and repo["name"].lower() not in seen:
                seen.add(repo["name"].lower())
                repo["url"] = f"https://github.com/{repo['name']}"
                repos.append(repo)
    json.dump(
        {"repos": repos[:MAX_TABS], "left_for_later": len(repos[MAX_TABS:]), "failed": failed},
        sys.stdout,
        indent=2,
    )
    print()


def mark_seen(names):
    seen = load_seen()
    today = datetime.date.today().isoformat()
    for name in names:
        name = repo_name(name) or name
        seen.setdefault(name, today)
    STATE.mkdir(parents=True, exist_ok=True)
    SEEN.write_text(json.dumps(seen, indent=1, sort_keys=True) + "\n")
    (STATE / "last-run").write_text(today + "\n")
    print(f"{len(names)} marked as seen, {len(seen)} in total")


if __name__ == "__main__":
    if sys.argv[1:2] == ["fetch"]:
        fetch()
    elif sys.argv[1:2] == ["mark-seen"] and sys.argv[2:]:
        mark_seen(sys.argv[2:])
    else:
        sys.exit(__doc__)
