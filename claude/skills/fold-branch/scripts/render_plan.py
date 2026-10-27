#!/usr/bin/env python3
"""Render a fold plan JSON into the review page and print the page's path.

Usage:
    render_plan.py PLAN_JSON OUTPUT_HTML
"""

import json
import pathlib
import sys
from datetime import datetime, timezone

TEMPLATE = pathlib.Path(__file__).resolve().parent.parent / "assets" / "plan.html"
REQUIRED = ("repo", "branch", "base")


def check_variant(name, variant):
    """Exits when a variant's old commits point to new commits it does not define."""
    for key in ("before", "after"):
        if key not in variant:
            sys.exit(f"{name} is missing '{key}'")
    ids = {commit["id"] for commit in variant["after"]}
    for commit in variant["before"]:
        unknown = [target for target in commit.get("to", []) if target not in ids]
        if unknown:
            sys.exit(f"{name}: {commit['sha']} points to unknown new commits: {unknown}")


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    plan = json.loads(pathlib.Path(sys.argv[1]).read_text())
    missing = [key for key in REQUIRED if key not in plan]
    if missing:
        sys.exit(f"Plan is missing: {', '.join(missing)}")
    if "variants" in plan:
        for variant in plan["variants"]:
            check_variant(f"Variant '{variant.get('name')}'", variant)
    else:
        check_variant("Plan", plan)
    plan.setdefault("generated_at", datetime.now(timezone.utc).isoformat(timespec="seconds"))

    # Keep "</script>" inside strings from closing the page's script tag.
    data = json.dumps(plan).replace("</", "<\\/")
    page = TEMPLATE.read_text().replace("/*__PLAN__*/null", data)
    output = pathlib.Path(sys.argv[2]).resolve()
    output.write_text(page)
    print(output)


if __name__ == "__main__":
    main()
