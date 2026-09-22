"""Render the FFF static site from templates/ and data/standings-<season>.json.

Reads data/standings-<season>.json (written by compute.py) and renders
templates/ to docs/ per SPEC.md §9 (L4): home.html -> docs/index.html,
playoffs.html -> docs/playoffs.html, graph.html -> docs/graph.html (L5),
plus static/ copied to docs/static/.
Pure: no network, re-runs offline. Output is deterministic (no timestamps)
so L7 can commit only when it changes.

Pages not rendered (SPEC.md §4 — render only what the data supports, do not
invent data):
- player1.html needs per-team roster data, not in standings.json.
- weeklyupdate.html / welcome.html POST to Flask routes that no longer exist.
- update.html / error.html were admin/Flask concerns and are dropped.
"""
import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

# (template, output file) — home is the site root: layout.html's navbar
# links to index.html (de-Flasked in L3).
PAGES = (
    ("home.html", "index.html"),
    ("playoffs.html", "playoffs.html"),
    ("graph.html", "graph.html"),
)


def main():
    parser = argparse.ArgumentParser(description="Render the FFF static site to docs/.")
    parser.add_argument("--season", type=int, default=datetime.now().year,
                        help="Season year to build (default: current year)")
    args = parser.parse_args()
    season = args.season

    standings_path = Path("data") / f"standings-{season}.json"
    if not standings_path.exists():
        print(f"ERROR: {standings_path} not found. "
              f"Run compute.py --season {season} first.", file=sys.stderr)
        sys.exit(1)
    data = json.loads(standings_path.read_text(encoding="utf-8"))

    env = Environment(loader=FileSystemLoader("templates"),
                      autoescape=select_autoescape())
    context = {
        "standings": data["standings"],
        "weeks": data["weeks"],
        "throughWeek": data["throughWeek"],
        "regularSeasonWeeks": data["regularSeasonWeeks"],
        "season": data["season"],
    }

    docs = Path("docs")
    docs.mkdir(parents=True, exist_ok=True)
    for template, out_name in PAGES:
        out = docs / out_name
        # active_page drives the sidebar's active nav state (L5).
        # encoding="utf-8": the locale default (cp1252 on Windows) would
        # corrupt non-ASCII text (owner names, dashes) in the HTML.
        out.write_text(env.get_template(template).render(active_page=out_name, **context) + "\n",
                       encoding="utf-8")
        print(f"Wrote {out}")

    shutil.copytree("static", docs / "static", dirs_exist_ok=True)
    print(f"Copied static/ to {docs / 'static'}")


if __name__ == "__main__":
    main()
