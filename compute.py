"""Compute FFF dual-point standings from a raw ESPN fetch.

Reads data/raw-<season>.json (written by fetch.py) and writes
data/standings-<season>.json per SPEC.md §1 and §5. Pure: no network,
re-runs offline against a committed raw file.

Scoring (SPEC.md §1): each regular-season week, every team can earn up to
2 points — 1 for winning its head-to-head matchup, 1 for finishing in the
top half of the league (strictly above the "score to beat", the 6th-lowest
of the 12 scores, per v1's getApiData.getScoresToBeat()). The regular-season
length is read from mSettings.settings.scheduleSettings.matchupPeriodCount,
never hardcoded; later weeks are the playoff bracket and contribute no dual
points.

Tie rules (SPEC.md §1 — assumptions, pending league confirmation):
- Exact H2H tie -> no point to either team.
- Exact tie at the top-half boundary -> no point to either, so the league
  awards 5 top-half points that week rather than 7.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

LEAGUE_ID = "877873"


def current_streak(h2h_seq):
    """Current H2H streak from a chronological list of 1 (won) / 0 (lost or
    tied) results, most recent last. "W3", "L2", or "-" if no games played.
    """
    if not h2h_seq:
        return "-"
    last = h2h_seq[-1]
    n = 0
    for r in reversed(h2h_seq):
        if r != last:
            break
        n += 1
    return f"{'W' if last else 'L'}{n}"


def score_to_beat(scores):
    """The week's score to beat: the 6th-lowest of the 12 scores.

    v1's getApiData.getScoresToBeat(): sort ascending, index [5] is the
    highest score that missed the top six.
    """
    return sorted(scores)[5]


def _played(matchup):
    """True if a schedule entry is a decided game with both sides scored.

    Unplayed games carry winner "UNDECIDED" and 0.0 scores; playoff byes
    carry no 'away' side at all.
    """
    if matchup.get("winner") == "UNDECIDED":
        return False
    home, away = matchup.get("home"), matchup.get("away")
    if not home or not away:
        return False
    return all(isinstance(side.get("totalPoints"), (int, float))
               for side in (home, away))


def compute_week(week, matchups):
    """Dual points for one regular-season week (SPEC.md §1).

    matchups: the week's played schedule entries. Returns the §5 week dict:
    week, scoreToBeat, games, teams.
    """
    games = []
    teams = {}
    for m in matchups:
        home, away = m["home"], m["away"]
        home_id, away_id = home["teamId"], away["teamId"]
        home_score, away_score = home["totalPoints"], away["totalPoints"]
        # H2H point: the higher score takes it.
        if home_score > away_score:
            winner = home_id
        elif away_score > home_score:
            winner = away_id
        else:
            # Exact H2H tie: no point to either team.
            winner = None
        games.append({
            "home": home_id, "away": away_id,
            "homeScore": round(home_score, 1), "awayScore": round(away_score, 1),
            "winner": winner,
        })
        for team_id, score, won in (
                (home_id, home_score, winner == home_id),
                (away_id, away_score, winner == away_id)):
            teams[team_id] = {"teamId": team_id, "score": score,
                              "h2h": 1 if won else 0, "topHalf": 0,
                              "weekPoints": 0}

    stb = score_to_beat([t["score"] for t in teams.values()])
    for t in teams.values():
        # Top-half point: strictly greater than the score to beat. An exact
        # tie at the boundary gives neither.
        t["topHalf"] = 1 if t["score"] > stb else 0
        t["weekPoints"] = t["h2h"] + t["topHalf"]

    return {
        "week": week,
        "scoreToBeat": round(stb, 1),
        "games": games,
        "teams": sorted(teams.values(), key=lambda t: t["teamId"]),
    }


def build_standings(raw, updated):
    """Raw fetch dict (mMatchupScore + mTeam + mSettings) -> §5 standings dict.

    Pure function of its inputs; `updated` is the UTC timestamp string the
    caller stamps on the run.
    """
    ms = raw["mMatchupScore"]
    teams_view = raw["mTeam"]
    week_count = raw["mSettings"]["settings"]["scheduleSettings"]["matchupPeriodCount"]

    members = {m["id"]: m for m in teams_view.get("members", [])}
    team_info = {}
    for t in teams_view["teams"]:
        owner = members.get(t.get("primaryOwner"), {})
        owner_name = " ".join(p for p in (owner.get("firstName"),
                                          owner.get("lastName")) if p) \
            or owner.get("displayName")
        team_info[t["id"]] = {"name": t.get("name"), "owner": owner_name}

    # Group by matchupPeriodId — never index the schedule by arithmetic
    # (SPEC.md §3: the playoffs do not have 6 entries per week).
    by_week = {}
    for m in ms.get("schedule", []):
        by_week.setdefault(m["matchupPeriodId"], []).append(m)

    # A week is complete when every team has a played game in it.
    # throughWeek is the last complete week, counting up from week 1, and
    # never extends past the regular season.
    weeks_out = []
    through_week = 0
    for week in range(1, week_count + 1):
        played = [m for m in by_week.get(week, []) if _played(m)]
        played_teams = {s["teamId"] for m in played for s in (m["home"], m["away"])}
        if len(played_teams) != len(team_info):
            break
        weeks_out.append(compute_week(week, played))
        through_week = week

    stats = {tid: {"h2hPoints": 0, "topHalfPoints": 0, "wins": 0, "losses": 0,
                   "ties": 0, "pointsFor": 0.0, "pointsAgainst": 0.0,
                   "scores": [], "h2h_seq": []}
             for tid in team_info}
    for w in weeks_out:
        for g in w["games"]:
            home, away = g["home"], g["away"]
            stats[home]["pointsFor"] += g["homeScore"]
            stats[away]["pointsFor"] += g["awayScore"]
            stats[home]["pointsAgainst"] += g["awayScore"]
            stats[away]["pointsAgainst"] += g["homeScore"]
            if g["winner"] == home:
                stats[home]["wins"] += 1
                stats[away]["losses"] += 1
            elif g["winner"] == away:
                stats[away]["wins"] += 1
                stats[home]["losses"] += 1
            else:
                stats[home]["ties"] += 1
                stats[away]["ties"] += 1
        for t in w["teams"]:
            s = stats[t["teamId"]]
            s["h2hPoints"] += t["h2h"]
            s["topHalfPoints"] += t["topHalf"]
            s["scores"].append(t["score"])
            s["h2h_seq"].append(t["h2h"])

    standings = []
    for tid, s in stats.items():
        info = team_info[tid]
        points_for = round(s["pointsFor"], 1)
        last3 = s["scores"][-3:]
        standings.append({
            "teamId": tid,
            "name": info["name"],
            "owner": info["owner"],
            "points": s["h2hPoints"] + s["topHalfPoints"],
            "h2hPoints": s["h2hPoints"],
            "topHalfPoints": s["topHalfPoints"],
            "record": f'{s["wins"]}-{s["losses"]}'
                      + (f'-{s["ties"]}' if s["ties"] else ""),
            "pointsFor": points_for,
            "pointsAgainst": round(s["pointsAgainst"], 1),
            "averageScore": round(points_for / through_week, 1) if through_week else 0.0,
            "avgLast3": round(sum(last3) / len(last3), 1) if last3 else 0.0,
            # Luck index: H2H points earned minus top-half points earned.
            # Positive means winning matchups more often than raw scoring
            # alone would justify (a favorable schedule); negative means
            # scoring top-half more often than winning (a tough schedule).
            "luckIndex": s["h2hPoints"] - s["topHalfPoints"],
            "streak": current_streak(s["h2h_seq"]),
        })
    standings.sort(key=lambda r: (-r["points"], -r["pointsFor"]))
    ranked = [{"rank": i, **row} for i, row in enumerate(standings, 1)]

    return {
        "season": ms["seasonId"],
        "league": str(ms.get("id", LEAGUE_ID)),
        "updated": updated,
        "regularSeasonWeeks": week_count,
        "throughWeek": through_week,
        "weeks": weeks_out,
        "standings": ranked,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Compute FFF dual-point standings from raw ESPN data.")
    parser.add_argument("--season", type=int, default=datetime.now().year,
                        help="Season year to compute (default: current year)")
    args = parser.parse_args()
    season = args.season

    raw_path = Path("data") / f"raw-{season}.json"
    if not raw_path.exists():
        print(f"ERROR: {raw_path} not found. Run fetch.py --season {season} first.",
              file=sys.stderr)
        sys.exit(1)
    raw = json.loads(raw_path.read_text())

    updated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    standings = build_standings(raw, updated)

    out = Path("data") / f"standings-{season}.json"
    out.write_text(json.dumps(standings, indent=2) + "\n")
    print(f"Wrote {out} ({out.stat().st_size} bytes), "
          f"through week {standings['throughWeek']} of {standings['regularSeasonWeeks']}")


if __name__ == "__main__":
    main()