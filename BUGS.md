# Bugs

Defects to work through. Newest last. See `SPEC.md` §0 for the working protocol.

**Format:** id, date, title, where found, what's wrong, impact, resolution (once
fixed), status.

---

## Open

_None._

## Resolved

One line each (full write-ups: git history, 2026-09-18 → 2026-09-22).

- **BUG-001** (2026-09-18) — spec named a nonexistent key →
  `matchupPeriodCount` (SPEC.md §1 corrected).
- **BUG-002** (2026-09-18) — week count not in the fetched views → third call
  (`mSettings`) added to `fetch.py`.
- **BUG-003** (2026-09-22) — Career Stats credited the title to the wrong
  owner (weeks 15–17 discarded) → `build_playoffs()` parses the winners'
  bracket; separate **Titles** / **Reg #1** columns.
- **BUG-004** (2026-09-22) — click-to-sort dead on Home (colspan divider row
  threw in the comparator) → narrow rows treated as decoration; headers
  keyboard-operable.
- **BUG-005** (2026-09-22) — Stats chart rendered a filled blob and tooltips
  threw (3.x API on Chart.js 2.x) → `fill: false`, 2.x callback; Chart.js only
  on graph.html.
- **BUG-006** (2026-09-22) — `score_to_beat()` hardcoded a 12-team field →
  `sorted(scores)[len(scores) // 2 - 1]`; tests cover 8–12 teams.
- **BUG-007** (2026-09-22) — leading an unfinished season counted as a
  regular-season title → only counted when `throughWeek == regularSeasonWeeks`.
- **BUG-008** (2026-09-22) — season picker threw away the page you were on →
  options append `active_page`; links built off `root_season`, not
  `current_season`.
- **BUG-009** (2026-09-22) — past seasons buried the result → champion banner,
  sortable **Finish** column, **Final Standings** table. **Standing rule:** the
  league reseeds the playoffs by hand, so ESPN's `playoffSeed` is wrong — use
  `rankCalculatedFinal`.
