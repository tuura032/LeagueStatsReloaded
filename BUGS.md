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
