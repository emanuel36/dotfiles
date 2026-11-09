---
name: fold-branch
description: >-
  Rewrite the current git branch's history into clean, logical commits: fold course corrections,
  fixups, review fixes, reverts and mid-branch redesigns into the commits they belong to, so the
  history reads as if the final decisions were made from the start. Plans first (a before/after
  map in the terminal for approval), then rewrites with backup, stash, per-commit build/tests and an
  identical final tree. Use this whenever the user wants to organize, clean up, tidy, squash,
  fold or reorganize the commits of a branch, rewrite branch history, says the commits got messy
  ("ficou desorganizado", "organiza os commits", "reescreve o histórico", "junta os fixes nos
  commits certos", "tira as correções de curso"), asks whether a branch has too many commits, or
  wants a dry-run plan of how a branch would be folded, including before opening a PR. Not for
  writing a single new commit, editing one commit message, or git questions that do not rewrite
  history.
---

# Fold branch

Turn a branch whose history shows how the work happened (attempts, fixes, renames, review
rounds) into a history that shows what the work is: a short sequence of commits where each one
is a coherent change that builds and passes its tests. Reviewers read commits one by one, and
`git bisect` and `git blame` are only useful when each commit is real and self-contained.

The guiding rule: **tell the final story**. A fix to something created earlier on the same
branch is not a separate event for the reader; it belongs inside the commit that created the
thing. Only changes to code that existed before the branch are events in their own right.

Write the plan, the commit messages and the final report in **English**. Talk to the user
in their own language.

## Modes

- **Plan only (dry run):** the user asks what would change, wants a plan, or is looking at
  someone else's branch. Stop after step 4.
- **Fold:** the default. After the user approves the plan, execute it without further questions,
  except for the published-branch confirmation in step 5.

## 1. Gather facts

Run the analysis from the repository (it only reads):

```bash
python3 <skill-dir>/scripts/analyze_branch.py [--base <ref>] [--head <ref>] > <scratch>/fold.json
```

It reports, per commit: author, files and line counts, new/deleted files, whether it is
published, and two blame-based signals:

- `changes_lines_from`: which commits wrote the lines this commit modifies or deletes. Keys are
  short SHAs of branch commits, or `"base"` for code that existed before the branch.
- `inserts_next_to`: for pure insertions, which commits wrote the neighboring lines. Weaker
  signal: it tells what the insertion extends.

Also at the top level: `base_candidates` (closest first), `dirty`, `published_commits`,
`dependent_branches` (local branches stacked on top) and `base_recent_subjects` (for detecting
the message convention).

**Pick the base.** The closest candidate is usually right, including when the branch is stacked
on another feature branch (then the base is that branch, not the integration branch). If your
memory has a base branch recorded for this repo, prefer it. If candidates tie and disagree in a
way that matters, ask.

Then read the actual diffs (`git show <sha>`) of every commit. The signals point you to likely
targets, but the classification is a judgment about intent, so look at the code.

## 2. Classify each commit

| Class | What it is | Action |
|---|---|---|
| `keep` | A coherent new behavior, module or refactor | Keep; may get a better message |
| `fold` | Fix, adjustment, rename or tidy of code created earlier on the branch | Fold into the commit that created those lines |
| `redesign` | The approach changed mid-branch (own helper replaced by a shared one, data model reshaped) | Rewrite the original commit so it is born with the final design |
| `review` | Changes made in response to review comments | Fold into the commits they touch, split by hunk if needed |
| `lint` | Formatting, line length, imports of branch code | Fold |
| `drop` | Debug code, temporary logs, an addition later reverted on the branch | Remove (both sides of an add/revert pair) |
| `base-fix` | A change to code that existed before the branch | Its own commit: it is a real change the reviewer must see |
| `split` | One commit mixing several of the above | Split by hunk, then classify each part |
| `changelog` | Changelog / version file edits | One entry, in the last commit of the ticket |

How to read the signals: a commit whose `changes_lines_from` is entirely branch commits is a
`fold`/`redesign`/`review`/`lint` candidate, and the dominant key is the likely target. Lines from
`"base"` mean at least part of it is `base-fix` or a legitimate part of a feature that edits
existing code; the diff decides which. A commit with no `changes_lines_from` and only new files is
usually `keep`.

Merge commits from the base into the branch disappear: the rewrite rebases onto the base and
resolves each conflict in the commit where it belongs.

## 3. Shape the new history

- **Order:** foundations first (constants, shared helpers, preparatory refactors), then data and
  model, then each behavior, then wiring (DI, modules, configuration), then docs. A commit must
  never use something introduced by a later one.
- **Granularity is the user's call, so offer options.** The right size depends on the project,
  the reviewers and the change, so when more than one grouping is reasonable, print each one in the
  plan as a variant (step 4) and let the user pick. Typical pair:
  - **Compact:** small related commits (under ~30 lines of production code, or not meaningful
    alone) merge into their neighbor.
  - **Granular:** one commit per observable change, however small.
  Mark the one you would pick as recommended and say why. If only one grouping
  makes sense (e.g. two clearly separate features), a single plan is fine. In every variant, each
  commit gets a one-line reason explaining why it stands alone.
- **Tests** go in the same commit as the code they test; there is no "add tests" commit.
- **Each commit builds and passes its tests.** If an intermediate state cannot build (for
  example, a caller and a callee changed together), they belong in the same commit.
- **Authors:** a folded commit keeps the author of its target. When a folded-in change came from a
  different author, add a `Co-authored-by` trailer. A rebuilt commit takes the author who wrote
  most of its lines.
- **Attribution trailer:** every commit the rewrite produces gets the session's commit
  attribution trailer (for example `Co-Authored-By: Claude ...`), including commits whose only
  change is the message and commits by other people. Be consistent: either all rewritten commits
  have it or the session requires none. Keep any trailers the commits already had.
- **Messages:** rewrite messages even for kept commits when a better one exists.
  1. Use the repository's convention, found in `base_recent_subjects`, CONTRIBUTING, README,
     AGENTS.md or CLAUDE.md. Example convention: `VP-589 Send ignitionReport on each ignition
     change` (ticket key, then an imperative sentence).
  2. Add a body of one-line bullets: only what the commit changes in behavior and why. This
     matters most for commits that absorbed several fixes, because the "why" of those fixes
     would otherwise be lost. Leave out what is obvious from the diff or true of every commit
     ("Cover each function with unit tests"), and never comment on the history itself ("Changes
     code that existed before this branch", "Folds the review fix"): the message describes the
     code, and the history story belongs in the plan and the report.
  3. If the repository has no convention, use the user's global one (their CLAUDE.md; typically
     Conventional Commits with a subject of 50 characters or fewer and body lines of 72 or
     fewer).

### Strategy (hybrid)

Decide per segment of the history and note it in each new commit's detail line:

- **`fixup`** (default): every old commit maps cleanly to one target. Reorder and fold with a
  generated rebase todo list. Cheap, keeps authorship, and conflicts are rare when fixes only
  touch branch-created lines.
- **`rebuild`**: a mid-branch redesign, or a segment that conflicts repeatedly when reordered.
  Rebuild that segment's commits from the final tree.
- **`keep`**: untouched apart from maybe the message.

`references/rewrite-recipes.md` has the exact git sequences for each, plus splitting, authorship,
stacked branches, verification and undo. Read it before step 6.

## 4. Present the plan

Show the plan in the chat as a **flow map** inside one code block; no HTML page, file or browser
window. Old commits on the left, new commits on the right, joined by lines, so the user sees where
each fix went:

```
feature/VP-589-psvi-reports on develop-k265   9 → 3   hybrid

BEFORE                           AFTER
● 2253223 Add PSVI message model ──┐
● b943290 Shared unit conversion ──┴──▶ ◆ N1 Add PSVI message model  fixup · 2 commits

● 7cea060 Save last CAN odometer ──┐
● e41d9a2 Fix speed rounding     ──┼──▶ ◆ N2 Consolidate speed and odometer
● c0f3b18 Review: rename cache   ──┘      fixup · 3 commits · +co-author

● a5eaff1 Ignition on a timer    ──┐
● d8830be Report on change       ──┴──▶ ◆ N3 Send ignitionReport on change
                                          rebuild · redesign
● f19c7d4 Debug log              ──✕ dropped
● 9b02e66 Revert debug log       ──✕ dropped

⚠ published: force-push needed (you push)   ⚠ stacked: feature/VP-590-...
Compact (3) ★ recommended: mode() is 4 lines, only useful with mean/median
Granular (5): one commit per function
Which do I apply?
```

- **Header:** branch, base, commit count before → after, strategy.
- **Left column:** every current commit, oldest first, `● <sha> <subject>`. A commit that is
  dropped ends in `──✕ dropped` instead of joining a group.
- **Right column:** each new commit `◆ N<k> <subject>` on the middle row of its group, then one
  detail line with `method · what it absorbed · co-author` when relevant (it may follow the
  subject on the same row when the group has two commits).
- **Alignment:** pad the left column to the longest subject so the connectors form one column;
  keep every line within the terminal width (shorten subjects with `…` if needed).
- **Warnings:** one line at the end for anything the user must decide or know: a published
  branch, dependent branches, `base-fix` commits, ambiguous targets, commits by other people.

Below the map, list for each new commit the full message (subject and body bullets), author, why
it stands alone and its changed files (`M path +42 -7`), in a second code block. Derive
the files from the `files` of the old commits it absorbs (in the analysis JSON), netting out what
they cancel: a file created and later deleted on the branch disappears, and a file created on the
branch stays `A` even when later commits modify it. For `rebuild` and `split` commits, take it
from the planned diff, not from the old commits.

**Several groupings:** print one map per grouping under its name (for example **Compact** and
**Granular**), mark the recommended one with the reason, and ask which to apply.

The user approves in chat, or comments per commit (`N3: merge into N2`). Apply the comments,
print the plan again and repeat until they approve. In plan-only mode, stop here.

If the user approved in advance ("já aprovo o plano", "pode executar direto"), still print the
plan, then execute the recommended variant without waiting, and name the alternatives in the
report so they can ask for a different grouping (the backup makes that cheap).

## 5. Safety before rewriting

- **Published commits** (`published_commits > 0`): the rewrite will need a force-push and affects
  anyone else with the branch. Ask for explicit confirmation naming the branch, even if the plan
  was approved. Never push; the user pushes.
- **Commits already on the base or on other branches** stay untouched. Only `base..HEAD` is
  rewritten.
- **Backup:** `git branch backup/<branch>-pre-fold` (add a timestamp if it exists). Back up
  dependent branches too.
- **Dirty worktree:** `git stash push --include-untracked -m fold-branch`, and `git stash pop` at
  the end.

## 6. Rewrite

Follow the plan exactly, using the recipes. Write message files first, then run the rebase or
rebuild. If something in the plan turns out impossible (an unexpected conflict that changes the
shape of the history), stop and show the user what changed instead of improvising a different
history.

Then move dependent branches onto the new tip (recipe: dependent branches).

## 7. Verify

1. **Same final tree:** `git diff backup/<branch>-pre-fold HEAD` prints nothing. Any difference
   must be one the user approved (for example, a dropped debug log); list each one in the report.
2. **Per-commit build and tests,** in a temporary worktree outside the user's checkout and in the
   background: for each commit, build and run the tests of the modules it touches; at the tip, run
   the full relevant suite. Get the commands from memory, the repo's CLAUDE.md/AGENTS.md/README, or
   ask once. Never run builds or tests in the user's checkout: they leave caches and build output
   behind (`__pycache__/`, `build/`), and the checkout must end with exactly the files it had.
   Compare `git status --porcelain` before and after; anything new that you created goes.
3. **Lint and line length** at the tip, on the lines the branch introduces.
4. `git range-diff backup/<branch>-pre-fold...HEAD` for the report.

If a commit fails, fix it in that commit (the content moves between commits; the final tree stays
the same) and re-verify.

## 8. Report and follow-ups

Report in English, briefly:

- A before → after table: new commit, the old commits it absorbed, test result per commit.
- Final-tree check result and any approved differences.
- Dependent branches moved, and their checks.
- Backup name, stash status, and how to undo:
  `git reset --hard backup/<branch>-pre-fold`.
- If published: that a force-push is needed, which the user does.

Then:

- **PR description:** if the branch has an open pull request, write an updated description draft
  as markdown in the current directory (`pr-<branch>.md`) reflecting the new commits, and tell
  the user its path. Do not post it.
- **Remember the repo's conventions:** save to memory what you had to discover for this repository
  and that is not already there: the message convention, the base branch, and the build and test
  commands. Next time, step 1 starts from them.
