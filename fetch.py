"""Fetch FFF league data from the public ESPN API.

Three calls (mMatchupScore, mTeam, mSettings), 1s apart, written to
data/raw-<season>.json. mSettings carries the regular-season length
(settings.scheduleSettings.matchupPeriodCount) that the other two views do
not. See SPEC.md §3 and §9 (L1).

**One deliberate exception to "verbatim" (added 2026-09-23): surnames.**
This repo is public -- GitHub Pages on the free tier requires it -- so
everything written here is world-readable. ESPN's member records carry full
legal names, and the league would rather not publish them. redact_members()
truncates each lastName to SURNAME_KEEP characters before the file is
written, which is enough for the site to tell two owners with the same first
name apart and not enough to identify anyone. notificationSettings is
dropped as pure noise.

Nothing downstream needs the full surname: compute.py builds owner identity
from firstName plus this prefix, and the site displays first names alone
unless two collide. See SPEC.md §3.
"""
import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

LEAGUE_ID = "877873"
BASE_URL = ("https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/"
            "seasons/{season}/segments/0/leagues/{league}")
VIEWS = ("mMatchupScore", "mTeam", "mSettings")

# How much of a surname to keep. Two characters already separates this
# league's Senger/Sharp; three leaves headroom for a future pair that
# shares the first two, without being enough to identify anyone.
SURNAME_KEEP = 3


def redact_members(raw):
    """Strip surnames and notification noise out of ESPN's member records.

    Also rewrites surnames out of *team* names: several owners here named
    their team after themselves ("Team Hildebrandt", "Team Sugar", "Team
    Huisken"), which would have leaked the very thing the member redaction
    removes. The surname is swapped for the owner's first name rather than
    truncated, because "Team Ethan" reads like a team name and "Team Hil."
    reads like a bug.

    Mutates and returns `raw`. Safe to run twice: the surname is gone from
    the member records after the first pass, so the team-name substitution
    simply finds nothing to do.
    """
    for view in (raw or {}).values():
        if not isinstance(view, dict):
            continue
        members = view.get("members") or []
        # Full surnames are still intact at this point -- do the team-name
        # substitution before truncating them.
        by_id = {m.get("id"): m for m in members}
        for team in view.get("teams") or []:
            member = by_id.get(team.get("primaryOwner"))
            name, first, last = team.get("name"), None, None
            if member:
                first, last = member.get("firstName"), member.get("lastName")
            if not (name and first and last and len(last) > SURNAME_KEEP):
                continue
            pattern = re.compile(re.escape(last), re.IGNORECASE)
            if pattern.search(name):
                team["name"] = pattern.sub(first, name)

        for member in members:
            last = member.get("lastName")
            if isinstance(last, str) and len(last) > SURNAME_KEEP:
                short = last[:SURNAME_KEEP]
                # displayName is usually an opaque handle ("senge023"), but
                # some members have set it to their full name outright, so
                # it needs the same truncation.
                display = member.get("displayName")
                if isinstance(display, str):
                    member["displayName"] = re.sub(
                        re.escape(last), short, display, flags=re.IGNORECASE)
                member["lastName"] = short
            member.pop("notificationSettings", None)
    return raw


def main():
    parser = argparse.ArgumentParser(description="Fetch FFF league data from ESPN.")
    parser.add_argument("--season", type=int, default=datetime.now().year,
                        help="Season year to fetch (default: current year)")
    args = parser.parse_args()
    season = args.season

    raw = {}
    try:
        for i, view in enumerate(VIEWS):
            if i:
                time.sleep(1)
            url = BASE_URL.format(season=season, league=LEAGUE_ID) + f"?view={view}"
            resp = requests.get(url)
            resp.raise_for_status()
            raw[view] = resp.json()
    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else "unknown"
        print(f"ERROR: ESPN returned HTTP {status} for season {season} "
              f"(league {LEAGUE_ID}). That season may not exist.", file=sys.stderr)
        sys.exit(1)

    redact_members(raw)

    out = Path("data") / f"raw-{season}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(raw, indent=2) + "\n")
    print(f"Wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
