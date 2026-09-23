# Bugs

Defects to work through. Newest last. See `SPEC.md` §0 for the working protocol
and §9 for the task list.

**Format:** id, date, title, where found, what's wrong, impact, resolution (once
fixed), status.

> Build-blockers are listed here too (clearly marked) so they are not lost —
> even though this file is mainly for working through after the build.

---

## Open

_None._

## Resolved

### BUG-008 — The season picker threw away the page you were on

- **Date:** 2026-09-22
- **Found in:** `templates/layout.html`, reported by the owner
- **What's wrong:** each option linked at the season's *directory*
  (`2025/`), which resolves to that season's `index.html`. Switching year
  from Playoffs dumped you on Home and you had to navigate back — worst for
  exactly the thing you change year for, comparing one page across seasons.
- **Resolution:** the option now appends `active_page`, so Playoffs → 2025
  lands on 2025's Playoffs.
- **Also fixed here (latent):** links were built off `current_season` (the
  calendar year) rather than `root_season` (the newest season *with data*,
  which is what `build.py` puts at the site root). Those differ every
  off-season, and when they do the root season's option pointed at a
  `<year>/` subdirectory that was never written. Nobody had hit it yet
  because the two have coincided all season.
- **Status:** resolved 2026-09-22.

### BUG-009 — Past seasons led with the regular season and buried the result

