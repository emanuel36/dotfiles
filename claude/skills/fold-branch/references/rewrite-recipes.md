# Rewrite recipes

Git mechanics for each strategy. Read the section that the approved plan needs.

## Contents
- Setup and teardown (backup, stash)
- Fixup + autosquash (the default path)
- Rebuilding a segment from the final tree
- Splitting a mixed commit
- Authorship
- Dependent (stacked) branches
- Per-commit verification
- Undo

## Setup and teardown

```bash
git branch backup/<branch>-pre-fold            # add -<yyyymmdd-hhmm> if it exists
git stash push --include-untracked -m fold-branch   # only if the worktree is dirty
# ... rewrite and verify ...
git stash pop                                  # only if you stashed
```

If `git stash pop` conflicts, stop and report the conflicting files; the stash entry stays in
`git stash list`, so nothing is lost.

## Fixup + autosquash

Use for every old commit whose changes all land in a single target commit. The commits are
already on the branch, so there is no need to create `fixup!` commits: write the whole rebase
todo list from the plan and hand it to git without an editor.

1. Write one message file per new commit (`<msgdir>/N1.txt`, ...) and a todo file. For the
   plan `N1 ← A, F1` and `N2 ← B`:

   ```text
   pick  <A> VP-1 First unit
   fixup <F1> VP-1 Fix in first unit
   exec  git commit --amend --quiet --no-verify -F <msgdir>/N1.txt
   pick  <B> VP-1 Second unit
   exec  git commit --amend --quiet --no-verify -F <msgdir>/N2.txt
   ```

   Order the `pick` lines in the plan's order of new commits; each `fixup` goes right under its
   target. Old commits that the plan drops are simply left out (only when their effect is undone
   later on the branch; otherwise the final tree changes).

2. Run it:

   ```bash
   GIT_SEQUENCE_EDITOR="cp <todo-file>" git rebase -i <base>
   ```

3. Conflicts happen when a fix moves above a commit it depends on. Resolve them toward the
   content the file must have at that point (the final content minus what later new commits
   add), then `git rebase --continue`. If a segment keeps conflicting, `git rebase --abort` and
   rebuild that segment instead.

## Rebuilding a segment from the final tree

Use for mid-branch redesigns and for history that cannot be reordered without repeated
conflicts. The end state is fixed: the tree of the backup.

```bash
git switch -c tmp/fold-final backup/<branch>-pre-fold   # final tree reference
git switch <branch>
git reset --hard <last commit kept before the segment>
```

For each new commit of the segment, in order:

1. Write each file to the state it has at that point. Files touched by only this commit are
   simply `git checkout tmp/fold-final -- <path>`. Files touched by several new commits need an
   intermediate version: start from the final content and remove what later commits introduce.
2. `git add` the paths, then `git commit -F <msgdir>/N.txt --author="<name> <email>"`.

After the last commit, `git diff tmp/fold-final HEAD` must print nothing (or exactly the
differences the user approved). Delete `tmp/fold-final` at the end.

## Splitting a mixed commit

During the rebase, mark the commit `edit`, then:

```bash
git reset HEAD^
git add -p <paths>   # not interactive here: stage with `git apply --cached <hunk.patch>`
git commit ...       # first part
git add -A && git commit ...   # rest
git rebase --continue
```

Write each hunk to a patch file from `git diff` output and apply it with
`git apply --cached`; this keeps the split scriptable.

## Authorship

- A `fixup` keeps the target commit's author, which is what the plan wants.
- When the fix's author differs from the target's author, add
  `Co-authored-by: <fix author> <email>` to the target's message.
- A rebuilt commit takes `--author` of whoever wrote most of its lines (from the analysis
  `author` of the old commits it comes from), plus `Co-authored-by` for the others.
- Keep existing trailers. Add the session's own attribution trailer only to commits whose content
  you changed.

## Dependent (stacked) branches

When another local branch sits on top of the rewritten one (the analysis lists it in
`dependent_branches`), move it after the rewrite:

```bash
git rebase --onto <branch> backup/<branch>-pre-fold <dependent>
```

Back up the dependent first (`backup/<dependent>-pre-fold`). Check that its tree only changed by
what the lower branch changed: `git diff backup/<dependent>-pre-fold <dependent>` should be empty
when the lower branch's final tree is unchanged.

## Per-commit verification

Run in a temporary worktree so the user's checkout stays usable, in the background:

```bash
git worktree add --detach ../.fold-verify <base>
for sha in $(git rev-list --reverse <base>..<branch>); do
  git -C ../.fold-verify checkout --quiet "$sha"
  (cd ../.fold-verify && <build> && <tests for modules this commit touches>) \
    || echo "FAIL $sha"
done
(cd ../.fold-verify && <full relevant suite>)   # at the tip only
git worktree remove ../.fold-verify
```

## Undo

```bash
git switch <branch> && git reset --hard backup/<branch>-pre-fold
```
