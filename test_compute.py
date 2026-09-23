"""Tests for compute.py — the dual-point math (SPEC.md §9 L2).

Run: python -m unittest test_compute -v

Covers the mandatory scenarios: a normal week, an H2H tie, a top-half
boundary tie, and that weeks 15-17 contribute no dual points.
"""
import unittest

import compute

UPDATED = "2026-09-18T13:04:11Z"


def make_matchup(week, home_id, away_id, home_score, away_score, played=True):
    if not played:
        return {
            "matchupPeriodId": week,
            "home": {"teamId": home_id, "totalPoints": 0.0},
            "away": {"teamId": away_id, "totalPoints": 0.0},
            "winner": "UNDECIDED",
        }
    if home_score > away_score:
        winner = "HOME"
    elif away_score > home_score:
        winner = "AWAY"
    else:
        winner = "TIE"
    return {
        "matchupPeriodId": week,
        "home": {"teamId": home_id, "totalPoints": home_score},
        "away": {"teamId": away_id, "totalPoints": away_score},
        "winner": winner,
    }


def week_games(scores, week=1):
    """Pair 12 scores in order: (1,2), (3,4), (5,6), (7,8), (9,10), (11,12)."""
    assert len(scores) == 12
    return [(2 * i + 1, 2 * i + 2, scores[2 * i], scores[2 * i + 1])
            for i in range(6)]


def make_raw(weeks, week_count=14, season=2025):
    """Build a raw-fetch-shaped dict.

    weeks: {week: [(home_id, away_id, home_score, away_score[, played]), ...]}
    """
    schedule = []
    for week, games in weeks.items():
        for game in games:
            schedule.append(make_matchup(week, *game))
    teams = [{"id": i, "name": f"Team {i}", "primaryOwner": f"{{o{i}}}",
              "owners": [f"{{o{i}}}"]} for i in range(1, 13)]
    members = [{"id": f"{{o{i}}}", "firstName": f"First{i}",
                "lastName": f"Last{i}", "displayName": f"user{i}"}
               for i in range(1, 13)]
    return {
        "mMatchupScore": {"seasonId": season, "id": 877873, "schedule": schedule},
        "mTeam": {"teams": teams, "members": members},
        "mSettings": {"settings": {"scheduleSettings":
                                   {"matchupPeriodCount": week_count}}},
    }


def full_season_weeks():
    """14 weeks of distinct scores: week w, team i scores 100 + 10w + (i-1)."""
    return {w: week_games([100 + 10 * w + i for i in range(12)], week=w)
            for w in range(1, 15)}


class TestNormalWeek(unittest.TestCase):
    """A normal week: 12 distinct scores, 6 decided matchups."""

    SCORES = [150, 100, 140, 110, 130, 120, 125, 105, 115, 135, 108, 118]

    def setUp(self):
        self.week = compute.compute_week(1, [make_matchup(1, *g)
                                              for g in week_games(self.SCORES)])

    def test_score_to_beat_is_sixth_lowest(self):
        # sorted: 100 105 108 110 115 118 | 120 125 130 135 140 150
        self.assertEqual(self.week["scoreToBeat"], 118)

    def test_h2h_points_go_to_higher_score(self):
        self.assertEqual([g["winner"] for g in self.week["games"]],
                         [1, 3, 5, 7, 10, 12])

    def test_top_half_is_strictly_above_score_to_beat(self):
        top_half = {t["teamId"] for t in self.week["teams"] if t["topHalf"]}
        self.assertEqual(top_half, {1, 3, 5, 6, 7, 10})

    def test_week_points(self):
        expected = {1: 2, 2: 0, 3: 2, 4: 0, 5: 2, 6: 1,
                    7: 2, 8: 0, 9: 0, 10: 2, 11: 0, 12: 1}
        for t in self.week["teams"]:
            self.assertEqual(t["weekPoints"], expected[t["teamId"]],
                             f"team {t['teamId']}")
        # a normal week distributes 6 H2H + 6 top-half = 12 points
        self.assertEqual(sum(t["weekPoints"] for t in self.week["teams"]), 12)

    def test_week_shape(self):
        self.assertEqual(self.week["week"], 1)
        self.assertEqual(len(self.week["games"]), 6)
        self.assertEqual(len(self.week["teams"]), 12)
        self.assertEqual([t["teamId"] for t in self.week["teams"]],
                         list(range(1, 13)))


