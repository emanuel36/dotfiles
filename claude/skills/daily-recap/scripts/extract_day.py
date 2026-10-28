#!/usr/bin/env python3
"""Collect one day of Claude Code sessions into a compact JSON digest.

Reads the session transcripts under ~/.claude/projects and keeps only what a daily recap needs:
per project, the sessions active that day with their title, branches, typed prompts and last
reply, the lines Claude added and removed per file, and the commits, pushes and pull requests
made that day. Subagent transcripts count toward their parent session. Only events whose
timestamp falls inside the local day are used, so a session that crosses midnight is split.

Commits come from two sources merged by SHA: what the transcripts recorded (git's output and
Claude Code's own record of git operations), and `git log` of that day, by the user, in every
repository the sessions ran git in. The second catches quiet commits (`-q`) and ones made by
hand; the first keeps commits from repositories that no longer exist. Each commit belongs to
the session that recorded it or, failing that, to the session that ran git in its repository
closest to the commit time. Subagents add edits but no git activity, since the main session
already runs git in every real repository it works on. Files and repositories under /tmp or
inside skill-creator eval workspaces are throwaway test fixtures and ignored.

It also lists, per session, the actions taken in other tools (Jira, Confluence, Slack, Bitbucket,
GitHub, Gmail, Drive) and the documents produced: HTML, PDF, Markdown and Office files that
Claude pointed the user to in its replies, modified that day and not tracked by git (so output,
not source, and not scratch files Claude never mentioned).

Usage:
    extract_day.py [--date YYYY-MM-DD] [--projects-dir PATH] [--out FILE]
"""

import argparse
import difflib
import json
import pathlib
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache

PROMPT_CHARS = 400
REPLY_CHARS = 600
MAX_PROMPTS = 40
TICKET = re.compile(r"\b([A-Z][A-Z0-9]{1,9}-[1-9][0-9]{0,5})\b")
NOT_TICKETS = {"UTF", "ISO", "SHA", "RFC", "CVE", "MD", "COVID", "TLS", "SSL", "HTTP"}
SLASH_COMMAND = re.compile(
    r"<command-name>([^<]+)</command-name>(?:.*<command-args>(.*?)</command-args>)?", re.S
)
# Session housekeeping that says nothing about the work done.
TRIVIAL_PROMPTS = re.compile(
    r"^(/(clear|resume|exit|compact|reload-plugins|model|config|status|cost|context|login|"
    r"logout|doctor|permissions|plugin|mcp|help|fast)\b.*|\[Request interrupted[^\]]*\])$",
    re.S,
)
# The first line git prints after a commit: "[branch abc1234] subject".
COMMIT_LINE = re.compile(r"^\[(?:[^\]\s]+ )*?(?:\(root-commit\) )?([0-9a-f]{7,40})\] (.+)$", re.M)
GIT_DIR = re.compile(r"""(?:\bcd\s+|\bgit\s+-C\s+)(["']?)([^\s"';&|)]+)\1""")
LANGUAGES = {
    ".py": "Python", ".go": "Go", ".kt": "Kotlin", ".kts": "Kotlin", ".java": "Java",
    ".js": "JavaScript", ".mjs": "JavaScript", ".ts": "TypeScript", ".tsx": "TypeScript",
    ".jsx": "JavaScript", ".sh": "Shell", ".bash": "Shell", ".zsh": "Shell", ".c": "C",
    ".h": "C", ".cpp": "C++", ".hpp": "C++", ".rs": "Rust", ".rb": "Ruby", ".lua": "Lua",
    ".html": "HTML", ".css": "CSS", ".scss": "CSS", ".sql": "SQL", ".md": "Markdown",
    ".json": "JSON", ".yaml": "YAML", ".yml": "YAML", ".toml": "TOML", ".xml": "XML",
    ".gradle": "Gradle", ".proto": "Protobuf", ".tf": "Terraform", ".swift": "Swift",
}
# Write operations in other tools, by tool or operation name, as the reader would call them.
ACTIONS = {
    "slack_send_message": "Slack message", "slack_send_message_draft": "Slack draft",
    "slack_schedule_message": "Slack scheduled message",
    "slack_create_canvas": "Slack canvas created", "slack_update_canvas": "Slack canvas updated",
    "createJiraIssue": "Jira issue created", "editJiraIssue": "Jira issue edited",
    "transitionJiraIssue": "Jira status changed", "addCommentToJiraIssue": "Jira comment",
    "addOrEditJiraIssueComment": "Jira comment", "addWorklogToJiraIssue": "Jira worklog",
    "createIssueLink": "Jira link", "createConfluencePage": "Confluence page created",
    "createConfluenceContent": "Confluence page created",
    "updateConfluencePage": "Confluence page updated",
    "updateConfluenceContent": "Confluence page updated",
    "createConfluenceFooterComment": "Confluence comment",
    "createConfluenceInlineComment": "Confluence comment",
    "addBitbucketRepoPullRequestComment": "Bitbucket PR comment",
    "createBitbucketRepoPullRequest": "Bitbucket PR opened",
    "updateBitbucketRepoPullRequest": "Bitbucket PR updated",
    "create_draft": "Email draft", "create_file": "Drive file created",
    "update_file": "Drive file updated",
}
GH_ACTION = re.compile(r"\bgh\s+(pr|issue)\s+(comment|review|edit|merge|close|create)\b")
GH_API_WRITE = re.compile(
    r"\bgh\s+api\b(?=.*(?:-X|--method)\s*(?:POST|PATCH|PUT))"
    r".*?repos/([\w.-]+/[\w.-]+)/(?:pulls|issues)/(\d+)/(reviews|comments)"
)
DOC_EXTENSIONS = r"\.(?:html|pdf|md|docx|pptx|xlsx)"
DOCUMENT = re.compile(
    rf"""`([^`\s]+{DOC_EXTENSIONS})`|(?:^|[\s'"(])((?:~|/)[^\s'"`<>|;&()]+{DOC_EXTENSIONS})\b"""
)
HOME = pathlib.Path.home()
# Scratch files, eval fixtures and Claude's own state are not work the user would call
# "code written".
IGNORED_PATH = re.compile(
    rf"^(/tmp/|{re.escape(str(HOME / '.claude' / 'projects'))}/)|-workspace/iteration-\d+/"
)
GIT_COMMIT = re.compile(r"\bgit\b[^|;&]*\bcommit\b")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--date", help="local day to collect, YYYY-MM-DD (default: today)")
    parser.add_argument("--projects-dir", default=str(HOME / ".claude" / "projects"))
    parser.add_argument("--out", help="write the JSON here instead of stdout")
    return parser.parse_args()


