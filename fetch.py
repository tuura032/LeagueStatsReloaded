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

**Second artifact: --starters (added 2026-09-24).** The three views above
carry team totals only, no players. `--starters` adds a second, separate
pass over the mBoxscore view -- one request per matchup period, because
ESPN attaches rosters only to the period you ask for -- and writes
data/starters-<season>.json: every *started* player, week by week. That is a
trimmed subset of ESPN's response, not a transform: 0.5-0.9 MB comes back
per week and only the eight fields the site needs are kept, because the raw
bodies would be ~100 MB a season in a repo that commits its data.

It is deliberately NOT part of the default fetch. A full season is ~17
requests at one per second, past seasons never change, and the daily bot
has no reason to re-walk 2019 every morning. Run it once per new season and
weekly during the current one; by default it re-fetches only the weeks it
does not already have (plus the newest one, which may have been mid-week
when it was stored).
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

# The --starters pass. mBoxscore is asked for one matchup period at a time:
# the response only carries rosters for the scoringPeriodId in the query, and
# this league's matchup periods map 1:1 onto scoring periods (verified for
# every season 2019-2026 -- a playoff matchup's pointsByScoringPeriod keys
# match its matchupPeriodId).
BOXSCORE_VIEW = "mBoxscore"

# Fields kept per started player. Everything else in ESPN's ~0.8 MB weekly
# response (projections, per-stat breakdowns, ownership, bench, injury
# history) is dropped -- see the module docstring.
#   week      matchup period, 1-based
#   teamId    fantasy team that started them
#   slot      lineup slot they filled (compute.LINEUP_SLOT_LABELS)
#   playerId  ESPN player id, stable across seasons
#   name      full name as ESPN had it that week
#   pos       defaultPositionId: 1 QB, 2 RB, 3 WR, 4 TE, 5 K, 16 D/ST
#   proTeamId NFL team they were on that week
#   points    appliedStatTotal -- actual fantasy points, this league's rules
STARTER_FIELDS = ("week", "teamId", "slot", "playerId", "name", "pos",
                  "proTeamId", "points")

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


def starter_rows(payload, week):
    """The started lineups for one matchup period, trimmed to STARTER_FIELDS.

    Two roster blocks come back per team and they are not interchangeable:

    - rosterForMatchupPeriod is the nine players who actually started. Their
      points sum exactly to the team's totalPoints. But ESPN zeroes
      lineupSlotId in this block, so it cannot say *which* slot anyone filled.
    - rosterForCurrentScoringPeriod carries the real lineupSlotId -- and also
      the bench (slot 20) and IR (21), which is exactly what must not be
      counted.

    So: the starter list comes from the first block, and the slot is looked up
    from the second by playerId. Same request, same week, so the two agree.

    Unplayed weeks are skipped rather than stored as a row of zeroes: ESPN
    happily returns a future week's projected lineup with appliedStatTotal 0.
    """
    rows = []
    for matchup in payload.get("schedule") or []:
        if matchup.get("matchupPeriodId") != week:
            continue
        for key in ("home", "away"):
            side = matchup.get(key) or {}
            started = ((side.get("rosterForMatchupPeriod") or {})
                       .get("entries") or [])
            # A playoff bye has no opposing side, and an unplayed week scores
            # 0.0 for everyone -- neither is a lineup worth recording.
            if not started or not side.get("totalPoints"):
                continue
            slots = {e.get("playerId"): e.get("lineupSlotId")
                     for e in ((side.get("rosterForCurrentScoringPeriod") or {})
                               .get("entries") or [])}
            for entry in started:
                pool = entry.get("playerPoolEntry") or {}
                player = pool.get("player") or {}
                rows.append({
                    "week": week,
                    "teamId": side.get("teamId"),
                    "slot": slots.get(entry.get("playerId"),
                                      entry.get("lineupSlotId")),
                    "playerId": entry.get("playerId"),
                    "name": player.get("fullName"),
                    "pos": player.get("defaultPositionId"),
                    "proTeamId": player.get("proTeamId"),
                    "points": pool.get("appliedStatTotal"),
                })
    return rows


