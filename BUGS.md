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