def day_bounds(day):
    """Returns the UTC start and end of a local calendar day."""
    start = datetime.combine(day, datetime.min.time()).astimezone()
    return start.astimezone(timezone.utc), (start + timedelta(days=1)).astimezone(timezone.utc)


def parse_ts(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def local_hhmm(ts):
    return ts.astimezone().strftime("%H:%M")


def language(path):
    name = pathlib.PurePath(path).name
    if name in ("Makefile", "Dockerfile"):
        return name
    return LANGUAGES.get(pathlib.PurePath(path).suffix.lower(), "Other")


def short_path(path):
    try:
        return "~/" + str(pathlib.Path(path).relative_to(HOME))
    except ValueError:
        return str(path)


def git(cwd, *args):
    """Runs git in cwd and returns stdout, or None when git fails or cwd is gone."""
    if not cwd or not pathlib.Path(cwd).is_dir():
        return None
    result = subprocess.run(
        ["git", "-C", cwd, *args], capture_output=True, text=True, check=False
    )
    return result.stdout if result.returncode == 0 else None


@lru_cache(maxsize=None)
def repo_root(path):
    """Returns the top level of the git repository holding a directory, or None."""
    top = git(path, "rev-parse", "--show-toplevel")
    return top.strip() if top else None


def edit_counts(result):
    """Returns (added, removed) lines for an Edit or Write tool result."""
    if result.get("structuredPatch"):
        lines = [line for hunk in result["structuredPatch"] for line in hunk.get("lines", [])]
        return sum(l.startswith("+") for l in lines), sum(l.startswith("-") for l in lines)
    if result.get("type") == "create":
        return len(result.get("content", "").splitlines()), 0
    if "oldString" in result:
        diff = list(difflib.ndiff(
            result["oldString"].splitlines(), result.get("newString", "").splitlines()
        ))
        return sum(l.startswith("+ ") for l in diff), sum(l.startswith("- ") for l in diff)
    return 0, 0


def prompt_text(entry):
    """Returns what the user typed in a transcript entry, or None for anything else."""
    if entry.get("isMeta") or entry.get("promptSource") == "system":
        return None
    content = entry["message"].get("content")
    if isinstance(content, list):
        if any(block.get("type") == "tool_result" for block in content):
            return None
        content = "\n".join(b.get("text", "") for b in content if b.get("type") == "text")
    if not isinstance(content, str) or not content.strip():
        return None
    command = SLASH_COMMAND.search(content)
    if command:
        text = f"{command.group(1).strip()} {(command.group(2) or '').strip()}".strip()
    elif content.lstrip().startswith("<"):
        return None
    else:
        text = content.strip()
    return None if TRIVIAL_PROMPTS.match(text) else text


def command_dirs(command, cwd):
    """Returns the directories a shell command runs git in: cwd, then each `cd` or `git -C`."""
    base = pathlib.Path(cwd or HOME)
    found = [pathlib.Path(directory).expanduser() for _, directory in GIT_DIR.findall(command)]
    return [str(base)] + [str(base / directory) for directory in found]


def tool_call(entry, tool_calls):
    """Returns the (tool_use block, cwd) a tool result answers, or empty values."""
    content = entry["message"].get("content")
    for block in content if isinstance(content, list) else []:
        if isinstance(block, dict) and block.get("type") == "tool_result":
            return tool_calls.get(block.get("tool_use_id"), ({}, None))
    return {}, None


def action_for(block):
    """Returns (kind, target) when a tool call writes to another tool, else None."""
    name = block.get("name") or ""
    tool_input = block.get("input") or {}
    if name == "Bash":
        command = tool_input.get("command") or ""
        api = GH_API_WRITE.search(command)
        if api:
            repo = api.group(1).split("/")[1]
            return f"GitHub PR {api.group(3)[:-1]}", f"{repo}#{api.group(2)}"
        cli = GH_ACTION.search(command)
        # `gh pr create` already shows up as a pull request of the session.
        if cli and (cli.group(1), cli.group(2)) != ("pr", "create"):
            noun = "PR" if cli.group(1) == "pr" else "issue"
            return f"GitHub {noun} {cli.group(2)}", None
        return None
    if not name.startswith("mcp__"):
        return None
    operation = name.split("__")[-1]
    if operation in ("executeWrite", "executeDestructive"):
        operation = tool_input.get("name") or operation
        tool_input = tool_input.get("inputs") or {}
    kind = ACTIONS.get(operation)
    if not kind:
        return None
    if tool_input.get("pending"):
        kind += " (draft)"
    if tool_input.get("repoId"):
        pr = tool_input.get("prId")
        return kind, tool_input["repoId"] + (f"#{pr}" if pr else "")
    tickets = sorted(tickets_in(json.dumps(tool_input)))
    if tickets:
        return kind, tickets[0]
    return kind, tool_input.get("title") or tool_input.get("channel_name")


def document_paths(text, cwd):
    """Returns the document paths a reply mentions, resolved against the session directory."""
    base = pathlib.Path(cwd or HOME)
    found = [quoted or bare for quoted, bare in DOCUMENT.findall(text)]
    return [str(base / pathlib.Path(path).expanduser()) for path in found]


def produced_documents(paths, start, end):
    """Keeps the paths modified inside the day that git does not track (output, not source)."""
    kept = []
    for path in sorted(set(paths)):
        file = pathlib.Path(path).resolve()
        hidden = any(part.startswith(".") for part in file.parts[len(HOME.parts):])
        if IGNORED_PATH.search(str(file)) or hidden or not file.is_file():
            continue
        if not start.timestamp() <= file.stat().st_mtime < end.timestamp():
            continue
        if git(str(file.parent), "ls-files", "--error-unmatch", file.name) is not None:
            continue
        kept.append(short_path(path))
    return kept


def reply_text(entry):
    blocks = entry["message"].get("content") or []
    if isinstance(blocks, str):
        return blocks.strip()
    return "\n".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()


def clip(text, limit):
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def tickets_in(*texts):
    found = set()
    for text in texts:
        for match in TICKET.findall(text or ""):
            if match.split("-")[0] not in NOT_TICKETS:
                found.add(match)
    return found


class Session:
    """Day-filtered facts about one session, including its subagents' work."""

    def __init__(self, session_id):
        self.id = session_id
        self.title = None
        self.cwd = None
        self.branches = set()
        self.first = self.last = None
        self.prompts = []
        self.last_reply = None
        self.files = defaultdict(lambda: [0, 0])
        self.commits = {}
        self.git_dirs = defaultdict(list)
        self.pushes = set()
        self.prs = {}
        self.tickets = set()
        self.subagents = 0
        self.skills = set()
        self.actions = []
        self.documents = set()

    def touch(self, ts):
        self.first = ts if self.first is None or ts < self.first else self.first
        self.last = ts if self.last is None or ts > self.last else self.last

    def read(self, path, start, end, subagent=False):
        """Adds the entries of one transcript file that fall inside [start, end)."""
        tool_calls = {}
        with open(path, encoding="utf-8", errors="replace") as handle:
            for raw in handle:
                try:
                    entry = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                kind = entry.get("type")
                if kind == "ai-title" and not subagent:
                    self.title = entry.get("aiTitle") or self.title
                    continue
                ts = parse_ts(entry.get("timestamp"))
                if ts is None or not start <= ts < end:
                    continue
                if not subagent:
                    self.cwd = self.cwd or entry.get("cwd")
                    if entry.get("gitBranch") not in (None, "", "HEAD"):
                        self.branches.add(entry["gitBranch"])
                if kind == "assistant":
                    self.read_assistant(entry, ts, subagent, tool_calls)
                elif kind == "user":
                    self.read_user(entry, ts, subagent, tool_calls)

    def read_assistant(self, entry, ts, subagent, tool_calls):
        for block in entry["message"].get("content") or []:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            tool_calls[block.get("id")] = (block, entry.get("cwd") or self.cwd)
            if block.get("name") == "Skill" and not subagent:
                self.skills.add((block.get("input") or {}).get("skill"))
            command = (block.get("input") or {}).get("command") or ""
            if not subagent and re.search(r"\bgit\b", command):
                for directory in command_dirs(command, entry.get("cwd") or self.cwd):
                    self.git_dirs[directory].append(ts)
            if subagent:
                continue
            self.touch(ts)
            if block.get("name") == "Agent":
                self.subagents += 1
            if "jira" in block.get("name", "").lower():
                self.tickets |= tickets_in(json.dumps(block.get("input", {})))
        if not subagent and reply_text(entry):
            self.last_reply = reply_text(entry)
            self.documents.update(document_paths(self.last_reply, entry.get("cwd") or self.cwd))

    def read_user(self, entry, ts, subagent, tool_calls):
        content = entry["message"].get("content")
        for block in content if isinstance(content, list) else []:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                call = tool_calls.get(block.get("tool_use_id"))
                if call and not block.get("is_error"):
                    self.read_action(call[0], block, ts)
        result = entry.get("toolUseResult")
        if isinstance(result, dict):
            self.read_tool_result(result, tool_call(entry, tool_calls), subagent)
        if subagent:
            return
        self.touch(ts)
        text = prompt_text(entry)
        if text and text.startswith("/"):
            self.skills.add(text.split()[0].lstrip("/"))
        if text:
            self.prompts.append({"time": local_hhmm(ts), "text": clip(text, PROMPT_CHARS)})
            self.tickets |= tickets_in(text)

    def read_tool_result(self, result, call, subagent):
        path = result.get("filePath")
        if path and ("structuredPatch" in result or "oldString" in result):
            if not IGNORED_PATH.search(path):
                added, removed = edit_counts(result)
                self.files[path][0] += added
                self.files[path][1] += removed
        block, cwd = call
        command = (block.get("input") or {}).get("command") or ""
        if subagent or IGNORED_PATH.search(command_dirs(command, cwd)[-1] + "/"):
            return
        if GIT_COMMIT.search(command):
            for sha, subject in COMMIT_LINE.findall(result.get("stdout") or ""):
                self.add_commit(sha, subject=subject)
        operation = result.get("gitOperation") or {}
        if operation.get("commit", {}).get("sha"):
            commit = operation["commit"]
            self.add_commit(commit["sha"], kind=commit.get("kind"), branch=commit.get("branch"))
        if operation.get("push", {}).get("branch"):
            self.pushes.add(operation["push"]["branch"])
        if operation.get("pr", {}).get("url"):
            pr = operation["pr"]
            self.prs[pr["url"]] = {"url": pr["url"], "number": pr.get("number"),
                                   "action": pr.get("action")}

    def read_action(self, block, result_block, ts):
        action = action_for(block)
        if not action:
            return
        kind, target = action
        self.actions.append({"time": local_hhmm(ts), "kind": kind, "target": target})
        if kind == "Bitbucket PR opened":
            text = json.dumps(result_block.get("content"))
            url = re.search(r"https://bitbucket\.org/[\w.-]+/[\w.-]+/pull-requests/(\d+)", text)
            if url:
                self.prs[url.group(0)] = {"url": url.group(0), "number": int(url.group(1)),
                                          "action": "created"}

    def add_commit(self, sha, **facts):
        commit = self.commits.setdefault(sha[:7], {"sha": sha[:7]})
        commit.update({key: value for key, value in facts.items() if value})

    def to_json(self):
        prompts = self.prompts
        if len(prompts) > MAX_PROMPTS:
            half = MAX_PROMPTS // 2
            skipped = {"time": "", "text": f"[{len(prompts) - MAX_PROMPTS} prompts omitted]"}
            prompts = prompts[:half] + [skipped] + prompts[-half:]
        return {
            "id": self.id,
            "title": self.title,
            "start": local_hhmm(self.first),
            "end": local_hhmm(self.last),
            "branches": sorted(self.branches),
            "prompt_count": len(self.prompts),
            "prompts": prompts,
            "last_reply": clip(self.last_reply or "", REPLY_CHARS),
            "subagents": self.subagents,
            "lines_added": sum(a for a, _ in self.files.values()),
            "lines_removed": sum(r for _, r in self.files.values()),
            "files": [
                {"path": short_path(p), "language": language(p), "added": a, "removed": r}
                for p, (a, r) in sorted(self.files.items(), key=lambda i: -sum(i[1]))
            ],
            "skills": sorted(s for s in self.skills if s),
            "actions": self.actions,
            "documents": self.documents,
            "pushes": sorted(self.pushes),
            "prs": list(self.prs.values()),
            "tickets": sorted(self.tickets),
        }


def collect(projects_dir, day):
    start, end = day_bounds(day)
    # A file last written before the day began cannot hold events from it.
    cutoff = start.timestamp()
    sessions = []
    for path in sorted(projects_dir.glob("*/*.jsonl")):
        if path.stat().st_mtime < cutoff:
            continue
        session = Session(path.stem)
        session.read(path, start, end)
        for sub in sorted((path.parent / path.stem / "subagents").glob("*.jsonl")):
            if sub.stat().st_mtime >= cutoff:
                session.read(sub, start, end, subagent=True)
        # Sessions started in /tmp are automated probes and spikes, not the user's work.
        if (session.cwd or "").startswith("/tmp/"):
            continue
        if session.first and (session.prompts or session.files or session.commits):
            session.documents = produced_documents(session.documents, start, end)
            sessions.append(session)
    return sessions


def day_commits(repo, day):
    """Returns the user's commits of the day in a repository, keyed by short SHA."""
    since = datetime.combine(day, datetime.min.time()).astimezone()
    email = (git(repo, "config", "user.email") or "").strip()
    log = git(
        repo, "log", "--all", "--no-merges", f"--since={since.isoformat()}",
        f"--until={(since + timedelta(days=1)).isoformat()}", f"--author={email}",
        "--format=%h%x09%ct%x09%s",
    ) if email else None
    commits = {}
    for line in (log or "").splitlines():
        sha, epoch, subject = line.split("\t", 2)
        when = datetime.fromtimestamp(int(epoch), timezone.utc)
        commits[sha[:7]] = {"sha": sha[:7], "subject": subject, "repo": repo, "time": when}
    return commits


def line_counts(repo, sha):
    numstat = git(repo, "show", "--numstat", "--format=", sha) or ""
    counts = [line.split("\t") for line in numstat.splitlines()]
    counts = [c for c in counts if len(c) == 3 and c[0].isdigit() and c[1].isdigit()]
    return sum(int(c[0]) for c in counts), sum(int(c[1]) for c in counts)


def assign_commits(sessions, day):
    """Gives each commit of the day to one session; returns {session id: [commit, ...]}."""
    activity = defaultdict(list)
    for session in sessions:
        for directory, times in session.git_dirs.items():
            root = repo_root(directory)
            if root and not IGNORED_PATH.search(root + "/"):
                activity[root] += [(ts, session.id) for ts in times]
    logged = {}
    for repo in activity:
        logged.update(day_commits(repo, day))

    owned = defaultdict(list)
    recorded = set()
    for session in sessions:
        for sha, commit in session.commits.items():
            if sha in recorded:
                continue
            recorded.add(sha)
            commit = {**commit, **logged.pop(sha, {})}
            if "repo" not in commit:
                commit["repo"] = next(
                    (r for r in activity if git(r, "cat-file", "-e", f"{sha}^{{commit}}")
                     is not None), None,
                )
            owned[session.id].append(commit)
    for commit in logged.values():
        nearest = min(activity[commit["repo"]], key=lambda a: abs(a[0] - commit["time"]))
        owned[nearest[1]].append(commit)

    for commits in owned.values():
        for commit in commits:
            commit.pop("time", None)
            if commit.get("repo"):
                commit["added"], commit["removed"] = line_counts(commit["repo"], commit["sha"])
        commits.sort(key=lambda c: c.get("subject") or "")
    return owned


def home_project(session, commits):
    """Returns the project a session belongs to.

    That is the repository of its working directory or, when it was started outside any
    repository (~/Downloads, ~/workspace), the repository it edited and committed to most.
    """
    root = repo_root(session.cwd)
    if root:
        return root
    weight = Counter()
    for path, (added, removed) in session.files.items():
        file_root = repo_root(str(pathlib.Path(path).parent))
        if file_root:
            weight[file_root] += added + removed
    for commit in commits:
        if commit.get("repo"):
            weight[commit["repo"]] += commit.get("added", 0) + commit.get("removed", 0) + 1
    return weight.most_common(1)[0][0] if weight else session.cwd or "unknown"


def summarize(day, sessions):
    commits_by_session = assign_commits(sessions, day)
    groups = defaultdict(list)
    for session in sessions:
        groups[home_project(session, commits_by_session.get(session.id, []))].append(session)

    by_language = defaultdict(lambda: {"added": 0, "removed": 0, "files": 0})
    projects = []
    for root, members in groups.items():
        items = sorted((s.to_json() for s in members), key=lambda s: s["start"])
        for item in items:
            item["commits"] = [
                {**c, "repo": pathlib.PurePath(c["repo"]).name if c.get("repo") else None}
                for c in commits_by_session.get(item["id"], [])
            ]
        commits = [c for s in items for c in s["commits"]]
        for item in items:
            for f in item["files"]:
                stats = by_language[f["language"]]
                stats["added"] += f["added"]
                stats["removed"] += f["removed"]
                stats["files"] += 1
        tickets = {t for s in items for t in s["tickets"]}
        tickets |= tickets_in(*(c.get("subject") for c in commits))
        tickets |= tickets_in(*(b for s in items for b in s["branches"] + s["pushes"]))
        projects.append({
            "name": pathlib.PurePath(root).name,
            "path": short_path(root),
            "start": items[0]["start"],
            "end": max(s["end"] for s in items),
            "lines_added": sum(s["lines_added"] for s in items),
            "lines_removed": sum(s["lines_removed"] for s in items),
            "commit_count": len(commits),
            "pr_count": sum(len(s["prs"]) for s in items),
            "tickets": sorted(tickets),
            "sessions": items,
        })
    projects.sort(key=lambda p: p["start"])

    all_sessions = [s for p in projects for s in p["sessions"]]
    return {
        "date": day.isoformat(),
        "weekday": day.strftime("%A"),
        "home": str(HOME),
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "totals": {
            "projects": len(projects),
            "sessions": len(all_sessions),
            "prompts": sum(s["prompt_count"] for s in all_sessions),
            "lines_added": sum(s["lines_added"] for s in all_sessions),
            "lines_removed": sum(s["lines_removed"] for s in all_sessions),
            "files": len({f["path"] for s in all_sessions for f in s["files"]}),
            "commits": sum(p["commit_count"] for p in projects),
            "prs": sum(p["pr_count"] for p in projects),
            "first": min((s["start"] for s in all_sessions), default=None),
            "last": max((s["end"] for s in all_sessions), default=None),
        },
        "by_language": dict(sorted(by_language.items(),
                                   key=lambda i: -(i[1]["added"] + i[1]["removed"]))),
        "projects": projects,
    }


def main():
    args = parse_args()
    day = date.fromisoformat(args.date) if args.date else date.today()
    projects_dir = pathlib.Path(args.projects_dir).expanduser()
    if not projects_dir.is_dir():
        sys.exit(f"No Claude Code projects directory at {projects_dir}")
    digest = summarize(day, collect(projects_dir, day))
    text = json.dumps(digest, indent=1, ensure_ascii=False)
    if args.out:
        out = pathlib.Path(args.out).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text)
        print(out)
    else:
        print(text)


if __name__ == "__main__":
    main()
