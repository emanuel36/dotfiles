#!/usr/bin/env python3
"""Collect the facts needed to plan a branch history rewrite, as JSON.

For each commit between the base and HEAD it reports the author, the files and line counts,
and which earlier commit of the same branch wrote the lines it changes or removes (by blaming
the commit's parent). A commit whose changed lines all come from earlier branch commits is a
course correction candidate; one that changes lines from the base is a real change to
pre-existing code.

Usage:
    analyze_branch.py [--repo PATH] [--base REF] [--head REF]
"""

import argparse
import json
import re
import subprocess
import sys
from collections import Counter

INTEGRATION_NAMES = ("main", "master", "develop", "dev", "trunk")
SKIP_REF = re.compile(r"(^|/)(backup|tmp)/|/HEAD$")
HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
BLAME_HEADER = re.compile(r"^([0-9a-f]{40}) \d+ (\d+)")


def git(repo, *args, check=True):
    """Runs git in the repository and returns stdout."""
    result = subprocess.run(
        ["git", "-C", repo, *args], capture_output=True, text=True, check=False
    )
    if check and result.returncode != 0:
        sys.exit(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def lines(text):
    return [line for line in text.splitlines() if line.strip()]


def upstream(repo, branch):
    ref = f"{branch}@{{upstream}}"
    return git(repo, "rev-parse", "--abbrev-ref", ref, check=False).strip() or None


def base_candidates(repo, head, branch, own_upstream):
    """Ranks refs by how few commits HEAD has on top of them (closest base first)."""
    refs = lines(git(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads",
                     "refs/remotes"))
    found = {}
    for ref in refs:
        if ref in (branch, own_upstream) or SKIP_REF.search(ref):
            continue
        merge_base = git(repo, "merge-base", head, ref, check=False).strip()
        if not merge_base or merge_base == head:
            continue  # unrelated, or the ref already contains HEAD
        ahead = int(git(repo, "rev-list", "--count", f"{merge_base}..{head}").strip())
        short = ref.split("/", 1)[1] if ref.startswith(("origin/", "upstream/")) else ref
        found.setdefault(merge_base, []).append(
            {"ref": ref, "ahead": ahead, "integration": short in INTEGRATION_NAMES}
        )
    flat = [c for group in found.values() for c in group]
    flat.sort(key=lambda c: (c["ahead"], not c["integration"], "/" in c["ref"]))
    return flat[:5]


def blame_parent(repo, commit, path):
    """Maps each line number of path at commit^ to the commit that wrote it."""
    out = git(repo, "blame", "--porcelain", f"{commit}^", "--", path, check=False)
    owners = {}
    for line in out.splitlines():
        match = BLAME_HEADER.match(line)
        if match:
            owners[int(match.group(2))] = match.group(1)
    return owners


def changed_old_lines(repo, commit):
    """Yields (old_path, old_lines, added_only_anchor) per hunk of the commit."""
    diff = git(repo, "diff", "-U0", "--find-renames", f"{commit}^", commit)
    old_path = None
    for line in diff.splitlines():
        if line.startswith("--- "):
            old_path = None if line == "--- /dev/null" else line[6:]
        match = HUNK.match(line)
        if match and old_path:
            start, count = int(match.group(1)), int(match.group(2) or 1)
            if count:
                yield old_path, range(start, start + count), False
            else:
                # Pure insertion after line `start`: the neighbors hint at what it extends.
                yield old_path, range(max(start, 1), start + 2), True


def analyze_commit(repo, sha, branch_shas):
    parents = git(repo, "rev-list", "--parents", "-n1", sha).split()[1:]
    info = git(repo, "show", "-s", "--format=%an%x00%ae%x00%aI%x00%s%x00%b", sha).split("\x00")
    numstat = lines(git(repo, "show", "--format=", "--numstat", "--find-renames", sha))
    files = []
    for row in numstat:
        added, removed, path = row.split("\t", 2)
        files.append({"path": path, "added": added, "removed": removed})
    status = lines(git(repo, "show", "--format=", "--name-status", "--find-renames", sha))
    record = {
        "sha": sha,
        "short": sha[:7],
        "author": info[0],
        "email": info[1],
        "date": info[2],
        "subject": info[3],
        "body": info[4].strip(),
        "merge": len(parents) > 1,
        "files": files,
        "new_files": [s.split("\t")[-1] for s in status if s.startswith("A")],
        "deleted_files": [s.split("\t")[-1] for s in status if s.startswith("D")],
    }
    if record["merge"]:
        return record

    changed, adjacent = Counter(), Counter()
    blame_cache = {}
    for path, old_lines, insertion in changed_old_lines(repo, sha):
        owners = blame_cache.setdefault(path, blame_parent(repo, sha, path))
        target = adjacent if insertion else changed
        for number in old_lines:
            owner = owners.get(number)
            if owner:
                target[owner[:7] if owner in branch_shas else "base"] += 1
    record["changes_lines_from"] = dict(changed.most_common())
    record["inserts_next_to"] = dict(adjacent.most_common())
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", default=".")
    parser.add_argument("--base", help="Base ref; detected when omitted")
    parser.add_argument("--head", default="HEAD", help="Branch to analyze (default: HEAD)")
    args = parser.parse_args()
    repo = args.repo

    head = git(repo, "rev-parse", args.head).strip()
    branch = git(repo, "rev-parse", "--abbrev-ref", args.head).strip() or head[:7]
    own_upstream = upstream(repo, branch)
    candidates = base_candidates(repo, head, branch, own_upstream)
    base_ref = args.base or (candidates[0]["ref"] if candidates else None)
    if not base_ref:
        sys.exit("No base found; pass --base")
    base = git(repo, "merge-base", head, base_ref).strip()

    shas = lines(git(repo, "rev-list", "--reverse", f"{base}..{head}"))
    unpushed = set(lines(git(repo, "rev-list", f"{base}..{head}", "--not", "--remotes")))
    branch_shas = set(shas)
    commits = [analyze_commit(repo, sha, branch_shas) for sha in shas]
    for commit in commits:
        commit["published"] = commit["sha"] not in unpushed

    dependents = [
        ref for ref in lines(git(repo, "for-each-ref", "--contains", head,
                                 "--format=%(refname:short)", "refs/heads"))
        if ref != branch and not SKIP_REF.search(ref)
    ]

    print(json.dumps({
        "repo": git(repo, "rev-parse", "--show-toplevel").strip(),
        "branch": branch,
        "upstream": own_upstream,
        "base_ref": base_ref,
        "base_sha": base,
        "base_candidates": candidates,
        "dirty": args.head == "HEAD" and bool(git(repo, "status", "--porcelain").strip()),
        "published_commits": len(shas) - len(unpushed),
        "dependent_branches": dependents,
        "base_recent_subjects": lines(git(repo, "log", "--no-merges", "-n", "30",
                                          "--format=%s", base)),
        "commits": commits,
    }, indent=1))


if __name__ == "__main__":
    main()