class TestH2HTie(unittest.TestCase):
    """An exact H2H tie: no point to either team."""

    SCORES = [100, 100, 140, 110, 130, 120, 125, 105, 115, 135, 108, 118]

    def setUp(self):
        self.week = compute.compute_week(1, [make_matchup(1, *g)
                                              for g in week_games(self.SCORES)])

    def test_tied_game_has_no_winner(self):
        self.assertIsNone(self.week["games"][0]["winner"])

    def test_tied_teams_get_no_h2h_point(self):
        by_id = {t["teamId"]: t for t in self.week["teams"]}
        self.assertEqual(by_id[1]["h2h"], 0)
        self.assertEqual(by_id[2]["h2h"], 0)
        # only 5 H2H points awarded that week
        self.assertEqual(sum(t["h2h"] for t in self.week["teams"]), 5)

    def test_rest_of_week_unaffected(self):
        # sorted: 100 100 105 108 110 115 | 118 120 125 130 135 140
        self.assertEqual(self.week["scoreToBeat"], 115)
        by_id = {t["teamId"]: t for t in self.week["teams"]}
        self.assertEqual([t["teamId"] for t in self.week["teams"] if t["topHalf"]],
                         [3, 5, 6, 7, 10, 12])
        self.assertEqual(sum(t["weekPoints"] for t in self.week["teams"]), 11)


class TestTopHalfBoundaryTie(unittest.TestCase):
    """6th and 7th lowest scores identical: neither gets the top-half point,
    so the league awards 5 top-half points that week rather than 7."""

    SCORES = [90, 91, 92, 93, 94, 100, 100, 101, 102, 103, 104, 105]

    def setUp(self):
        self.week = compute.compute_week(1, [make_matchup(1, *g)
                                              for g in week_games(self.SCORES)])

    def test_score_to_beat_is_the_tied_score(self):
        # sorted: 90 91 92 93 94 100 100 101 102 103 104 105
        self.assertEqual(self.week["scoreToBeat"], 100)

    def test_teams_at_the_boundary_get_no_point(self):
        by_id = {t["teamId"]: t for t in self.week["teams"]}
        self.assertEqual(by_id[6]["score"], 100)
        self.assertEqual(by_id[7]["score"], 100)
        self.assertEqual(by_id[6]["topHalf"], 0)
        self.assertEqual(by_id[7]["topHalf"], 0)

    def test_only_five_top_half_points_awarded(self):
        self.assertEqual(sum(t["topHalf"] for t in self.week["teams"]), 5)
        by_id = {t["teamId"]: t for t in self.week["teams"]}
        self.assertEqual([t["teamId"] for t in self.week["teams"] if t["topHalf"]],
                         [8, 9, 10, 11, 12])


class TestPlayoffWeeksContributeNothing(unittest.TestCase):
    """Weeks 15-17 are the playoff bracket: no dual points, no standings data."""

    def setUp(self):
        weeks = full_season_weeks()
        # playoff bracket with huge scores that would distort anything
        # if they leaked into the regular-season math
        weeks[15] = [(1, 2, 500, 400), (3, 4, 450, 350), (5, 6, 420, 380)]
        weeks[16] = [(1, 3, 600, 300), (5, 2, 550, 320)]
        weeks[17] = [(1, 5, 700, 200)]
        self.out = compute.build_standings(make_raw(weeks), UPDATED)

    def test_only_regular_season_weeks_present(self):
        self.assertEqual(self.out["throughWeek"], 14)
        self.assertEqual(self.out["regularSeasonWeeks"], 14)
        self.assertEqual(len(self.out["weeks"]), 14)
        self.assertEqual(max(w["week"] for w in self.out["weeks"]), 14)

    def test_playoff_scores_do_not_reach_standings(self):
        by_id = {r["teamId"]: r for r in self.out["standings"]}
        # team 1's regular-season scores: 100 + 10w for w in 1..14
        expected_pf = sum(100 + 10 * w for w in range(1, 15))
        self.assertEqual(by_id[1]["pointsFor"], expected_pf)
        self.assertEqual(by_id[1]["averageScore"], round(expected_pf / 14, 1))
        # 14 regular-season games, no ties in this fixture
        wins, losses = by_id[1]["record"].split("-")
        self.assertEqual(int(wins) + int(losses), 14)
        # dual points capped at 2 per week x 14 weeks
        for r in self.out["standings"]:
            self.assertLessEqual(r["points"], 28)
            self.assertEqual(r["points"],
                             r["h2hPoints"] + r["topHalfPoints"])

    def test_identical_output_without_playoff_weeks(self):
        out_no_playoffs = compute.build_standings(
            make_raw(full_season_weeks()), UPDATED)
        self.assertEqual(self.out["standings"], out_no_playoffs["standings"])
        self.assertEqual(self.out["weeks"], out_no_playoffs["weeks"])


