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
import hashlib
import json
import os
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


def phrase_hash():
    """SHA-256 of the league passphrase, or "" when none is configured.

    The phrase itself is never committed: CI puts it in the environment from
    a GitHub Secret (LEAGUE_PHRASE) and only this digest is baked into the
    page. A local build with no secret set produces no hash, which disables
    the gate entirely -- so `python build.py` on a laptop still renders a
    browsable site.

    Be clear about what this is: the page content ships in the HTML either
    way, so the gate keeps out search engines and casual visitors, not anyone
    willing to open devtools. It is a doorbell, not a lock. The reason that
    is acceptable here is that there is nothing sensitive behind it any
    more -- surnames are stripped from the data at fetch time.
    """
    phrase = os.environ.get("LEAGUE_PHRASE", "").strip()
    if not phrase:
        return ""
    return hashlib.sha256(phrase.encode("utf-8")).hexdigest()


def ordinal(n):
    """1 -> '1st', 2 -> '2nd', 12 -> '12th', 23 -> '23rd'.

    Used for final placements. 11/12/13 are the exceptions that a naive
    last-digit lookup gets wrong ("11st"), so they are special-cased.
    """
    if n is None:
        return ""
    n = int(n)
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


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

    # Prize amounts (the league pot) are a league setting, not ESPN data, so
    # they live in data/prizes.json instead of being hardcoded in the
    # template. The owner edits that file when the pot changes; build.py just
    # reads it. Read once here (not per-season) since the pot is a single
    # league-wide setting shared by every rendered season.
    prizes_path = data_dir / "prizes.json"
    if not prizes_path.exists():
        print("ERROR: data/prizes.json not found.", file=sys.stderr)
        sys.exit(1)
    prize_config = json.loads(prizes_path.read_text(encoding="utf-8"))
    # All-time winnings, computed once over every season on file. Only
    # fully-decided seasons contribute, so an in-progress year doesn't pay
    # out money nobody has won yet.
    career_money = compute.career_payouts(all_standings, prize_config)
    # Only seasons that actually paid out, newest first -- the per-year
    # columns on the all-time winnings table.
    money_seasons = sorted({year for row in career_money for year in row["bySeason"]},
                           reverse=True)

    # Display names: the league refers to each other by first name, and
    # team names change yearly while people don't. Built from every owner
    # across every season at once so a name reads the same on every page.
    all_owners = {row["owner"]
                  for season_data in all_standings
                  for row in season_data["standings"]}
    short = compute.short_names(all_owners)

    env = Environment(loader=FileSystemLoader("templates"),
                      autoescape=select_autoescape())
    env.filters["ordinal"] = ordinal
    gate_hash = phrase_hash()
    if gate_hash:
        print("Passphrase gate: enabled (hash baked in, phrase not stored)")
    else:
        print("Passphrase gate: disabled (set LEAGUE_PHRASE to enable)")
    # `short` on a full owner name; `names` on a list of them, joined as
    # "A", "A & B" or "A, B & C".
    env.filters["short"] = lambda owner: short.get(owner, owner)
    env.filters["names"] = lambda owners: compute.join_names(
        [short.get(o, o) for o in owners])
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
            # The newest season that has data, which is what lives at the
            # site root. Distinct from current_season (the calendar year):
            # in the off-season the new year exists but has no data yet.
            "root_season": root_season,
            "base": "" if season == root_season else "../",
            "rivalry_owners": rivalry_owners,
            "rivalry_matrix": rivalry_matrix,
            "careers": careers,
            # Prize lines for this season, each already resolved to a
            # winner, plus the same money re-cut as a ranked payout table.
            # Both come from one resolver in compute.py -- when the macro
            # owned that logic the two views could silently disagree.
            "prizes": compute.resolve_prizes(
                data, compute.prizes_for_season(prize_config, season)),
            "payouts": compute.season_payouts(
                data, compute.prizes_for_season(prize_config, season)),
            "career_money": career_money,
            "money_seasons": money_seasons,
            "entryFee": data.get("entryFee"),
            "phrase_hash": gate_hash,
            # How many teams make the playoffs, per the league's own ESPN
            # settings. home.html used to assume half the field, which is
            # right for this league only by coincidence.
            "playoffTeamCount": data.get("playoffTeamCount"),
            # Championship results (None until a season's final is decided),
            # plus a teamId -> owner lookup so the prize table can name a
            # champion without re-scanning standings in the template.
            "playoffs": data.get("playoffs"),
            "owner_by_team": {s["teamId"]: s["owner"] for s in data["standings"]},
            # Whether this season has finished and ESPN has published final
            # placements. Drives the "Finish" column, which is meaningless
            # (and all em-dashes) mid-season.
            "has_final_ranks": any(s.get("finalRank")
                                   for s in data["standings"]),
            # Final placement order, best first -- the answer to "how did
            # this season actually end", which for a past season matters at
            # least as much as the regular-season table.
            # Advanced stats, records and awards for the Stats page.
            # Derived at render time from the week data already on disk --
            # no extra ESPN call, nothing new stored in the JSON artifact.
            "season_stats": compute.build_season_stats(data),
            "final_standings": sorted(
                (s for s in data["standings"] if s.get("finalRank")),
                key=lambda s: s["finalRank"]),
            "updated": data.get("updated"),
            "leagueName": data.get("leagueName"),
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
