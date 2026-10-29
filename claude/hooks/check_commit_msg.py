#!/usr/bin/env python3
"""PreToolUse hook: block a Bash `git commit` whose message breaks the commit rules.

Rules (from the global CLAUDE.md): a Conventional Commits subject of at most 50 characters,
a blank line after it, and body lines of at most 72 characters. Merge, revert and
fixup!/squash!/amend! subjects are left alone, and so are body lines holding a URL.

The message is read from `-m`/`--message` (a `$(cat <<EOF ...)` heredoc included), from
`-F -` with a heredoc on stdin, or from `-F <file>`. A commit whose message cannot be read
(the editor, `--no-edit`, `-C <commit>`) is let through. Exit 2 blocks the call and shows the
problems to Claude.
"""

import json
import re
import shlex
import sys
from pathlib import Path

TYPES = ("feat", "fix", "docs", "style", "refactor", "perf", "test", "build", "ci", "chore",
         "revert")
SUBJECT = re.compile(rf"^(?:{'|'.join(TYPES)})(?:\([^()\s]+\))?!?: \S")
EXEMPT = ("Merge ", 'Revert "', "fixup! ", "squash! ", "amend! ")
SUBJECT_MAX = 50
BODY_MAX = 72
HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1[^\n]*\n(.*?)\n[ \t]*\2[ \t]*(?=\n|$)", re.S)
SEPARATORS = {"&&", "||", ";", "|", "&", "\n"}
SKIP_FLAGS = {"-C", "-c", "--reuse-message", "--reedit-message", "--fixup", "--squash",
              "--no-edit"}


def split_heredocs(command: str) -> tuple[str, list[str]]:
    """Returns the command without its heredoc bodies, and the bodies in order."""
    bodies = [match.group(3) for match in HEREDOC.finditer(command)]
    return HEREDOC.sub("<<HEREDOC", command), bodies


def commit_args(command: str) -> list[str] | None:
    """The arguments after `git [...] commit`, up to the next shell separator; None if none."""
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    tokens = list(lexer)
    for i, token in enumerate(tokens):
        if token != "git":
            continue
        j = i + 1
        while j < len(tokens) and tokens[j] in ("-C", "-c"):
            j += 2
        if j < len(tokens) and tokens[j] == "commit":
            args = []
            for arg in tokens[j + 1:]:
                if arg in SEPARATORS:
                    break
                args.append(arg)
            return args
    return None


def message_of(args: list[str], bodies: list[str], cwd: str) -> str | None:
    """The commit message the arguments give, or None when it cannot be read."""
    parts: list[str] = []
    heredocs = iter(bodies)
    i = 0
    while i < len(args):
        arg = args[i]
        flag, _, inline = arg.partition("=")
        if flag in SKIP_FLAGS or arg.startswith("--fixup") or arg.startswith("--squash"):
            return None
        if arg in ("-m", "--message", "-F", "--file") or (arg.startswith("-m") and len(arg) > 2):
            if arg.startswith("-m") and len(arg) > 2:
                value = arg[2:]
            else:
                i += 1
                if i >= len(args):
                    return None
                value = args[i]
            if arg in ("-F", "--file"):
                if value != "-":
                    path = Path(cwd, value).expanduser()
                    return path.read_text() if path.is_file() else None
                value = next(heredocs, None)
                if value is None:
                    return None
            elif "<<HEREDOC" in value:
                value = next(heredocs, None)
                if value is None:
                    return None
            parts.append(value)
        elif flag in ("--message", "--file") and inline:
            return message_of([flag, inline] + args[i + 1:], bodies, cwd)
        i += 1
    return "\n\n".join(parts) if parts else None


def problems(message: str) -> list[str]:
    """Every rule the message breaks."""
    lines = message.strip("\n").splitlines()
    if not lines:
        return ["the message is empty"]
    subject = lines[0]
    if subject.startswith(EXEMPT):
        return []
    found = []
    if not SUBJECT.match(subject):
        found.append(f"subject is not Conventional Commits `<type>[(<scope>)]: <description>` "
                     f"with type in {', '.join(TYPES)}: {subject!r}")
    if len(subject) > SUBJECT_MAX:
        found.append(f"subject has {len(subject)} characters, max {SUBJECT_MAX}: {subject!r}")
    if len(lines) > 1 and lines[1].strip():
        found.append("line 2 must be blank, between the subject and the body")
    for number, line in enumerate(lines[2:], start=3):
        if len(line) > BODY_MAX and "://" not in line:
            found.append(f"body line {number} has {len(line)} characters, max {BODY_MAX}")
    return found


def main() -> None:
    data = json.load(sys.stdin)
    command = data.get("tool_input", {}).get("command", "")
    if "commit" not in command:
        return
    stripped, bodies = split_heredocs(command)
    try:
        args = commit_args(stripped)
    except ValueError:
        return
    if args is None:
        return
    message = message_of(args, bodies, data.get("cwd", "."))
    if message is None:
        return
    found = problems(message)
    if found:
        print("Commit message breaks the commit rules; rewrite it and commit again:",
              file=sys.stderr)
        for problem in found:
            print(f"- {problem}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
