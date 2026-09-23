# Enhancements

The live backlog. Newest last within each section. See `AGENTS.md` for the
working protocol. Superseded `ROADMAP.md` and `BENCH_POINTS.md` — their still
-open findings are folded in below (2026-09-23); the rest is git history.

**Format:** id, description, why it's easy (data already on hand, if true),
status.

---

## Open — content & features

- **ENH-003** — Matchup visualizer: per-week box-score cards (two teams,
  scores, a bar, W/L + top-half badges). Pairs with ENH-004.
- **ENH-004** — Weekly recap: auto-generated, deterministic (not AI) recap —
  top scorer, biggest upset, score to beat, who got unlucky/backed in. Fully
  computable from `weeks[]`, already stored.
- **ENH-005** — League Rules page from `mSettings` — PPR scoring, auction
  draft, 2 keepers, FAAB, playoff seeding, trade deadline, entry fee.
  `fetch.py` already downloads this every morning; nothing renders it.
- **ENH-006** — Team logos + abbreviations — `teams[].logo` and
  `teams[].abbrev` are already in every raw file, unused.
- **ENH-007** — Owner profile pages (`/owner/<name>`) — career arc,
  best/worst weeks, full H2H list. Career Stats covers the aggregate half;
  the "Owners" sidebar accordion currently expands to a dead end with no
  pages to link to — build this or cut the accordion.
- **ENH-008** — Championship / playoff-odds simulator. Wants more of the
  season played out first; biggest remaining payoff on the list.
- **ENH-009** — Small free wins already sitting in `mTeam`/`mSettings`, no
  new fetch: `transactionCounter` → "Most Active Manager" / FAAB-spent
  awards; `draftDayProjectedRank` vs `currentProjectedRank` → riser/bust;
  `teams[].eliminated` → an "eliminated" badge.
- **ENH-010** — Records book / power rankings / head-to-head compare view —
  lower priority than ENH-003/004, same "content, not scaffolding" bucket.
- **ENH-011** — Rank-movement arrows using git history (diff this week's
  `standings-<season>.json` against last week's commit). Cheap, high
  perceived-liveness.
- **ENH-012** — `mRoster` endpoint for lineup-level data: literal bench
  points, optimal-lineup regret. The one item here that's a genuinely new
  capability, not just unused existing data — needs a new fetch call.

## Open — polish & UX

- **ENH-013** — Favicon/branding refresh — `static/fffIcon.png` is still the
  2018 placeholder.
- **ENH-014** — OG/social meta tags + a preview image — the link gets pasted
  into the league chat weekly and unfurls as a bare URL.
- **ENH-015** — "Last updated" stamp — `standings-<season>.json` carries
  `updated`; no template renders it.
- **ENH-016** — Mobile pass 2: fade/scroll affordance on tables that overflow
  right, sticky table headers, rivalry matrix rethink for mobile (pick an
  owner → ranked list of their H2H records, not a 12×12 grid), consistent nav
  labels between desktop and mobile ("Stats" vs "Careers" vs full names).
- **ENH-017** — Accessibility: wrap sort `<th>` labels in a `<button>` so
  they're keyboard-reachable; add a non-color cue to the red/green H2H/rivalry
  heatmaps; give the pinned-row click target a `role` and focus style.
- **ENH-018** — Vendor/pin Chart.js and upgrade off 2.7.1 (currently 9 years
  old, loaded on every page though only `graph.html` uses it).

## Open — quality of life / dev experience

- **ENH-019** — `build.py --check` mode: fail if `docs/` would change on a
  clean rebuild. Catches template/data drift early.

## Open — multi-league

The app is a handful of hardcoded constants away from supporting more than
one league — most of the values it needs are already in the fetched JSON:

- League ID (`fetch.py`/`compute.py`) and the literal league name (9
  templates) → config + `mSettings.settings.name` (already fetched, just
  unused for this).
- `docs/<league>/<season>/` layout + a league picker next to the season
  picker.
- A `leagues.yml` mapping league ID → display config, looped the same way
  seasons already are (L9 pattern, one level up).

Sequence this last — it's real work but lower payoff than the content/UX
items above, and every piece unblocking it (playoff-count-from-settings, no
more 12-team hardcoding) is already done.

## Explicitly not building

From the 2026-09-22 outside consult — recorded so it doesn't get
re-litigated: a database (see `SPEC.md` §6), a JS framework, user
accounts/login, live in-game scoring, ESPN-beating projections, or unit tests
for template rendering (the screenshot baseline is the right tool for that).

---

## Done

- **ENH-001** — Historical / multi-season data — done 2026-09-22 (L9).
  Archive now covers 2019–2026; newest season with data is the site root.
- **ENH-002** — Season picker (dropdown to select league year) — done
  2026-09-22 (L9). Picker macro in `templates/layout.html`; options keep the
  current page and are built off `root_season` (BUG-008).
- **ENH-020** — Stat help bubbles + mobile column visibility — done
  2026-09-23. "?" bubbles beside Home/Playoffs stat headers explain each
  stat (hover on desktop, tap/keyboard on mobile); H2H Wins and Top Six
  Finishes no longer hidden on small screens; Playoffs "Week N" renamed
  "Most Recent". The tip is a JS-positioned floating div clamped to the
  viewport — a pure-CSS ::after tip clipped at the table's overflow
  container edge on phones.

For everything else shipped before 2026-09-23 (dual-point stats page, luck
index, rivalries, career stats, dark mode, Tailwind rewrite, real champions
from the playoff bracket, prize/payout split, etc.) — see `git log` and
`WORKLOG.md`; the old `ROADMAP.md` narrative tracking all of that by hand is
retired as of this consolidation.