class TestInProgressSeason(unittest.TestCase):
    """An in-progress season: unplayed weeks are UNDECIDED with 0.0 scores."""

    def setUp(self):
        weeks = {
            1: week_games([150, 100, 140, 110, 130, 120,
                           125, 105, 115, 135, 108, 118], week=1),
            2: week_games([110, 120, 100, 130, 125, 105,
                           140, 95, 135, 100, 150, 90], week=2),
        }
        for w in range(3, 15):
            weeks[w] = [(2 * i + 1, 2 * i + 2, 0.0, 0.0, False)
                        for i in range(6)]
        self.out = compute.build_standings(make_raw(weeks), UPDATED)

    def test_through_week_stops_at_last_complete_week(self):
        self.assertEqual(self.out["throughWeek"], 2)
        self.assertEqual([w["week"] for w in self.out["weeks"]], [1, 2])

    def test_standings_cover_played_weeks_only(self):
        by_id = {r["teamId"]: r for r in self.out["standings"]}
        self.assertEqual(len(self.out["standings"]), 12)
        # team 1: 150 + 110
        self.assertEqual(by_id[1]["pointsFor"], 260.0)
        self.assertEqual(by_id[1]["averageScore"], 130.0)
        wins, losses = by_id[1]["record"].split("-")
        self.assertEqual(int(wins) + int(losses), 2)


class TestStandingsShapeAndSort(unittest.TestCase):
    """§5 output shape, sort order, and record format."""

    def setUp(self):
        self.out = compute.build_standings(make_raw(full_season_weeks()),
                                           UPDATED)

    def test_top_level_keys(self):
        self.assertEqual(self.out["season"], 2025)
        self.assertEqual(self.out["league"], "877873")
        self.assertEqual(self.out["updated"], UPDATED)
        self.assertEqual(self.out["regularSeasonWeeks"], 14)
        self.assertEqual(self.out["throughWeek"], 14)
        self.assertEqual(len(self.out["standings"]), 12)

    def test_ranks_and_sort_order(self):
        rows = self.out["standings"]
        self.assertEqual([r["rank"] for r in rows], list(range(1, 13)))
        for a, b in zip(rows, rows[1:]):
            self.assertGreaterEqual(a["points"], b["points"])
            if a["points"] == b["points"]:
                self.assertGreaterEqual(a["pointsFor"], b["pointsFor"])

    def test_every_week_distributes_twelve_points(self):
        for w in self.out["weeks"]:
            self.assertEqual(len(w["games"]), 6)
            self.assertEqual(len(w["teams"]), 12)
            self.assertEqual(sum(t["weekPoints"] for t in w["teams"]), 12)

    def test_record_and_owner(self):
        by_id = {r["teamId"]: r for r in self.out["standings"]}
        for r in self.out["standings"]:
            wins, losses = r["record"].split("-")
            self.assertEqual(int(wins) + int(losses), 14)
        self.assertEqual(by_id[1]["owner"], "First1 Last1")
        self.assertEqual(by_id[1]["name"], "Team 1")

    def test_record_includes_ties_when_there_are_any(self):
        weeks = {
            1: week_games([100, 100, 140, 110, 130, 120,
                           125, 105, 115, 135, 108, 118], week=1),
            2: week_games([90, 120, 100, 130, 125, 105,
                           140, 95, 135, 100, 150, 90], week=2),
        }
        out = compute.build_standings(make_raw(weeks, week_count=2), UPDATED)
        by_id = {r["teamId"]: r for r in out["standings"]}
        # team 1: week 1 tie (100-100), week 2 loss (90 vs 120)
        self.assertEqual(by_id[1]["record"], "0-1-1")


