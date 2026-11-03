#!/usr/bin/env python3
"""Collect today's trending and new GitHub repositories the user has not seen yet.

Sources, in the order their repositories are listed:
  - Trendshift: the daily ranking, read from the JSON embedded in its home page.
  - Show HN: posts of the last two days that link a GitHub repository and got some votes.
  - GitHub search: repositories created in the last week that already gathered stars.

Usage:
  trending.py fetch            prints the unseen repositories as JSON, without recording them
  trending.py mark-seen NAME…  records owner/repo names as seen, so they never come back

Each fetched repository carries what the summary page shows: its source ("trendshift",
"show_hn" or "new") with rank, stars gained and HN points, the GitHub numbers (stars, forks,
issues, language, license, created and pushed days), homepage, description, the first image of
its README and up to README_CHARS of the README itself. A field GitHub could not give is null.

The seen list is $XDG_STATE_HOME/trending-repos/seen.json ({"owner/repo": "first seen day"});
mark-seen also writes the day to last-run there, which tells the session-start hook it is done.
"""

import datetime
import functools
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
README_CHARS = 8000
# Markdown and HTML images, in the order they appear.
IMAGE = re.compile(r"!\[[^\]]*\]\(\s*<?([^)\s>]+)|<img\b[^>]*?\bsrc=[\"']([^\"']+)", re.IGNORECASE)
# Most READMEs open with status badges or star charts, which make a useless thumbnail.
BADGE_HOSTS = {"img.shields.io", "shields.io", "badgen.net", "badge.fury.io", "codecov.io",
               "api.star-history.com", "starchart.cc"}
BLOB_URL = re.compile(r"^https?://github\.com/([\w.-]+/[\w.-]+)/blob/")


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
        repos.append({"name": match[2], "source": "trendshift", "rank": int(match[1]),
                      "gained": int(gained[1]) if gained else None})
    if not repos:
        raise ValueError("no ranking found, the page format may have changed")
    repos.sort(key=lambda repo: repo["rank"])
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
            repos.append({"name": name, "source": "show_hn", "points": hit["points"]})
    return repos


@functools.cache
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


def github_headers(accept="application/vnd.github+json"):
    headers = {"Accept": accept}
    token = github_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


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
    url = f"https://api.github.com/search/repositories?{query}"
    items = json.loads(get(url, github_headers()))["items"]
    repos = []
    for item in items:
        description = item.get("description") or ""
        if not description or SPAM.search(f"{item['full_name']} {description}"):
            continue
        repos.append({"name": item["full_name"], "source": "new",
                      "gained": item["stargazers_count"]})
    return repos[:SEARCH_LIMIT]


def first_image(readme, name):
    """Returns the absolute URL of the first image in a README that is not a badge.

    Args:
        readme: the README text, Markdown or HTML.
        name: the repository's owner/repo, against which relative paths are resolved.

    Returns:
        The image URL, or None when the README has no image besides badges.
    """
    for match in IMAGE.finditer(readme):
        url = match[1] or match[2]
        parts = urllib.parse.urlparse(url)
        host, file = parts.netloc.lower(), parts.path.lower().rsplit("/", 1)[-1]
        # Only the file name: a repo named "badger" must keep its images.
        if host in BADGE_HOSTS or "badge" in file or file.endswith(".svg"):
            continue
        if url.startswith("//"):
            return f"https:{url}"
        if host:
            return BLOB_URL.sub(r"https://raw.githubusercontent.com/\1/", url)
        if url.startswith(("data:", "#")):
            continue
        return f"https://raw.githubusercontent.com/{name}/HEAD/{url.removeprefix('./').lstrip('/')}"
    return None


def enrich(repo):
    """Adds the GitHub numbers, the README and its first image to a fetched repository.

    Each GitHub call fails on its own, so a rate limit or a missing README leaves the repository
    on the list with null numbers or an empty README instead of dropping it.

    Args:
        repo: a repository from one of the sources, with at least "name".

    Returns:
        The same dict, with every field of the fetch output filled or null.
    """
    api = f"https://api.github.com/repos/{repo['name']}"
    try:
        info = json.loads(get(api, github_headers()))
    except Exception:  # noqa: BLE001
        info = {}
    try:
        readme = get(f"{api}/readme", github_headers("application/vnd.github.raw"))
    except Exception:  # noqa: BLE001
        readme = ""
    license_id = (info.get("license") or {}).get("spdx_id")
    repo.update({
        "url": f"https://github.com/{repo['name']}",
        "description": info.get("description") or repo.get("description"),
        "homepage": info.get("homepage") or None,
        "stars": info.get("stargazers_count"),
        "forks": info.get("forks_count"),
        "issues": info.get("open_issues_count"),
        "language": info.get("language"),
        "license": license_id if license_id != "NOASSERTION" else None,
        "created": (info.get("created_at") or "")[:10] or None,
        "pushed": (info.get("pushed_at") or "")[:10] or None,
        "image": first_image(readme, repo["name"]),
        "readme": readme[:README_CHARS],
    })
    for field in ("source", "rank", "gained", "points"):
        repo.setdefault(field, None)
    return repo


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
                repos.append(repo)
    json.dump(
        {"repos": [enrich(repo) for repo in repos[:MAX_TABS]],
         "left_for_later": len(repos[MAX_TABS:]), "failed": failed},
        sys.stdout,
        indent=2,
        # Escaped, a Chinese README takes six times the characters Claude has to read.
        ensure_ascii=False,
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
