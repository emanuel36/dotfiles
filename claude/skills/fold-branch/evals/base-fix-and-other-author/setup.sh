#!/usr/bin/env bash
# Builds ./repo with feature/PRJ-9-percent: commits by Ana Souza, the user's fixes to her code,
# and a fix to code that existed before the branch. Leaves the worktree dirty on purpose.
. "$(dirname "$0")/../lib.sh"
ana() { c "Ana Souza" "ana.souza@example.com" "$1"; }
init_repo repo
git switch -q -c feature/PRJ-9-percent

cat > calc/percent.py <<'PY'
def percent_of(part, whole):
    return part / whole * 100


def percent_change(old, new):
    return (new - old) / old * 100
PY
cat > tests/test_percent.py <<'PY'
import unittest

from calc import percent


class PercentTest(unittest.TestCase):
    def test_percent_of(self):
        self.assertEqual(percent.percent_of(1, 4), 25)

    def test_percent_change(self):
        self.assertEqual(percent.percent_change(50, 75), 50)
PY
ana "PRJ-9 Add the percentage helpers"

cat > calc/fmt.py <<'PY'
def format_percent(value):
    return f"{value:.1f}%"
PY
cat > tests/test_fmt.py <<'PY'
import unittest

from calc import fmt


class FmtTest(unittest.TestCase):
    def test_format_percent(self):
        self.assertEqual(fmt.format_percent(12.345), "12.3%")
PY
ana "PRJ-9 Format percentages for display"

sed -i 's|    return (new - old) / old \* 100|    return round((new - old) / old * 100, 2)|' calc/percent.py
cat >> tests/test_percent.py <<'PY'

    def test_percent_change_rounds(self):
        self.assertEqual(percent.percent_change(3, 4), 33.33)
PY
me "PRJ-9 fix percent_change rounding"

python3 - <<'PY'
p = "calc/ops.py"; s = open(p).read()
s = s.replace("""def divide(a, b):
    return a / b""", """def divide(a, b):
    if b == 0:
        raise ZeroDivisionError("divide by zero")
    return a / b""")
open(p, "w").write(s)
p = "tests/test_ops.py"; s = open(p).read()
s += """
    def test_divide_by_zero(self):
        with self.assertRaises(ZeroDivisionError):
            ops.divide(1, 0)
"""
open(p, "w").write(s)
PY
me "PRJ-9 guard divide by zero"

sed -i 's|    return f"{value:.1f}%"|    return f"{value:+.1f}%"|' calc/fmt.py
sed -i 's|"12.3%"|"+12.3%"|' tests/test_fmt.py
ana "PRJ-9 fix: show the sign of percentages"

# Uncommitted work the rewrite must not lose.
printf '\nSee calc/percent.py for percentages.\n' >> README.md
printf 'todo: percent_of with a zero whole\n' > notes.txt
