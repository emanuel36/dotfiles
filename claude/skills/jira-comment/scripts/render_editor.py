#!/usr/bin/env python3
"""Render the comment variants JSON into the editor page and print the page's path.

Usage:
    render_editor.py VARIANTS_JSON OUTPUT_HTML
"""

import json
import pathlib
import sys
from datetime import datetime, timezone

TEMPLATE = pathlib.Path(__file__).resolve().parent.parent / "assets" / "editor.html"
REQUIRED = ("key", "variants")
VARIANT_REQUIRED = ("name", "markdown")


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    data = json.loads(pathlib.Path(sys.argv[1]).read_text())
    missing = [key for key in REQUIRED if key not in data]
    if missing:
        sys.exit(f"Variants JSON is missing: {', '.join(missing)}")
    if not data["variants"]:
        sys.exit("Variants JSON has no variants")
    for index, variant in enumerate(data["variants"]):
        missing = [key for key in VARIANT_REQUIRED if key not in variant]
        if missing:
            sys.exit(f"Variant {index} is missing: {', '.join(missing)}")
    data.setdefault("generated_at", datetime.now(timezone.utc).isoformat(timespec="seconds"))

    # Keep "</script>" inside strings from closing the page's script tag.
    payload = json.dumps(data).replace("</", "<\\/")
    page = TEMPLATE.read_text().replace("/*__DATA__*/null", payload)
    output = pathlib.Path(sys.argv[2]).resolve()
    output.write_text(page)
    print(output)


if __name__ == "__main__":
    main()