class TestLuckIndexAndStreak(unittest.TestCase):
    """Luck index (h2hPoints - topHalfPoints) and current H2H streak.

    full_season_weeks() pairs teams (1,2) (3,4) ... (11,12) every week with
    strictly increasing scores by team id, so the higher id in each pair
    always wins H2H. Team 2 wins every week (h2h) while always scoring in
    the bottom half (topHalf never earned) -- maximally lucky. Team 12 wins
    every week AND always scores top-half -- deserved wins, no luck. Team 1
    loses every week and is always bottom half -- unlucky in neither
    direction, just bad.
    """

    def setUp(self):
        self.out = compute.build_standings(make_raw(full_season_weeks()),
                                           UPDATED)
        self.by_id = {r["teamId"]: r for r in self.out["standings"]}

    def test_lucky_team_wins_without_scoring(self):
        team2 = self.by_id[2]
        self.assertEqual(team2["h2hPoints"], 14)
        self.assertEqual(team2["topHalfPoints"], 0)
        self.assertEqual(team2["luckIndex"], 14)
        self.assertEqual(team2["streak"], "W14")

    def test_deserving_team_has_no_luck(self):
        team12 = self.by_id[12]
        self.assertEqual(team12["h2hPoints"], 14)
        self.assertEqual(team12["topHalfPoints"], 14)
        self.assertEqual(team12["luckIndex"], 0)
        self.assertEqual(team12["streak"], "W14")

    def test_losing_team_streak_and_zero_luck(self):
        team1 = self.by_id[1]
        self.assertEqual(team1["h2hPoints"], 0)
        self.assertEqual(team1["topHalfPoints"], 0)
        self.assertEqual(team1["luckIndex"], 0)
        self.assertEqual(team1["streak"], "L14")

    def test_streak_breaks_on_result_change(self):
        weeks = {
            1: week_games([150, 100, 140, 110, 130, 120,
                           125, 105, 115, 135, 108, 118], week=1),
            2: week_games([90, 120, 100, 130, 125, 105,
                           140, 95, 135, 100, 150, 91], week=2),
        }
        # team 1: week 1 win (150 > 100), week 2 loss (90 < 120)
        out = compute.build_standings(make_raw(weeks, week_count=2), UPDATED)
        by_id = {r["teamId"]: r for r in out["standings"]}
        self.assertEqual(by_id[1]["streak"], "L1")

    def test_no_games_played_streak_is_dash(self):
        weeks = {w: [(2 * i + 1, 2 * i + 2, 0.0, 0.0, False) for i in range(6)]
                 for w in range(1, 15)}
        out = compute.build_standings(make_raw(weeks), UPDATED)
        for r in out["standings"]:
            self.assertEqual(r["streak"], "-")
            self.assertEqual(r["luckIndex"], 0)


class TestRivalries(unittest.TestCase):
    """build_rivalries: all-time head-to-head records, matched by owner."""

    def setUp(self):
        self.season1 = compute.build_standings(
            make_raw(full_season_weeks(), season=2024), UPDATED)
        # Same owners, same team ids, second season -- as if the same
        # 12-team league played a second year (make_raw's team/owner
        # mapping is deterministic by id, so this reuses it exactly).
        self.season2 = compute.build_standings(
            make_raw(full_season_weeks(), season=2025), UPDATED)

    def test_record_accumulates_across_seasons(self):
        owners, matrix = compute.build_rivalries([self.season1, self.season2])
        # team 1 (First1 Last1) always loses to team 2 (First2 Last2) in
        # full_season_weeks(), 14 times per season, 2 seasons = 28 meetings.
        a, b = "First1 Last1", "First2 Last2"
        self.assertIn(a, owners)
        self.assertEqual(matrix[a][b], {"wins": 0, "losses": 28, "ties": 0})
        self.assertEqual(matrix[b][a], {"wins": 28, "losses": 0, "ties": 0})

    def test_teams_that_never_met_have_no_entry(self):
        _, matrix = compute.build_rivalries([self.season1])
        # team 1 only ever plays team 2 in full_season_weeks()'s fixed pairing.
        self.assertNotIn("First3 Last3", matrix["First1 Last1"])

    def test_single_season_matches_that_seasons_games(self):
        owners, matrix = compute.build_rivalries([self.season1])
        self.assertEqual(len(owners), 12)
        a, b = "First1 Last1", "First2 Last2"
        self.assertEqual(matrix[a][b]["losses"], 14)

    def test_no_seasons_gives_empty_result(self):
        owners, matrix = compute.build_rivalries([])
        self.assertEqual(owners, [])
        self.assertEqual(matrix, {})


if __name__ == "__main__":
    unittest.main()