def dump_starters(season, rows):
    """Serialize a starters file with one player per line.

    json.dumps(indent=2) would spread each of ~1,700 rows a season over ten
    lines, which makes the committed diff for a single new week unreadable.
    One compact object per line keeps a week's worth of change to a week's
    worth of lines. Rows are sorted so a re-fetch of unchanged weeks produces
    a byte-identical file and the daily bot has nothing to commit.
    """
    rows = sorted(rows, key=lambda r: (r["week"], r["teamId"], r["playerId"]))
    weeks = sorted({r["week"] for r in rows})
    body = ",\n".join(
        "    " + json.dumps({f: r.get(f) for f in STARTER_FIELDS})
        for r in rows)
    return "\n".join([
        "{",
        f'  "season": {season},',
        f'  "weeks": {json.dumps(weeks)},',
        '  "starters": [',
        body,
        "  ]",
        "}",
        "",
    ])


def fetch_starters(season, refetch_all=False):
    """Walk mBoxscore week by week and write data/starters-<season>.json.

    Which weeks to ask for comes from the committed raw file's schedule, so
    this never guesses at a season's length or pokes at periods that do not
    exist. Weeks already on file are kept as they are, except the newest one
    -- it may have been stored mid-week with games still to play.
    """
    raw_path = Path("data") / f"raw-{season}.json"
    if not raw_path.exists():
        print(f"ERROR: {raw_path} not found. Run fetch.py --season {season} "
              f"first -- the schedule there is what says how many weeks to "
              f"ask for.", file=sys.stderr)
        sys.exit(1)
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    schedule = raw.get("mMatchupScore", {}).get("schedule") or []
    all_weeks = sorted({m.get("matchupPeriodId") for m in schedule
                        if m.get("matchupPeriodId")})

    out = Path("data") / f"starters-{season}.json"
    kept = []
    if out.exists() and not refetch_all:
        existing = json.loads(out.read_text(encoding="utf-8"))
        stored = existing.get("weeks") or []
        # Everything but the newest stored week is settled; re-ask for that
        # one in case it was captured with games still to come.
        settled = set(stored[:-1])
        kept = [r for r in existing.get("starters") or []
                if r.get("week") in settled]
        weeks = [w for w in all_weeks if w not in settled]
    else:
        weeks = all_weeks

    if not weeks:
        print(f"{out}: all {len(all_weeks)} weeks already on file, nothing to do.")
        return

    print(f"Fetching starters for {season}: {len(weeks)} week(s) "
          f"({weeks[0]}-{weeks[-1]}), one request each, 1s apart.")
    rows = list(kept)
    for i, week in enumerate(weeks):
        if i:
            time.sleep(1)
        url = (BASE_URL.format(season=season, league=LEAGUE_ID)
               + f"?view={BOXSCORE_VIEW}&scoringPeriodId={week}")
        try:
            resp = requests.get(url)
            resp.raise_for_status()
        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            print(f"ERROR: ESPN returned HTTP {status} for {season} week "
                  f"{week}.", file=sys.stderr)
            sys.exit(1)
        week_rows = starter_rows(resp.json(), week)
        rows.extend(week_rows)
        print(f"  week {week:>2}: {len(week_rows)} started players"
              f"{' (not played yet)' if not week_rows else ''}")
        if not week_rows:
            # Weeks are played in order, so the first empty one ends the
            # season's real data. Without this the daily bot would burn a
            # request on every remaining week of the year, every morning,
            # to be told the same thing each time.
            print(f"  stopping at week {week} -- the rest of the season "
                  f"has not been played.")
            break

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(dump_starters(season, rows), encoding="utf-8")
    stored_weeks = sorted({r["week"] for r in rows})
    print(f"Wrote {out} ({out.stat().st_size} bytes), "
          f"{len(rows)} starts across {len(stored_weeks)} week(s)")


def main():
    parser = argparse.ArgumentParser(description="Fetch FFF league data from ESPN.")
    parser.add_argument("--season", type=int, default=datetime.now().year,
                        help="Season year to fetch (default: current year)")
    parser.add_argument("--starters", action="store_true",
                        help="Fetch started lineups (mBoxscore, one request "
                             "per week) to data/starters-<season>.json "
                             "instead of the standings views")
    parser.add_argument("--refetch", action="store_true",
                        help="With --starters, re-fetch every week instead of "
                             "only the missing ones")
    args = parser.parse_args()
    season = args.season

    if args.starters:
        fetch_starters(season, refetch_all=args.refetch)
        return

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
