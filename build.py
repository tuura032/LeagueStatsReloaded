"""Render the FFF static site from templates/ and data/standings-<season>.json.

Reads data/standings-<season>.json (written by compute.py) and renders
templates/ to docs/ per SPEC.md §9 (L4): home.html -> index.html,
playoffs.html -> playoffs.html, graph.html -> graph.html (L5), plus
static/ copied alongside.
Pure: no network, re-runs offline. Output is deterministic (no timestamps)
so L7 can commit only when it changes.

Multi-season (L9): with no --season, every season that has a standings
file is built. The newest season is the site root (docs/); each older
season goes to docs/<season>/. Newest-season-is-root (rather than "the
current calendar year") keeps the root live through the off-season, when
the new year's season does not exist on ESPN yet. layout.html's season
picker links the seasons with relative URLs via the "base" context var;
static/ is copied into every output directory so the templates' relative
asset paths resolve in the subdirectories too.

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

import compute

# (template, output file) — home is the site root: layout.html's navbar
# links to index.html (de-Flasked in L3).
PAGES = (
    ("home.html", "index.html"),
    ("playoffs.html", "playoffs.html"),
    ("graph.html", "graph.html"),
    ("rivalries.html", "rivalries.html"),
    ("careers.html", "careers.html"),
)


def main():
    parser = argparse.ArgumentParser(description="Render the FFF static site to docs/.")
    parser.add_argument("--season", type=int, default=None,
                        help="Build only this season (default: every season with a standings file)")
    args = parser.parse_args()

    data_dir = Path("data")
    all_seasons = sorted(
        (int(p.stem.split("-")[1]) for p in data_dir.glob("standings-*.json")),
        reverse=True)
    if not all_seasons:
        print("ERROR: no data/standings-<season>.json found. Run compute.py first.",
              file=sys.stderr)
        sys.exit(1)

    if args.season is not None:
        if args.season not in all_seasons:
            print(f"ERROR: data/standings-{args.season}.json not found. "
                  f"Run compute.py --season {args.season} first.", file=sys.stderr)
            sys.exit(1)
        seasons = [args.season]
    else:
        seasons = all_seasons

    # Newest season is the site root; older seasons go to docs/<season>/.
    root_season = all_seasons[0]
    current_season = datetime.now().year

    # Rivalries are all-time, so they're computed once from every season on
    # file (not just the season(s) being (re)built) and reused on every
    # rendered page, regardless of --season.
    all_standings = [json.loads((data_dir / f"standings-{s}.json").read_text(encoding="utf-8"))
                      for s in all_seasons]
    rivalry_owners, rivalry_matrix = compute.build_rivalries(all_standings)
    careers = compute.build_career_stats(all_standings)

    env = Environment(loader=FileSystemLoader("templates"),
                      autoescape=select_autoescape())
    docs = Path("docs")
    for season in seasons:
        data = json.loads((data_dir / f"standings-{season}.json").read_text(encoding="utf-8"))
        out_dir = docs if season == root_season else docs / str(season)
        out_dir.mkdir(parents=True, exist_ok=True)
        context = {
            "standings": data["standings"],
            "weeks": data["weeks"],
            "throughWeek": data["throughWeek"],
            "regularSeasonWeeks": data["regularSeasonWeeks"],
            "season": data["season"],
            # L9 — season picker: every season, newest first; "base" is the
            # relative prefix that makes the picker's links resolve from a
            # subdirectory ("../" for past seasons, "" at the root).
            "seasons": all_seasons,
            "current_season": current_season,
            "base": "" if season == root_season else "../",
            "rivalry_owners": rivalry_owners,
            "rivalry_matrix": rivalry_matrix,
            "careers": careers,
        }
        for template, out_name in PAGES:
            out = out_dir / out_name
            # active_page drives the sidebar's active nav state (L5).
            # encoding="utf-8": the locale default (cp1252 on Windows) would
            # corrupt non-ASCII text (owner names, dashes) in the HTML.
            out.write_text(env.get_template(template).render(active_page=out_name, **context) + "\n",
                           encoding="utf-8")
            print(f"Wrote {out}")
        # The templates reference static/ relatively, so every output
        # directory needs its own copy. rmtree first: dirs_exist_ok=True
        # merges instead of mirroring, so a file removed from static/
        # (e.g. dashboard.css, retired for the Tailwind rewrite) would
        # otherwise linger as a stale orphan in docs/ forever.
        static_out = out_dir / "static"
        if static_out.exists():
            shutil.rmtree(static_out)
        shutil.copytree("static", static_out)
        print(f"Copied static/ to {static_out}")


if __name__ == "__main__":
    main()
