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
    """The week's score to beat: the highest score that missed the top half.

    v1's getApiData.getScoresToBeat() hardcoded index [5] -- correct for a
    12-team league and silently wrong for any other size, which made the
    whole scoring rule (SPEC.md §1, the reason this project exists) compute
    the wrong answer for a league that isn't 12 teams. Derived from the
    field size instead: index [n//2 - 1] is the highest score that missed
    the top half, which is [5] when n == 12.

    For an odd field the top half rounds up (11 teams -> 6 earn the point).
    """
    n = len(scores)
    if n < 2:
        raise ValueError(f"score_to_beat needs at least 2 scores, got {n}")
    return sorted(scores)[n // 2 - 1]


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


def build_playoffs(schedule, week_count):
    """Winners-bracket results for a season, or None if no champion yet.

    The dual-point scoring stops at week_count (SPEC.md §1) and everything
    after it used to be discarded outright -- which meant the site could not
    say who actually won the league, and Career Stats credited the "title"
    to whoever finished the regular season at #1. In 2025 that was Casey
    Pirsig, who then lost the final to Davíd Huisken by 45 points.

    ESPN tags each schedule entry with playoffTierType; WINNERS_BRACKET is
    the championship bracket (LOSERS_/WINNERS_CONSOLATION_LADDER are the
    also-ran ladders and are ignored). The final is the single bracket game
    in the highest bracket week.

    The final week is taken from every bracket entry, not just the played
    ones: mid-playoffs the later rounds exist but are UNDECIDED, and picking
    the highest *played* week would crown a semifinal winner as champion.
    Returns None until the final itself is decided.
    """
    bracket = [m for m in schedule
               if m.get("playoffTierType") == "WINNERS_BRACKET"
               and m["matchupPeriodId"] > week_count]
    if not bracket:
        return None

    final_week = max(m["matchupPeriodId"] for m in bracket)
    finals = [m for m in bracket if m["matchupPeriodId"] == final_week]
    # Exactly one game decides the title. Anything else is a bracket shape
    # this function does not understand, and guessing a champion is worse
    # than reporting none.
    if len(finals) != 1 or not _played(finals[0]):
        return None

    final = finals[0]
    home, away = final["home"], final["away"]
    if home["totalPoints"] > away["totalPoints"]:
        champion, runner_up = home["teamId"], away["teamId"]
    elif away["totalPoints"] > home["totalPoints"]:
        champion, runner_up = away["teamId"], home["teamId"]
    else:
        # A tied final has no winner to report; ESPN breaks these by rule,
        # not by score, and that rule is not in this payload.
        return None

    games = []
    # Sort by week, then ESPN's entry id to keep output stable across runs.
    # id is always present in real payloads; default 0 so the function does
    # not depend on a field it never otherwise reads.
    for m in sorted(bracket, key=lambda g: (g["matchupPeriodId"], g.get("id", 0))):
        h, a = m.get("home"), m.get("away")
        games.append({
            "week": m["matchupPeriodId"],
            # A bye carries no 'away' side at all (2025 week 15 has 7
            # entries for this reason -- the SPEC.md §3 trap).
            "home": h["teamId"] if h else None,
            "away": a["teamId"] if a else None,
            "homeScore": round(h["totalPoints"], 1) if h else None,
            "awayScore": round(a["totalPoints"], 1) if a else None,
            "bye": a is None or h is None,
        })

    # Points scored in the championship bracket, per team. Byes contribute
    # the bye week's score; a team that lost in round 1 simply has fewer
    # games in the sum, which is what "most points in the playoffs" means.
    playoff_points = {}
    for g in games:
        for team_id, score in ((g["home"], g["homeScore"]),
                               (g["away"], g["awayScore"])):
            if team_id is not None and score is not None:
                playoff_points[team_id] = round(
                    playoff_points.get(team_id, 0.0) + score, 1)
    most_pf = (max(playoff_points, key=lambda t: playoff_points[t])
               if playoff_points else None)

    return {
        "champion": champion,
        "runnerUp": runner_up,
        "mostPointsFor": most_pf,
        "pointsFor": playoff_points,
        "finalWeek": final_week,
        "championScore": round(max(home["totalPoints"], away["totalPoints"]), 1),
        "runnerUpScore": round(min(home["totalPoints"], away["totalPoints"]), 1),
        "games": games,
    }


def build_standings(raw, updated):
    """Raw fetch dict (mMatchupScore + mTeam + mSettings) -> §5 standings dict.

    Pure function of its inputs; `updated` is the UTC timestamp string the
    caller stamps on the run.
    """
    ms = raw["mMatchupScore"]
    teams_view = raw["mTeam"]
    schedule_settings = raw["mSettings"]["settings"]["scheduleSettings"]
    week_count = schedule_settings["matchupPeriodCount"]
    # How many teams make the playoffs is a league setting, not a constant.
    # home.html used to draw its playoff line at len(standings) // 2, which
    # is 6 here only because this league is 12 teams with a 6-team playoff
    # -- correct by coincidence, wrong for any league that splits differently.
    playoff_team_count = schedule_settings.get("playoffTeamCount")

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
        "leagueName": raw["mSettings"]["settings"].get("name"),
        "updated": updated,
        "regularSeasonWeeks": week_count,
        "playoffTeamCount": playoff_team_count,
        "throughWeek": through_week,
        "weeks": weeks_out,
        "standings": ranked,
        # None until the season's championship game is decided.
        "playoffs": build_playoffs(ms.get("schedule", []), week_count),
    }


