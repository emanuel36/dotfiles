#!/usr/bin/env bash
# Builds ./repo with a published feature/PRJ-7-stats (pushed to ./origin.git) that has fix
# commits, and feature/PRJ-8-report stacked on top of it. Records every ref in ./refs-before.txt.
. "$(dirname "$0")/../lib.sh"
ROOT=$PWD
git init -q --bare "$ROOT/origin.git"
init_repo repo
git remote add origin "$ROOT/origin.git"
git push -q origin main
git switch -q -c feature/PRJ-7-stats

cat > calc/stats.py <<'PY'
def mean(values):
    return sum(values) / len(values)


def median(values):
    ordered = sorted(values)
    return ordered[len(ordered) // 2]
PY
cat > tests/test_stats.py <<'PY'
import unittest

from calc import stats


class StatsTest(unittest.TestCase):
    def test_mean(self):
        self.assertEqual(stats.mean([1, 2, 3]), 2)

    def test_median_odd(self):
        self.assertEqual(stats.median([3, 1, 2]), 2)
PY
me "PRJ-7 Add mean and median"

cat >> calc/stats.py <<'PY'


def spread(values):
    return max(values) - min(values)
PY
cat >> tests/test_stats.py <<'PY'

    def test_spread(self):
        self.assertEqual(stats.spread([4, 1, 3]), 3)
PY
me "PRJ-7 Add spread"

python3 - <<'PY'
p = "calc/stats.py"; s = open(p).read()
s = s.replace("""    ordered = sorted(values)
    return ordered[len(ordered) // 2]""", """    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2""")
open(p, "w").write(s)
PY
me "PRJ-7 fix median for even lists"

sed -i 's/def spread(values):/def spread(values):\n    if not values:\n        return 0/' calc/stats.py
me "PRJ-7 handle empty list in spread (review)"
git push -q -u origin feature/PRJ-7-stats

git switch -q -c feature/PRJ-8-report
cat > calc/report.py <<'PY'
from calc import stats


def report(values):
    return f"mean={stats.mean(values)} spread={stats.spread(values)}"
PY
me "PRJ-8 Add a stats report"
git switch -q feature/PRJ-7-stats

git for-each-ref --format='%(refname) %(objectname)' > "$ROOT/refs-before.txt"
