"""Tests for compute.py — the dual-point math (SPEC.md §9 L2).

Run: python -m unittest test_compute -v

Covers the mandatory scenarios: a normal week, an H2H tie, a top-half
boundary tie, and that weeks 15-17 contribute no dual points.
"""
import unittest

import build
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


def make_bracket_matchup(week, home_id, away_id, home_score, away_score,
                         tier="WINNERS_BRACKET", played=True):
    """A playoff-bracket schedule entry. away_id=None makes it a bye (no
    'away' side at all), which is how ESPN represents a top-seed bye.
    """
    m = make_matchup(week, home_id, away_id or 1, home_score,
                     away_score or 0.0, played=played)
    m["playoffTierType"] = tier
    if away_id is None:
        del m["away"]
        m["winner"] = "UNDECIDED"
    return m


def make_raw(weeks, week_count=14, season=2025, bracket=None,
             playoff_team_count=6, name="Fantasy Football Fantasy",
             final_ranks=None):
    """Build a raw-fetch-shaped dict.

    weeks: {week: [(home_id, away_id, home_score, away_score[, played]), ...]}
    bracket: optional list of pre-built playoff schedule entries.
    """
    schedule = []
    for week, games in weeks.items():
        for game in games:
            schedule.append(make_matchup(week, *game))
    for m in bracket or []:
        schedule.append(m)
    teams = [{"id": i, "name": f"Team {i}", "primaryOwner": f"{{o{i}}}",
              "owners": [f"{{o{i}}}"],
              # ESPN publishes 0 until the season is over.
              "rankCalculatedFinal": (final_ranks or {}).get(i, 0)}
             for i in range(1, 13)]
    members = [{"id": f"{{o{i}}}", "firstName": f"First{i}",
                "lastName": f"Last{i}", "displayName": f"user{i}"}
               for i in range(1, 13)]
    return {
        "mMatchupScore": {"seasonId": season, "id": 877873, "schedule": schedule},
        "mTeam": {"teams": teams, "members": members},
        "mSettings": {"settings": {"name": name,
                                   "scheduleSettings":
                                   {"matchupPeriodCount": week_count,
                                    "playoffTeamCount": playoff_team_count}}},
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


class TestCareerStats(unittest.TestCase):
    """build_career_stats: cross-season totals per owner."""

    def setUp(self):
        self.season1 = compute.build_standings(
            make_raw(full_season_weeks(), season=2024), UPDATED)
        self.season2 = compute.build_standings(
            make_raw(full_season_weeks(), season=2025), UPDATED)

    def test_totals_accumulate_across_seasons(self):
        careers = compute.build_career_stats([self.season1, self.season2])
        by_owner = {c["owner"]: c for c in careers}
        # team 12 (First12 Last12) wins every H2H game and always tops the
        # scoring in full_season_weeks(): 14 wins/season x 2 seasons.
        team12 = by_owner["First12 Last12"]
        self.assertEqual(team12["seasons"], 2)
        self.assertEqual(team12["wins"], 28)
        self.assertEqual(team12["losses"], 0)
        self.assertEqual(team12["gamesPlayed"], 28)
        # Finishing #1 in the regular season is NOT a championship. Neither
        # test season has a playoff bracket, so nobody has a title.
        self.assertEqual(team12["regularSeasonFirsts"], 2)
        self.assertEqual(team12["titles"], 0)

    def test_career_average_is_weighted_not_mean_of_seasons(self):
        careers = compute.build_career_stats([self.season1, self.season2])
        by_owner = {c["owner"]: c for c in careers}
        c = by_owner["First1 Last1"]
        self.assertEqual(c["gamesPlayed"], 28)
        self.assertAlmostEqual(c["careerAverage"],
                               round(c["pointsFor"] / 28, 1))

    def test_best_and_worst_week_tracked_with_season_and_week(self):
        careers = compute.build_career_stats([self.season1, self.season2])
        by_owner = {c["owner"]: c for c in careers}
        # team 12's score each week is 100 + 10w + 11, identical in both
        # seasons since full_season_weeks() doesn't vary by season -- the
        # tie at week 14 (251 in both years) goes to whichever season was
        # given first (2024), since ties don't overwrite bestWeek/worstWeek.
        c = by_owner["First12 Last12"]
        self.assertEqual(c["bestWeek"], {"score": 251, "season": 2024, "week": 14})
        self.assertEqual(c["worstWeek"], {"score": 121, "season": 2024, "week": 1})

    def test_sorted_by_wins_then_points_for(self):
        careers = compute.build_career_stats([self.season1, self.season2])
        for a, b in zip(careers, careers[1:]):
            self.assertGreaterEqual(a["wins"], b["wins"])
            if a["wins"] == b["wins"]:
                self.assertGreaterEqual(a["pointsFor"], b["pointsFor"])

    def test_empty_input_gives_empty_result(self):
        self.assertEqual(compute.build_career_stats([]), [])


if __name__ == "__main__":
    unittest.main()

class TestScoreToBeatScalesWithLeagueSize(unittest.TestCase):
    """score_to_beat derives the boundary from the field size.

    v1 hardcoded index [5], the 6th-lowest of 12. Any other league size
    silently computed the wrong top-half boundary -- the scoring rule this
    whole project exists to get right.
    """

    def test_twelve_team_league_is_unchanged(self):
        scores = [100 + i for i in range(12)]  # 100..111
        self.assertEqual(compute.score_to_beat(scores), 105)
        self.assertEqual(compute.score_to_beat(scores), sorted(scores)[5])

    def test_ten_team_league_uses_fifth_lowest(self):
        scores = [100 + i for i in range(10)]  # 100..109
        self.assertEqual(compute.score_to_beat(scores), 104)
        self.assertEqual(len([s for s in scores if s > 104]), 5)

    def test_eight_team_league_uses_fourth_lowest(self):
        scores = [100 + i for i in range(8)]
        self.assertEqual(compute.score_to_beat(scores), 103)
        self.assertEqual(len([s for s in scores if s > 103]), 4)

    def test_odd_league_rounds_the_top_half_up(self):
        scores = [100 + i for i in range(11)]  # 100..110
        self.assertEqual(compute.score_to_beat(scores), 104)
        self.assertEqual(len([s for s in scores if s > 104]), 6)

    def test_order_does_not_matter(self):
        self.assertEqual(compute.score_to_beat([5, 1, 4, 2, 3, 6]),
                         compute.score_to_beat([1, 2, 3, 4, 5, 6]))

    def test_too_few_scores_raises(self):
        with self.assertRaises(ValueError):
            compute.score_to_beat([100])


class TestPlayoffBracket(unittest.TestCase):
    """build_playoffs: who actually won the league.

    Regression cover for the bug where weeks 15-17 were discarded entirely,
    so Career Stats credited the title to the regular-season #1 finisher
    even when that owner lost the championship game.
    """

    def _season_with_final(self, home_id, away_id, home_score, away_score,
                           season=2025):
        bracket = [
            make_bracket_matchup(15, 3, None, 110.0, None),   # 1-seed bye
            make_bracket_matchup(15, 5, 9, 136.0, 177.4),
            make_bracket_matchup(16, 3, 9, 140.9, 115.8),
            make_bracket_matchup(17, home_id, away_id, home_score, away_score),
        ]
        return compute.build_standings(
            make_raw(full_season_weeks(), season=season, bracket=bracket),
            UPDATED)

    def test_champion_is_the_winner_of_the_final(self):
        out = self._season_with_final(2, 12, 108.9, 154.5)
        self.assertEqual(out["playoffs"]["champion"], 12)
        self.assertEqual(out["playoffs"]["runnerUp"], 2)
        self.assertEqual(out["playoffs"]["finalWeek"], 17)
        self.assertEqual(out["playoffs"]["championScore"], 154.5)
        self.assertEqual(out["playoffs"]["runnerUpScore"], 108.9)

    def test_home_team_can_win_the_final(self):
        out = self._season_with_final(4, 12, 102.3, 80.0)
        self.assertEqual(out["playoffs"]["champion"], 4)
        self.assertEqual(out["playoffs"]["runnerUp"], 12)

    def test_champion_need_not_be_the_regular_season_leader(self):
        # Team 12 tops the regular season in full_season_weeks(); team 2
        # wins the final. The champion must be team 2.
        out = self._season_with_final(2, 5, 150.0, 100.0)
        self.assertEqual(out["standings"][0]["teamId"], 12)
        self.assertEqual(out["playoffs"]["champion"], 2)

    def test_no_bracket_means_no_champion(self):
        out = compute.build_standings(make_raw(full_season_weeks()), UPDATED)
        self.assertIsNone(out["playoffs"])

    def test_undecided_final_means_no_champion_yet(self):
        bracket = [
            make_bracket_matchup(15, 5, 9, 136.0, 177.4),
            make_bracket_matchup(16, 3, 9, 140.9, 115.8),
            make_bracket_matchup(17, 3, 9, 0.0, 0.0, played=False),
        ]
        out = compute.build_standings(
            make_raw(full_season_weeks(), bracket=bracket), UPDATED)
        self.assertIsNone(out["playoffs"])

    def test_mid_playoffs_does_not_crown_a_semifinal_winner(self):
        # The final exists but is unplayed. Picking the highest *played*
        # bracket week would wrongly crown the week-16 winner.
        bracket = [
            make_bracket_matchup(16, 3, 9, 140.9, 115.8),
            make_bracket_matchup(17, 3, 11, 0.0, 0.0, played=False),
        ]
        out = compute.build_standings(
            make_raw(full_season_weeks(), bracket=bracket), UPDATED)
        self.assertIsNone(out["playoffs"])

    def test_consolation_ladder_never_produces_a_champion(self):
        bracket = [
            make_bracket_matchup(17, 7, 8, 120.0, 90.0,
                                 tier="LOSERS_CONSOLATION_LADDER"),
            make_bracket_matchup(17, 5, 6, 130.0, 95.0,
                                 tier="WINNERS_CONSOLATION_LADDER"),
        ]
        out = compute.build_standings(
            make_raw(full_season_weeks(), bracket=bracket), UPDATED)
        self.assertIsNone(out["playoffs"])

    def test_tied_final_reports_no_champion(self):
        out = self._season_with_final(2, 12, 120.0, 120.0)
        self.assertIsNone(out["playoffs"])

    def test_bracket_byes_are_recorded_without_an_away_team(self):
        out = self._season_with_final(2, 12, 108.9, 154.5)
        byes = [g for g in out["playoffs"]["games"] if g["bye"]]
        self.assertEqual(len(byes), 1)
        self.assertEqual(byes[0]["home"], 3)
        self.assertIsNone(byes[0]["away"])

    def test_playoff_scores_still_contribute_no_dual_points(self):
        out = self._season_with_final(2, 12, 108.9, 154.5)
        self.assertEqual(out["throughWeek"], 14)
        self.assertEqual([w["week"] for w in out["weeks"]], list(range(1, 15)))

    def test_playoff_team_count_and_league_name_come_from_settings(self):
        out = compute.build_standings(
            make_raw(full_season_weeks(), playoff_team_count=4,
                     name="Some Other League"), UPDATED)
        self.assertEqual(out["playoffTeamCount"], 4)
        self.assertEqual(out["leagueName"], "Some Other League")


class TestCareerChampionships(unittest.TestCase):
    """Career titles count championships won, not regular seasons led."""

    def setUp(self):
        # Team 12 dominates both regular seasons. Team 2 wins the 2024
        # final; team 12 wins the 2025 final.
        self.s2024 = compute.build_standings(
            make_raw(full_season_weeks(), season=2024, bracket=[
                make_bracket_matchup(17, 2, 12, 150.0, 100.0)]), UPDATED)
        self.s2025 = compute.build_standings(
            make_raw(full_season_weeks(), season=2025, bracket=[
                make_bracket_matchup(17, 12, 2, 150.0, 100.0)]), UPDATED)

    def test_titles_track_the_final_not_the_standings(self):
        by_owner = {c["owner"]: c
                    for c in compute.build_career_stats([self.s2024, self.s2025])}
        t12, t2 = by_owner["First12 Last12"], by_owner["First2 Last2"]
        # Team 12 led the regular season twice but won one title.
        self.assertEqual(t12["regularSeasonFirsts"], 2)
        self.assertEqual(t12["titles"], 1)
        self.assertEqual(t12["championshipYears"], [2025])
        self.assertEqual(t12["runnerUps"], 1)
        # Team 2 never led the regular season but has a ring.
        self.assertEqual(t2["regularSeasonFirsts"], 0)
        self.assertEqual(t2["titles"], 1)
        self.assertEqual(t2["championshipYears"], [2024])
        self.assertEqual(t2["runnerUps"], 1)

    def test_owners_without_rings_have_none(self):
        by_owner = {c["owner"]: c
                    for c in compute.build_career_stats([self.s2024, self.s2025])}
        self.assertEqual(by_owner["First7 Last7"]["titles"], 0)
        self.assertEqual(by_owner["First7 Last7"]["championshipYears"], [])

    def test_season_without_a_bracket_awards_no_titles(self):
        plain = compute.build_standings(
            make_raw(full_season_weeks(), season=2026), UPDATED)
        by_owner = {c["owner"]: c for c in compute.build_career_stats([plain])}
        self.assertEqual(sum(c["titles"] for c in by_owner.values()), 0)
        self.assertEqual(by_owner["First12 Last12"]["regularSeasonFirsts"], 1)

    def test_leading_an_unfinished_season_is_not_a_regular_season_title(self):
        # Two weeks played out of 14: nobody has finished anything yet.
        partial = compute.build_standings(
            make_raw({w: week_games([100 + 10 * w + i for i in range(12)],
                                     week=w) for w in (1, 2)}, season=2026),
            UPDATED)
        self.assertEqual(partial["throughWeek"], 2)
        by_owner = {c["owner"]: c
                    for c in compute.build_career_stats([partial])}
        self.assertEqual(partial["standings"][0]["owner"], "First12 Last12")
        self.assertEqual(by_owner["First12 Last12"]["regularSeasonFirsts"], 0)
        self.assertEqual(sum(c["regularSeasonFirsts"]
                             for c in by_owner.values()), 0)


class TestFinalRank(unittest.TestCase):
    """finalRank carries ESPN's end-of-season placement.

    FFF reseeds the playoffs by hand off the dual-point standings, so
    `playoffSeed` does not describe the real bracket. `rankCalculatedFinal`
    is computed from results, so it survives the manual reseed -- verified
    against the winners bracket for 2022-2025, where rank 1 is the final's
    winner every time.
    """

    def test_final_rank_is_carried_onto_each_standings_row(self):
        out = compute.build_standings(
            make_raw(full_season_weeks(),
                     final_ranks={12: 3, 2: 1, 5: 2}), UPDATED)
        by_team = {r["teamId"]: r for r in out["standings"]}
        self.assertEqual(by_team[2]["finalRank"], 1)
        self.assertEqual(by_team[5]["finalRank"], 2)
        self.assertEqual(by_team[12]["finalRank"], 3)

    def test_in_progress_season_has_no_final_rank(self):
        # ESPN publishes rankCalculatedFinal as 0 until the season ends;
        # 0 must become None so the UI can hide the column rather than
        # show a league of zeroth-place finishers.
        out = compute.build_standings(make_raw(full_season_weeks()), UPDATED)
        self.assertTrue(all(r["finalRank"] is None for r in out["standings"]))

    def test_final_rank_is_independent_of_regular_season_rank(self):
        # Team 12 tops the dual-point standings; team 2 finishes 1st.
        out = compute.build_standings(
            make_raw(full_season_weeks(),
                     final_ranks={2: 1, 12: 4}), UPDATED)
        by_team = {r["teamId"]: r for r in out["standings"]}
        self.assertEqual(out["standings"][0]["teamId"], 12)
        self.assertEqual(by_team[12]["rank"], 1)
        self.assertEqual(by_team[12]["finalRank"], 4)
        self.assertEqual(by_team[2]["finalRank"], 1)


class TestOrdinalFilter(unittest.TestCase):
    """build.ordinal: placements are rendered as 1st/2nd/3rd/11th."""

    def test_common_suffixes(self):
        self.assertEqual(build.ordinal(1), "1st")
        self.assertEqual(build.ordinal(2), "2nd")
        self.assertEqual(build.ordinal(3), "3rd")
        self.assertEqual(build.ordinal(4), "4th")

    def test_teens_are_all_th(self):
        # The case a last-digit lookup gets wrong: "11st", "12nd", "13rd".
        for n in (11, 12, 13):
            self.assertTrue(build.ordinal(n).endswith("th"), n)

    def test_twenties_resume_normal_suffixes(self):
        self.assertEqual(build.ordinal(21), "21st")
        self.assertEqual(build.ordinal(22), "22nd")
        self.assertEqual(build.ordinal(23), "23rd")

    def test_none_renders_empty(self):
        self.assertEqual(build.ordinal(None), "")


class TestAllPlayRecords(unittest.TestCase):
    """all_play_records: record against the whole field, schedule removed."""

    def setUp(self):
        self.season = compute.build_standings(
            make_raw(full_season_weeks()), UPDATED)
        self.ap = compute.all_play_records(self.season)

    def test_every_team_plays_every_other_team_each_week(self):
        # 12 teams -> 11 notional games each, 14 weeks -> 154.
        for tid, rec in self.ap.items():
            total = rec["wins"] + rec["losses"] + rec["ties"]
            self.assertEqual(total, 11 * 14, f"team {tid}")

    def test_top_scorer_beats_the_whole_field_every_week(self):
        # full_season_weeks() gives team 12 the highest score every week.
        self.assertEqual(self.ap[12]["wins"], 11 * 14)
        self.assertEqual(self.ap[12]["losses"], 0)
        self.assertEqual(self.ap[12]["pct"], 1.0)

    def test_bottom_scorer_loses_to_the_whole_field(self):
        self.assertEqual(self.ap[1]["wins"], 0)
        self.assertEqual(self.ap[1]["losses"], 11 * 14)
        self.assertEqual(self.ap[1]["pct"], 0.0)

    def test_wins_and_losses_are_symmetric_across_the_league(self):
        total_w = sum(r["wins"] for r in self.ap.values())
        total_l = sum(r["losses"] for r in self.ap.values())
        self.assertEqual(total_w, total_l)

    def test_ties_count_as_half_a_win(self):
        # One week, six matchups, every team scoring exactly the same.
        season = compute.build_standings(
            make_raw({1: week_games([100.0] * 12)}), UPDATED)
        ap = compute.all_play_records(season)
        self.assertEqual(ap[1]["ties"], 11)
        self.assertEqual(ap[1]["wins"], 0)
        self.assertEqual(ap[1]["pct"], 0.5)


class TestScoringProfile(unittest.TestCase):
    """scoring_profile: volatility, weekly extremes, lucky/unlucky weeks."""

    def test_identical_scores_every_week_have_no_deviation(self):
        weeks = {w: week_games([100 + i for i in range(12)], week=w)
                 for w in range(1, 5)}
        season = compute.build_standings(make_raw(weeks), UPDATED)
        prof = compute.scoring_profile(season)
        self.assertEqual(prof[1]["stdev"], 0.0)

    def test_stdev_rises_with_swing(self):
        steady = {w: week_games([100 + i for i in range(12)], week=w)
                  for w in (1, 2)}
        swingy = {1: week_games([100 + i for i in range(12)], week=1),
                  2: week_games([200 + i for i in range(12)], week=2)}
        a = compute.scoring_profile(
            compute.build_standings(make_raw(steady), UPDATED))
        b = compute.scoring_profile(
            compute.build_standings(make_raw(swingy), UPDATED))
        self.assertLess(a[1]["stdev"], b[1]["stdev"])

    def test_weekly_firsts_and_lasts(self):
        season = compute.build_standings(
            make_raw(full_season_weeks()), UPDATED)
        prof = compute.scoring_profile(season)
        self.assertEqual(prof[12]["weeklyFirsts"], 14)
        self.assertEqual(prof[12]["weeklyLasts"], 0)
        self.assertEqual(prof[1]["weeklyLasts"], 14)

    def test_lucky_win_is_a_bottom_half_score_that_won(self):
        # Team 1 scores 10 (lowest by far) but its opponent scores 5.
        scores = [10.0, 5.0] + [100 + i for i in range(10)]
        season = compute.build_standings(
            make_raw({1: week_games(scores)}), UPDATED)
        prof = compute.scoring_profile(season)
        team1 = next(t for t in season["weeks"][0]["teams"] if t["teamId"] == 1)
        self.assertEqual(team1["h2h"], 1)
        self.assertEqual(team1["topHalf"], 0)
        self.assertEqual(prof[1]["luckyWins"], 1)
        self.assertEqual(prof[1]["unluckyLosses"], 0)

    def test_unlucky_loss_is_a_top_half_score_that_lost(self):
        # Teams 1 and 2 are the top two scores, but they play each other,
        # so the loser scored top-half and still lost.
        scores = [150.0, 149.0] + [100 + i for i in range(10)]
        season = compute.build_standings(
            make_raw({1: week_games(scores)}), UPDATED)
        prof = compute.scoring_profile(season)
        team2 = next(t for t in season["weeks"][0]["teams"] if t["teamId"] == 2)
        self.assertEqual(team2["h2h"], 0)
        self.assertEqual(team2["topHalf"], 1)
        self.assertEqual(prof[2]["unluckyLosses"], 1)


class TestSeasonRecords(unittest.TestCase):
    """season_records: single-game and single-week superlatives."""

    def setUp(self):
        # wk1 has a 60-point blowout (1 v 2) and a 1-point squeaker (3 v 4).
        wk1 = [(1, 2, 160.0, 100.0), (3, 4, 121.0, 120.0),
               (5, 6, 130.0, 110.0), (7, 8, 125.0, 105.0),
               (9, 10, 115.0, 112.0), (11, 12, 118.0, 108.0)]
        self.season = compute.build_standings(make_raw({1: wk1}), UPDATED)
        self.rec = compute.season_records(self.season)

    def test_biggest_blowout(self):
        self.assertEqual(self.rec["blowout"]["margin"], 60.0)
        self.assertEqual(self.rec["blowout"]["winner"], "First1 Last1")
        self.assertEqual(self.rec["blowout"]["loser"], "First2 Last2")

    def test_closest_game(self):
        self.assertEqual(self.rec["closest"]["margin"], 1.0)
        self.assertEqual(self.rec["closest"]["winner"], "First3 Last3")

    def test_high_and_low_weeks(self):
        self.assertEqual(self.rec["high"]["score"], 160.0)
        self.assertEqual(self.rec["high"]["owner"], "First1 Last1")
        self.assertEqual(self.rec["low"]["score"], 100.0)

    def test_tough_loss_is_the_best_losing_score(self):
        # 120.0 (team 4) is the highest score among the six losers.
        self.assertEqual(self.rec["toughLoss"]["score"], 120.0)
        self.assertEqual(self.rec["toughLoss"]["owner"], "First4 Last4")

    def test_cheap_win_is_the_worst_winning_score(self):
        # 115.0 (team 9) is the lowest score among the six winners.
        self.assertEqual(self.rec["cheapWin"]["score"], 115.0)
        self.assertEqual(self.rec["cheapWin"]["owner"], "First9 Last9")

    def test_shootout_and_snoozer_use_combined_points(self):
        # Combined totals: 260, 241, 240, 230, 227, 226.
        self.assertEqual(self.rec["shootout"]["combined"], 260.0)
        self.assertEqual(self.rec["snoozer"]["combined"], 226.0)
        self.assertEqual(self.rec["snoozer"]["winner"], "First11 Last11")

    def test_no_weeks_gives_no_records(self):
        empty = compute.build_standings(make_raw({}), UPDATED)
        self.assertEqual(compute.season_records(empty), {})


class TestSeasonAwards(unittest.TestCase):
    """season_awards: named superlatives, and deterministic."""

    def setUp(self):
        self.season = compute.build_standings(
            make_raw(full_season_weeks()), UPDATED)
        self.stats = compute.build_season_stats(self.season)
        self.by_key = {a["key"]: a for a in self.stats["awards"]}

    def test_the_wall_goes_to_the_best_all_play_record(self):
        self.assertEqual(self.by_key["wall"]["owner"], "First12 Last12")

    def test_ceiling_and_floor_go_to_the_right_teams(self):
        self.assertEqual(self.by_key["ceiling"]["owner"], "First12 Last12")
        self.assertEqual(self.by_key["floor"]["owner"], "First1 Last1")

    def test_every_award_is_fully_populated(self):
        for a in self.stats["awards"]:
            for field in ("key", "emoji", "name", "blurb", "owner", "detail"):
                self.assertTrue(a.get(field), f"{a.get('key')}.{field}")

    def test_awards_are_deterministic_across_runs(self):
        # The daily workflow commits only when docs/ changes, so an award
        # that rerolled per run would manufacture a commit every morning.
        again = compute.build_season_stats(self.season)["awards"]
        self.assertEqual(self.stats["awards"], again)

    def test_ties_break_on_team_id_not_iteration_order(self):
        # Every team scores identically every week, so every stat ties.
        weeks = {w: week_games([100.0] * 12, week=w) for w in range(1, 4)}
        season = compute.build_standings(make_raw(weeks), UPDATED)
        a = compute.build_season_stats(season)["awards"]
        b = compute.build_season_stats(season)["awards"]
        self.assertEqual(a, b)

    def test_empty_season_produces_no_crash(self):
        empty = compute.build_standings(make_raw({}), UPDATED)
        stats = compute.build_season_stats(empty)
        self.assertEqual(stats["records"], {})
        self.assertIsInstance(stats["awards"], list)

    def test_stats_table_covers_every_owner(self):
        self.assertEqual(len(self.stats["table"]), 12)
        row = next(r for r in self.stats["table"] if r["teamId"] == 12)
        self.assertEqual(row["allPlayPct"], 1.0)
        self.assertEqual(row["weeklyFirsts"], 14)


class TestAwardTies(unittest.TestCase):
    """Ties are shown as co-winners, not silently handed to one owner."""

    def test_names_formats_one_two_and_three_winners(self):
        rows = [{"owner": "A"}, {"owner": "B"}, {"owner": "C"}]
        self.assertEqual(compute._names(rows[:1]), "A")
        self.assertEqual(compute._names(rows[:2]), "A & B")
        self.assertEqual(compute._names(rows), "A, B & C")

    def test_leaders_returns_every_tied_row_ordered_by_team_id(self):
        rows = [{"teamId": 7, "v": 5}, {"teamId": 2, "v": 5},
                {"teamId": 9, "v": 1}]
        self.assertEqual([r["teamId"] for r in compute._leaders(rows, "v")],
                         [2, 7])
        self.assertEqual([r["teamId"]
                          for r in compute._leaders(rows, "v", reverse=False)],
                         [9])

    def test_leaders_ignores_rows_missing_the_stat(self):
        rows = [{"teamId": 1, "v": None}, {"teamId": 2, "v": 3}]
        self.assertEqual(compute._leaders(rows, "v"), [{"teamId": 2, "v": 3}])
        self.assertEqual(compute._leaders([{"teamId": 1, "v": None}], "v"), [])

    def test_a_shared_award_names_both_owners_and_is_flagged(self):
        # Every team identical every week -> every award is a 12-way tie.
        weeks = {w: week_games([100.0] * 12, week=w) for w in range(1, 4)}
        season = compute.build_standings(make_raw(weeks), UPDATED)
        awards = compute.build_season_stats(season)["awards"]
        self.assertTrue(awards)
        for a in awards:
            self.assertTrue(a["shared"], a["key"])
            self.assertIn("&", a["owner"])

    def test_a_clear_winner_is_not_flagged_as_shared(self):
        season = compute.build_standings(
            make_raw(full_season_weeks()), UPDATED)
        by_key = {a["key"]: a for a in compute.build_season_stats(season)["awards"]}
        self.assertFalse(by_key["wall"]["shared"])
        self.assertEqual(by_key["wall"]["owner"], "First12 Last12")