def build_rivalries(all_standings):
    """All-time head-to-head records between owners, across every given
    season's §5 standings dict (as many seasons as are passed in).

    Matches games by owner name rather than teamId, since a teamId's owner
    can change between seasons (and a team can be renamed) but the owner
    identity is what a "rivalry" actually means. A game between two teams
    with the same owner (shouldn't normally happen) is skipped.

    Returns (owners, matrix): owners is every owner name seen, sorted;
    matrix[a][b] is {"wins", "losses", "ties"} -- a's record against b.
    Only pairs that have actually played each other get an entry.
    """
    owners = set()
    matrix = {}
    for season in all_standings:
        owner_by_team = {s["teamId"]: s["owner"] for s in season["standings"]}
        for w in season["weeks"]:
            for g in w["games"]:
                a, b = owner_by_team.get(g["home"]), owner_by_team.get(g["away"])
                if not a or not b or a == b:
                    continue
                owners.add(a)
                owners.add(b)
                cell_a = matrix.setdefault(a, {}).setdefault(
                    b, {"wins": 0, "losses": 0, "ties": 0})
                cell_b = matrix.setdefault(b, {}).setdefault(
                    a, {"wins": 0, "losses": 0, "ties": 0})
                if g["winner"] == g["home"]:
                    cell_a["wins"] += 1
                    cell_b["losses"] += 1
                elif g["winner"] == g["away"]:
                    cell_b["wins"] += 1
                    cell_a["losses"] += 1
                else:
                    cell_a["ties"] += 1
                    cell_b["ties"] += 1
    return sorted(owners), matrix


def build_career_stats(all_standings):
    """Career totals per owner across every given season's §5 standings dict.

    Matched by owner name (see build_rivalries for why: teamId's owner can
    change between seasons). Returns a list of career rows, sorted by wins
    desc then pointsFor desc -- the same convention as a single season's
    standings. Each row:

    owner, seasons (count played), wins/losses/ties (career H2H record),
    pointsFor, gamesPlayed, careerAverage (pointsFor / gamesPlayed, a
    weighted average -- NOT the mean of each season's average), titles
    (seasons finished rank 1), topHalfPoints, luckIndex (career total),
    bestWeek/worstWeek ({score, season, week}), bestSeason ({points, season}).
    """
    careers = {}
    for season in all_standings:
        year = season["season"]
        owner_by_team = {s["teamId"]: s["owner"] for s in season["standings"]}
        playoffs = season.get("playoffs")
        champion_owner = (owner_by_team.get(playoffs["champion"])
                          if playoffs else None)
        runner_up_owner = (owner_by_team.get(playoffs["runnerUp"])
                           if playoffs else None)
        # Leading an unfinished season is not a regular-season title. Without
        # this, whoever happens to top the standings in week 2 is credited
        # with a finish they haven't earned.
        season_complete = (season.get("throughWeek")
                           == season.get("regularSeasonWeeks"))
        for row in season["standings"]:
            c = careers.setdefault(row["owner"], {
                "owner": row["owner"], "seasons": 0, "wins": 0, "losses": 0,
                "ties": 0, "pointsFor": 0.0, "gamesPlayed": 0,
                # "titles" counts actual championships (won the final);
                # "regularSeasonFirsts" counts finishing #1 in the dual-point
                # standings. These are NOT the same thing and conflating them
                # is what made the site name the wrong 2025 champion.
                "titles": 0, "regularSeasonFirsts": 0, "runnerUps": 0,
                "championshipYears": [],
                "topHalfPoints": 0, "luckIndex": 0,
                "bestWeek": None, "worstWeek": None, "bestSeason": None,
            })
            c["seasons"] += 1
            parts = [int(p) for p in row["record"].split("-")]
            w, l = parts[0], parts[1]
            t = parts[2] if len(parts) > 2 else 0
            c["wins"] += w
            c["losses"] += l
            c["ties"] += t
            c["pointsFor"] += row["pointsFor"]
            c["gamesPlayed"] += w + l + t
            c["topHalfPoints"] += row["topHalfPoints"]
            c["luckIndex"] += row["luckIndex"]
            if row["rank"] == 1 and season_complete:
                c["regularSeasonFirsts"] += 1
            if champion_owner is not None and row["owner"] == champion_owner:
                c["titles"] += 1
                c["championshipYears"].append(year)
            if runner_up_owner is not None and row["owner"] == runner_up_owner:
                c["runnerUps"] += 1
            if c["bestSeason"] is None or row["points"] > c["bestSeason"]["points"]:
                c["bestSeason"] = {"points": row["points"], "season": year}
        for w in season["weeks"]:
            for t in w["teams"]:
                owner = owner_by_team.get(t["teamId"])
                if not owner or owner not in careers:
                    continue
                c = careers[owner]
                entry = {"score": t["score"], "season": year, "week": w["week"]}
                if c["bestWeek"] is None or t["score"] > c["bestWeek"]["score"]:
                    c["bestWeek"] = entry
                if c["worstWeek"] is None or t["score"] < c["worstWeek"]["score"]:
                    c["worstWeek"] = entry

    for c in careers.values():
        c["careerAverage"] = (round(c["pointsFor"] / c["gamesPlayed"], 1)
                              if c["gamesPlayed"] else 0.0)
        c["pointsFor"] = round(c["pointsFor"], 1)

    return sorted(careers.values(),
                  key=lambda c: (-c["wins"], -c["pointsFor"]))


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