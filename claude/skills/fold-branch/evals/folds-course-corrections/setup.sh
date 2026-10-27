#!/usr/bin/env bash
# Builds ./repo: main plus feature/PRJ-7-stats, an 11-commit branch full of course corrections.
. "$(dirname "$0")/../lib.sh"
init_repo repo
git switch -q -c feature/PRJ-7-stats

cat > calc/stats.py <<'PY'
def _sum(values):
    return sum(values)


def mean(values):
    return _sum(values) / len(values)


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

cat > calc/cli.py <<'PY'
import sys

from calc import stats


def main(argv):
    values = [float(arg) for arg in argv]
    return f"mean={stats.mean(values)} median={stats.median(values)}"


if __name__ == "__main__":
    print(main(sys.argv[1:]))
PY
cat > tests/test_cli.py <<'PY'
import unittest

from calc import cli


class CliTest(unittest.TestCase):
    def test_main(self):
        self.assertEqual(cli.main(["1", "2", "3"]), "mean=2.0 median=2.0")
PY
me "PRJ-7 Add a CLI that prints the stats"

python3 - <<'PY'
p = "calc/stats.py"; s = open(p).read()
s = s.replace("""    ordered = sorted(values)
    return ordered[len(ordered) // 2]""", """    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2""")
open(p, "w").write(s)
p = "tests/test_stats.py"; s = open(p).read()
s += """
    def test_median_even(self):
        self.assertEqual(stats.median([4, 1, 3, 2]), 2.5)
"""
open(p, "w").write(s)
PY
me "PRJ-7 fix median for even lists"

sed -i 's/^    values = \[float(arg) for arg in argv\]$/&\n    print("DEBUG", values)/' calc/cli.py
me "PRJ-7 debug"

cat >> calc/stats.py <<'PY'


def mode(values):
    return max(set(values), key=values.count)
PY
cat >> tests/test_stats.py <<'PY'

    def test_mode(self):
        self.assertEqual(stats.mode([1, 2, 2, 3]), 2)
PY
me "PRJ-7 Add mode"

sed -i 's/_sum/_total/g' calc/stats.py
me "PRJ-7 rename sum helper"

sed -i '/print("DEBUG", values)/d' calc/cli.py
me "PRJ-7 remove debug print"

cat >> calc/stats.py <<'PY'


def variance(values):
    m = mean(values)
    return _total([(v - m) ** 2 for v in values]) / len(values)
PY
me "PRJ-7 Add variance"

python3 - <<'PY'
p = "calc/stats.py"; s = open(p).read()
s = s[:s.index("\n\n\ndef variance")] + "\n"
open(p, "w").write(s)
PY
me "PRJ-7 Revert variance, not needed"

sed -i 's/\[float(arg) for arg in argv\]/[float(argument) for argument in argv]/' calc/cli.py
me "PRJ-7 lint"

python3 - <<'PY'
p = "calc/stats.py"; s = open(p).read()
s = s.replace("""def mean(values):
    return""", """def mean(values):
    if not values:
        raise ValueError("mean of an empty list")
    return""")
open(p, "w").write(s)
p = "tests/test_stats.py"; s = open(p).read()
s = s.replace("""    def test_median_odd""", """    def test_mean_empty(self):
        with self.assertRaises(ValueError):
            stats.mean([])

    def test_median_odd""")
open(p, "w").write(s)
PY
me "PRJ-7 address review: reject an empty list in mean"
