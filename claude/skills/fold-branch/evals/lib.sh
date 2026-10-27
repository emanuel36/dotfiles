# Shared helpers for the eval setup scripts. Sourced, not run.
set -eu
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1
T=1767225600
c() {  # c "<author name>" "<email>" "<message>": commit everything staged + tracked changes
  T=$((T + 3600))
  git add -A
  GIT_AUTHOR_NAME="$1" GIT_AUTHOR_EMAIL="$2" GIT_COMMITTER_NAME="$1" GIT_COMMITTER_EMAIL="$2" \
    GIT_AUTHOR_DATE="@$T +0000" GIT_COMMITTER_DATE="@$T +0000" git commit -q -m "$3"
}
me() { c "Emanuel Pereira" "emanuel.pereira@platformscience.com" "$1"; }
init_repo() {
  git init -q -b main "$1" && cd "$1"
  git config user.name "Emanuel Pereira"
  git config user.email "emanuel.pereira@platformscience.com"
  mkdir -p calc tests
  printf '# calc\n\nSmall arithmetic helpers.\n\nRun the tests with `python3 -m unittest`.\n' > README.md
  : > calc/__init__.py; : > tests/__init__.py
  me "PRJ-1 Add the project skeleton"
  cat > calc/ops.py <<'PY'
def add(a, b):
    return a + b


def subtract(a, b):
    return a - b


def divide(a, b):
    return a / b
PY
  cat > tests/test_ops.py <<'PY'
import unittest

from calc import ops


class OpsTest(unittest.TestCase):
    def test_add(self):
        self.assertEqual(ops.add(2, 3), 5)

    def test_subtract(self):
        self.assertEqual(ops.subtract(2, 3), -1)

    def test_divide(self):
        self.assertEqual(ops.divide(6, 3), 2)
PY
  me "PRJ-2 Add the add, subtract and divide operations"
}