- **Date:** 2026-09-22
- **Found in:** `templates/home.html` / `playoffs.html`, reported by the owner
  ("for historical years I care about overall winner and final standings just
  as much, maybe more than regular season. The UX doesn't make sense for that")
- **What's wrong:** a finished season's Home page was headed "2025 Standings
  Through Week 14" and showed only the dual-point regular-season table. Who
  won the league was not on the page at all, and final placings existed
  nowhere on the site.
- **Impact:** the site could not answer the main question you ask a league
  archive — how did that season end.
- **Resolution:** `rankCalculatedFinal` (already in the `mTeam` payload,
  unused) is carried through as `finalRank`. A completed season's Home page
  now opens with a champion banner linking to the bracket, and the standings
  table gains a sortable **Finish** column beside the regular-season Rank.
  The Playoffs page gained a full **Final Standings** table (1..12, across
  playoffs and both consolation ladders), above the now clearly-labelled
  "Regular Season Seeding" table. Both are hidden mid-season.
- **Note on the league's rules:** FFF reseeds the playoffs by hand off the
  dual-point standings, so ESPN's `teams[].playoffSeed` does *not* describe
  the real bracket (2025 lists Sharp 3rd / Huisken 4th; the bracket ran
  Huisken as the 3 seed). `rankCalculatedFinal` is computed from results, so
  it survives the manual reseed — cross-checked against the winners bracket
  for 2022–2025, where rank 1 is the final's winner every time.
  **Do not use `playoffSeed`.**
- **Status:** resolved 2026-09-22.

### BUG-003 — Career Stats credited the title to the wrong owner

- **Date:** 2026-09-22
- **Found in:** `compute.py:build_career_stats`, surfaced during the
  `BENCH_POINTS.md` consult
- **What's wrong:** `compute.py` stopped at `matchupPeriodCount` and discarded
  weeks 15-17 entirely, so the site had no concept of a playoff result. The
  Career Stats "Titles" column counted **regular-season #1 finishes** and
  presented them as titles. The winners' bracket was in `data/raw-*.json` the
  whole time, tagged `playoffTierType: WINNERS_BRACKET`.
- **Impact:** four of the five stars on the live page named the wrong owner.
  2025's went to Casey Pirsig, who lost the final to Davíd Huisken 154.5-108.9.
  Real champions: Nicholas Polansky (2022), Daniel Sharp (2023), Pat Benner
  (2024), Davíd Huisken (2025).
- **Resolution:** `build_playoffs()` parses the winners' bracket and returns
  champion / runner-up / bracket games / playoff points-for. `standings-*.json`
  gains a `playoffs` key (None until a final is decided). Career Stats now has
  separate **Titles** (championships, with the years on hover) and **Reg #1**
  columns, and the Playoffs page shows a champion banner. 15 new tests.
- **Status:** resolved 2026-09-22.

### BUG-004 — Click-to-sort silently dead on the Home page

- **Date:** 2026-09-22
- **Found in:** `static/js/hello.js`
- **What's wrong:** the playoff-line divider is a `<tr>` with a single
  `<td colspan="10">`. The sorter iterated every row in the tbody and indexed
  `a.cells[col]`, which is `undefined` for that row, so the comparator threw
  `TypeError` and the exception propagated out of `Array.sort` — aborting the
  click handler before it reordered rows *or* set the sort arrow.
- **Impact:** headers on the site's main page looked interactive and did
  nothing, with no visible error. Careers and Playoffs were unaffected (no
  divider row), so it tested clean unless Home was clicked specifically.
- **Resolution:** rows narrower than the header row are treated as decoration:
  excluded from the sort, and re-inserted only while the data is in its
  original order (a "top 6 make it" line is a lie once the table is re-sorted
  by Points For). Headers also became keyboard-operable.
- **Status:** resolved 2026-09-22.

### BUG-005 — The Stats chart rendered as a solid blob, and its tooltips threw

- **Date:** 2026-09-22
- **Found in:** `templates/layout.html`
- **What's wrong:** two separate defects in the same script. (1) Chart.js 2.x
  defaults line datasets to `fill: true`, and each dataset set
  `backgroundColor`, so every series painted a filled area to the axis instead
  of a line. (2) The tooltip callback used `item.dataset.label` — the Chart.js
  **3.x** API — on Chart.js 2.7.1, where it is `undefined`, so every hover
  threw and no tooltip ever appeared.
- **Impact:** the Stats page was unreadable and un-hoverable.
- **Resolution:** `fill: false` on every dataset; tooltip callback rewritten
  against the 2.x `(item, data)` signature. Chart.js is also now loaded only on
  `graph.html` (the only page with a `<canvas>`) instead of all five.
- **Status:** resolved 2026-09-22.

### BUG-006 — `score_to_beat()` hardcoded a 12-team league

- **Date:** 2026-09-22
- **Found in:** `compute.py:score_to_beat`
- **What's wrong:** `sorted(scores)[5]` — the 6th-lowest — is "top half" only
  for 12 teams. Ported verbatim from v1's `getScoresToBeat()`.
- **Impact:** latent. Correct for FFF, and silently the wrong scoring rule for
  any other league size — i.e. it would have broken the one thing this project
  exists to compute the moment it was pointed at a second league.
- **Resolution:** `sorted(scores)[len(scores) // 2 - 1]`, identical at n=12.
  Odd fields round the top half up. Tests cover 8/10/11/12-team leagues.
- **Status:** resolved 2026-09-22.

### BUG-007 — Leading an unfinished season counted as a regular-season title

- **Date:** 2026-09-22
- **Found in:** `compute.py:build_career_stats`
- **What's wrong:** `if row["rank"] == 1` ran for every season on file,
  including the in-progress one, so whoever led in week 2 of 2026 was credited
  with a finish.
- **Impact:** Jamie Sugar showed a career regular-season title two weeks into
  the season.
- **Resolution:** only counted when `throughWeek == regularSeasonWeeks`.
- **Status:** resolved 2026-09-22.

### BUG-001 — Spec gap: `regularSeasonMatchupPeriodCount` does not exist *(BLOCKER for L2)*

- **Date:** 2026-09-18
- **Found in:** `SPEC.md` §1, while building L1 (`fetch.py`)
- **What's wrong:** §1 says to read the regular-season week count from
  `settings.scheduleSettings.regularSeasonMatchupPeriodCount`. That key does not
  exist in the ESPN API. The real key is
  `settings.scheduleSettings.matchupPeriodCount` — confirmed live, it is **14**
  for every season 2022–2025 (matches the spec's "currently 14").
- **Impact:** L2 (`compute.py`) cannot read the week count from the path the spec
  names. It must use `matchupPeriodCount` instead.
- **Resolution:** correct the key name in `SPEC.md` §1 and use `matchupPeriodCount`
  in `compute.py`.
- **Status:** resolved 2026-09-18 — `SPEC.md` §1 corrected to `matchupPeriodCount`;
  confirmed = 14 for 2022–2025.

### BUG-002 — Spec gap: week count is not in the two views L1 fetches *(BLOCKER for L2)*

- **Date:** 2026-09-18
- **Found in:** `SPEC.md` §3 / §9 (L1), while building L1 (`fetch.py`)
- **What's wrong:** L1 fetches only `mMatchupScore` and `mTeam`. Neither response
  contains a `settings` object at all. The `settings.scheduleSettings` object (with
  `matchupPeriodCount`) lives in `mSettings` (also present in `mMatchups` and
  `mPublicSchedule`). So `data/raw-<season>.json` as spec'd does **not** contain
  the regular-season week count that L2 needs.
- **Impact:** L2 has no source for the regular-season length unless the fetch also
  captures a settings-bearing view.
- **Proposed resolution (needs a decision):** add a third call (`mSettings`) to
  `fetch.py` so the raw file carries the week count — or derive the length another
  way. L1 was built to the spec's two views exactly; a third view was not added
  without a decision.
- **Status:** resolved 2026-09-18 — owner approved a third call; `fetch.py` now
  fetches `mSettings` and the raw file carries the week count. `SPEC.md` §3/§9
  updated to match.
