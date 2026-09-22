"""Fetch FFF league data from the public ESPN API.

Three calls (mMatchupScore, mTeam, mSettings), 1s apart, written verbatim to
data/raw-<season>.json. No transform. mSettings carries the regular-season
length (settings.scheduleSettings.matchupPeriodCount) that the other two views
do not. See SPEC.md §3 and §9 (L1).
"""
import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

LEAGUE_ID = "877873"
BASE_URL = ("https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/"
            "seasons/{season}/segments/0/leagues/{league}")
VIEWS = ("mMatchupScore", "mTeam", "mSettings")


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

    out = Path("data") / f"raw-{season}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(raw, indent=2) + "\n")
    print(f"Wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
