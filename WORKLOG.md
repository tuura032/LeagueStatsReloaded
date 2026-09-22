# Work log

One entry per session, newest last. See `SPEC.md` §0 for the working protocol
and §9 for the task list.

**Format:** task id, date, what changed, files touched, what was verified,
anything deferred or surprising.

---

## Task status

- [x] L1 — `fetch.py`
- [x] L2 — `compute.py` (tests mandatory)
- [x] L3 — De-Flask the templates
- [x] L4 — `build.py` static render
- [x] L5 — Data-drive sidebar + chart
- [x] L6 — Client-side table sorting
- [ ] L7 — GitHub Action + Pages
- [ ] L8 — README + cleanup
- [ ] L9 — Multi-season archive *(optional, not before L1–L8)*

---

## Entries

### 2026-09-18 — spec written

`SPEC.md` created. No code yet.

Context, for whoever picks this up: v1 (2018–19, Flask + Postgres + Heroku)
died when Heroku dropped free Postgres. The **frontend survived** and already
renders the dual-point scoring correctly — `home.html`'s table has H2H Wins and
Top Six Finishes columns. Only the data layer is being replaced.

Two things confirmed against the live 2025 data while writing the spec:

- Regular season is **14 weeks** (`regularSeasonMatchupPeriodCount`), so dual
  points stop after week 14. Weeks 15–17 are the playoff bracket.
- v1's `(week-1)*6 + matchup` indexing of `schedule` **breaks in the
  playoffs** — week 15 of 2025 has 7 entries, not 6. Filter on
  `matchupPeriodId` instead.

Open question for the league, not blocking L1–L2 but needed before launch: the
two tie rules in §1. Defaults are written and tested; they just need confirming.

**Next: L1.**

### 2026-09-18 — L1: fetch.py

Built `fetch.py` per §9 L1. Two ESPN calls (`mMatchupScore`, `mTeam`), 1s apart,
written verbatim to `data/raw-<season>.json`. `--season` flag defaults to the
current year. No transform — the file is `{ "mMatchupScore": {...}, "mTeam": {...} }`,
each value the unmodified ESPN response. A non-200 (e.g. a missing season → 404)
prints a clear message and exits 1.

**Files:** `fetch.py` (new); `data/raw-2025.json`, `data/raw-2026.json` (fetched
artifacts).

**Verified against the live API:**
- `--season 2025` → 181KB, 103 schedule entries (14×6 + 7 + 6 + 6), 12 teams.
  Sample matchup matches the §3 shape (`matchupPeriodId`, `home/away.teamId`,
  `totalPoints`).
- Default (no flag) → picks the current year (2026), fetches 775KB. Works.
- `--season 1999` → clean HTTP 404 message, exit code 1.

**Spec gaps found and resolved this session (logged in `BUGS.md`):**
1. `regularSeasonMatchupPeriodCount` (named in §1) **does not exist** in the ESPN
   API. The real key is `settings.scheduleSettings.matchupPeriodCount` (= 14 for
   2022–2025, confirmed live).
2. That settings object is **not in `mMatchupScore` or `mTeam`** — it's in
   `mSettings` (also `mMatchups` / `mPublicSchedule`).

Owner decided: add a third call. `fetch.py` now fetches `mSettings` too, so the
raw file carries the week count. `SPEC.md` §1 (key name), §3 (third view), and
§9 L1 (three calls) updated to match. Both bugs resolved. Re-fetched
`raw-2025.json` / `raw-2026.json` with all three views; `matchupPeriodCount` = 14
in both.

**Also this session (requested by the owner):** created `BUGS.md` and
`ENHANCEMENTS.md`. Tracked historical/multi-season data (L9) and the season-picker
dropdown in `ENHANCEMENTS.md`.

**Next: L2 — `compute.py`.** Unblocked. Read the regular-season length from
`mSettings.settings.scheduleSettings.matchupPeriodCount`. Not started.

### 2026-09-18 — L2: compute.py

Built `compute.py` per §9 L2. Reads `data/raw-<season>.json`, writes
`data/standings-<season>.json` per §1 and §5. Pure, no network. `--season`
flag defaults to the current year (mirrors `fetch.py`). Regular-season length
read from `mSettings.settings.scheduleSettings.matchupPeriodCount`, never
hardcoded. Schedule is grouped by `matchupPeriodId` — no arithmetic indexing
(§3 trap 1).

**Files:** `compute.py` (new), `test_compute.py` (new);
`data/standings-2025.json`, `data/standings-2026.json` (computed artifacts).

**Tests — 21, all passing** (`python -m unittest test_compute -v`). Stdlib
`unittest` only — no new dependency (§2 list is complete). Covers the four
mandatory scenarios: a normal week (STB = 6th-lowest, 12 points distributed),
an H2H tie (no point to either, `winner: null`, 5 H2H points that week), a
top-half boundary tie (6th/7th identical → neither gets the point, 5 top-half
points that week), and weeks 15–17 contributing nothing (output identical
with or without playoff weeks present). Plus: in-progress season
(`throughWeek` stops at the last complete week), §5 shape, sort order
(points desc, pointsFor desc), record format.

**Verified against the real raw files:**
- `--season 2025` → through week 14 of 14. Independently re-derived
  `h2hPoints` (from the raw `winner` field), `topHalfPoints` and `pointsFor`
  for all 12 teams with a separate one-off script — exact match on all three.
  Week 5 game 1v4 matches the §5 example (143.8 vs 117.4, winner 1).
- `--season 2026` → through week 1 of 14 (in progress; ESPN's
  `currentMatchupPeriod` is 2, only week 1 is decided). Week 1 contains a
  real boundary case: Sam Engsberg scored exactly the STB (104.2) and got no
  top-half point — the strictly-greater rule working on live data.

**Decisions made this session (flagged, none re-litigates §10):**
- `throughWeek` = last *contiguous complete* week (all 12 teams have a
  decided game), capped at `matchupPeriodCount`. Unplayed games are
  `winner: "UNDECIDED"` with 0.0 scores, so a week mid-play is incomplete,
  not a week of zeroes.
- A game counts as played when both sides have numeric `totalPoints` and the
  matchup is not `UNDECIDED`. Playoff byes (two of them in 2025 week 15)
  carry no `away` key at all — handled.
- `record` is computed from the regular-season schedule, not ESPN's
  `mTeam` record (which includes playoffs): `"W-L"`, or `"W-L-T"` when a
  team has ties.
- `owner` = primary owner's "First Last" from `mTeam.members` (fallback
  `displayName`); `name` = the team name.
- `avgLast3` = mean of the last up-to-3 weeks on hand (fewer early in a
  season). All scores/sums rounded to 1 decimal to keep git diffs clean.
- The §5 example's week-5 `scoreToBeat` (108.9) is illustrative; the real
  2025 week-5 STB is 112.1.

**Next: L3 — De-Flask the templates.** Not started.

### 2026-09-18 — L3: De-Flask the templates

De-Flasked `templates/` per §9 L3. Scope confirmed with the owner up front:
full variable mapping for `home.html` **plus** full de-DB of `playoffs.html`
(including the wins-to-clinch / games-back formulas and `mostpf`), since the
task's four listed names alone would leave the tables unrenderable from the
JSON.

**Files:** `templates/layout.html`, `templates/home.html`,
`templates/playoffs.html`. Nothing else touched; no new dependencies.

**The five lines in §4:**
- `layout.html:12` `url_for('static', filename='fffIcon.png')` → `static/fffIcon.png`
- `layout.html:18` `url_for('home')` → `index.html`
- `layout.html:97–103` `get_flashed_messages()` block deleted
- `home.html:144` `url_for('static', filename='js/hello.js')` → `static/js/hello.js`

**Variable mapping (DB name → JSON key):**
- `sortedbywin` → `standings`; `current_week` → `throughWeek`
- `info.total_wins` → `info.points` (v1's `total_wins` was H2H wins + top-6
  count, i.e. the dual-point total — confirmed in v1's `/update` route)
- `info.total_points` → `info.pointsFor`
- `info.wins` → `info.h2hPoints`; `info.top6` → `info.topHalfPoints`
- Average Score expression → `info.averageScore`; Avg Last 3 expression →
  `info.avgLast3`
- playoffs: wins-to-clinch → `standings[6].points`, games back →
  `standings[0].points`, Heating Up → `info.avgLast3 - info.averageScore`,
  `mostpf.owner` → `standings | sort(attribute='pointsFor', reverse=true) | first`
- playoffs per-week score columns: v1 indexed the DB row positionally
  (`info[current_week+3/4/5]` — the exact trap §3 warns about). Replaced with a
  small Jinja macro `weekScore(weeks, teamId, week)` that looks the score up in
  the JSON `weeks` array. Missing weeks (early season) render 0, as v1 did.

**Decisions / flags (none re-litigates §10):**
- playoffs' hardcoded `13` (the 2018–19 season length) → `regularSeasonWeeks`,
  per §1's read-from-the-API rule.
- Display formats preserved so the page looks identical: Avg Last 3 stays an
  integer (`| round | int`), playoffs week scores stay `| int`, and `| round`
  renders ints/floats exactly as v1's did (same filter, same expression shape —
  int input renders `8`, float input `8.0`, verified).
- Relative paths assume a flat `docs/` layout (HTML at the root, `static/` as a
  sibling). `build.py` (L4) must render/copy to match.
- `layout.html:10` (`href="/static/dashboard.css"`) is a pre-existing absolute
  path **not** in §4's five lines — left untouched; it will 404 on Pages until
  L4 addresses it.
- Deliberately not touched: home table header route links (`/total_wins`,
  `/h2h`, `/top6`, `/average_score`) are L6; sidebar owner names and the 2018
  Chart.js dataset are L5; home.html's `{% if welcome %}` and
  `{% if some_week %}` blocks stay guarded (render nothing unless passed) — the
  "view week" block is the future weekly-recap view, data available in `weeks`.
- `player1.html` has no Flask syntax but needs roster data that is not in
  `standings.json` → per §4, leave unrendered in L4. `weeklyupdate.html` /
  `welcome.html` are POST forms to Flask routes (admin concerns) — L4's
  rendering decision.

**Verified:** rendered both pages with Jinja2 3.1.6 against the real
`data/standings-2025.json` and `data/standings-2026.json` (one-off script,
deleted after running). 12/12 home-table rows match the JSON cell-for-cell in
both seasons; all six computed playoffs columns (wins-to-clinch, games back,
heating up, three week scores) independently re-derived and matched; prize row
(top-3 owners + most-PF owner) correct; no `url_for` / `get_flashed_messages` /
DB-shaped names anywhere in the rendered output (header route links aside —
L6). The 2026 file (throughWeek 1) exercises the missing-weeks edge case.

**Next: L4 — `build.py` static render.** Not started.

### 2026-09-18 — L4: build.py

Built `build.py` per §9 L4. Reads `data/standings-<season>.json`, renders
`templates/` to `docs/`, copies `static/` to `docs/static/`. Pure, no network.
`--season` flag defaults to the current year (mirrors `fetch.py` /
`compute.py`); clear error + exit 1 if the standings file is missing. Output
is deterministic (no timestamps in the HTML) so L7's commit-only-if-changed
works.

**Files:** `build.py` (new); `templates/layout.html:10` (one line — see
below); `docs/` (rendered artifacts: `index.html`, `playoffs.html`,
`static/`).

**One template line (explicit handoff from L3):** `layout.html:10`
`href="/static/dashboard.css"` → `static/dashboard.css`. L3's entry said it
"will 404 on Pages until L4 addresses it". Same kind of fix as §4's five
lines (server path → relative path). No other template changes — the
`git diff` of `templates/` is exactly L3's work plus this one line.

**Pages rendered:** `home.html` → `docs/index.html` (site root; the navbar
links to `index.html`) and `playoffs.html` → `docs/playoffs.html` (L3 fully
de-DB'd it and the JSON supports it completely). Context is the four JSON
keys verbatim — `standings`, `weeks`, `throughWeek`, `regularSeasonWeeks`;
no transform. `welcome` / `some_week` are not passed, so the guarded blocks
render nothing, as L3 left them.

**Pages not rendered (§4: "render only if the data supports them"):**
- `player1.html` — needs roster data that is not in `standings.json`
  (L3's note).
- `graph.html` — the chart page; its dataset is L5's to data-drive.
  Rendering it now would publish 2018 numbers as current.
- `weeklyupdate.html` / `welcome.html` — POST forms to Flask routes that no
  longer exist.
- `update.html` / `error.html` — §4: "can be dropped".

**Verified** (one-off script, deleted after running):
- Both seasons (2025, 2026): all 12 home-table rows match the JSON
  cell-for-cell in order; all seven playoffs cells per row (total wins,
  wins-to-clinch, games back, heating up, three week scores) independently
  re-derived and matched; prize row (top-3 owners + most-PF owner) correct.
- 2026 (throughWeek 1) exercises the early-season edge: Week -1 / Week 0
  columns render 0, clinch header reads 26.
- No `{{` / `{%` / `url_for` / `get_flashed_messages` / `/static/` anywhere
  in either rendered page; the CSS link is relative.
- `docs/static/` is byte-identical to `static/` (all 3 files).
- Determinism: two consecutive builds produce byte-identical output.

**Deferred / flagged (not L4's tasks):**
- Sidebar route links (`/`, `/playoffs`, `/data`, `/player/1..12`) and the
  2018 owner names remain — L5 (data-drive the sidebar).
- Table-header sort links (`/total_wins`, `/total_points`, `/average_score`,
  `/h2h`, `/top6`) — L6. Note L6's task text names four of these; the
  template has five (plus the `/` on the Rank header).
- home.html's mobile nav (`/`, `/playoffs`, `/stats`) and the week
  pagination (`/1`–`/13`) are dead route links **not assigned to any task in
  §9** — flagged for the owner. The pagination is the UI for the future
  weekly-recap view L3 anticipated.
- `docs/` is not cleaned before a build: `copytree(dirs_exist_ok=True)`
  overwrites but never deletes. No stale files exist today; if a page is
  ever removed from `PAGES`, its old file would linger.
- Local Windows quirk: the first `copytree` run hit a transient WinError 32
  (file in use, likely AV scanning a just-written file); the immediate
  re-run succeeded. Not expected on the Linux runner.

**Next: L5 — Data-drive the sidebar and chart.** Not started.

### 2026-09-21 — L5: Data-drive sidebar + chart

Data-driven the sidebar and chart per §9 L5. The owner delegated the
design decisions for this task ("modern UI/UX, you are the expert").

**Files:** `templates/layout.html` (sidebar, chart script, scoped
`<style>` block), `templates/graph.html` (rewritten chart page),
`build.py` (render graph.html, pass `season` + `active_page`, explicit
UTF-8), `docs/` (rendered artifacts — now includes `graph.html`).

**Sidebar (layout.html):**
- 12 hardcoded 2018 team names → loop over `standings`: rank number,
  owner name (primary), team name (secondary, muted), full names in a
  `title` tooltip. Rank order = standings order.
- Owner entries are deliberately **not links**: `player1.html` is
  unrendered (no roster data in standings.json), and 12 links to the
  same page would be worse than none. Re-link when team pages exist.
- Dead route links fixed: `/` → `index.html`, `/playoffs` →
  `playoffs.html`, `/data` → `graph.html`.
- Active nav state is now per-page: build.py passes `active_page`
  (the output filename) and the template marks the matching link
  `active`. 2018 hardcoded `active` on Home, which was wrong on the
  other pages.
- New component styles live in a scoped `<style>` block in
  layout.html's head — `static/dashboard.css` untouched per §0 (the
  task names layout.html, not static/).

**Chart (layout.html + graph.html):**
- 2018's hardcoded dataset (13 labels, 10 values) → rendered from
  `weeks`/`standings` in the template: one line per team, weekly
  points-for, labels `Wk 1..throughWeek`, emitted with Jinja's
  `tojson` (HTML-safe for `<script>` context).
- Top-3 teams (by rank) visible by default; the other 9 hidden and
  toggled via the legend — 12 lines at once is unreadable. Hint text
  on the page explains it.
- Okabe–Ito colorblind-safe 12-color palette, assigned by rank.
- Modern config: responsive canvas in a fixed-height wrapper (2018
  used fixed 900×380 attributes), 2px lines, small points, bottom
  legend with point styles, nearest-hover tooltips, light grid.
- The init is now guarded with `if (ctx)`: 2018's unguarded
  `new Chart(document.getElementById("myChart"), …)` ran on every
  page and threw a console error on pages without the canvas.
- The commented-out duplicate canvas in layout.html's main area
  deleted.

**graph.html (now rendered by build.py — L4's handoff):**
- 2018's hardcoded "Analysis" paragraph (2018 commentary, "More data
  to come") → four stat cards computed in the template from `weeks`:
  league average/week, highest-scoring week, lowest-scoring week,
  biggest single week (owner + week). All directly derived from
  standings.json — nothing invented.
- Canvas gets `role="img"` + `aria-label`; subtitle shows season and
  weeks covered from the JSON.

**build.py:**
- `graph.html` added to PAGES.
- Context gains `season` (from the JSON) and per-page `active_page`.
- **Latent bug found and fixed:** `write_text()` used the locale
  default encoding — cp1252 on this Windows box. Output declared
  `<meta charset="utf-8">` but was cp1252 bytes, so "Davíd Huisken"
  (2025) rendered as mojibake — this affected L4's 2025 output too.
  Read and write are now explicit `encoding="utf-8"`. (compute.py's
  JSON is unaffected: `json.dumps` is ASCII-only.)

**Verified** (one-off script, deleted after running):
- Both seasons: sidebar has all 12 owners + teams in rank order with
  ranks 1–12; no 2018 names, no `/player/`, no dead route links, no
  `url_for` / `/static/` / Jinja leftovers; exactly one active nav
  item, correct per page.
- `chartData` (extracted from the rendered HTML, `json.loads`): 12
  datasets, labels `Wk 1..N`, every team's weekly scores
  independently re-derived from the JSON `weeks` — exact match;
  hidden flag = rank ≥ 4; colors consistent.
- Stat cards independently re-derived (league avg, best/low week,
  biggest single week) — exact match.
- 2026 (throughWeek 1) edge: 1 label, 1 point per dataset, "1 week"
  (no plural), best = low = Wk 1.
- Output bytes valid UTF-8; "Davíd Huisken" intact.
- Inline chart script passes `node --check`.
- Determinism: two consecutive builds byte-identical (both seasons).

**Deferred / flagged (not L5's tasks):**
- home.html's mobile nav (`/`, `/playoffs`, `/stats`) and week
  pagination remain — still unassigned (L4's flag stands).
- Table-header sort links and `static/js/hello.js` / the "JS Table"
  demo — L6.

**Next: L6 — Client-side table sorting.** Not started.

### 2026-09-22 — L6: Client-side table sorting

Replaced the dead v1 sort route links with client-side column sorting
per §9 L6. The 2019 "new js table" commit (bb2267b) — the abandoned
attempt at this feature — is finished: the stub `static/js/hello.js`
now carries the sorter, and the standings table sorts on header click.

**Files:** `templates/home.html` (table id, headers, scoped `<style>`
block), `static/js/hello.js` (sorter; `myFunction` kept), `docs/`
(rendered artifacts — both seasons rebuilt, ends on 2026 as before).

**Standings table (home.html):**
- The six headers that carried dead route links (`/` on Rank,
  `/total_wins`, `/total_points`, `/average_score`, `/h2h`, `/top6`)
  are now plain `<th>`s with `class="sortable"` — §4's "keep the
  `<th>` elements, drop the `<a href>`". Owner and Avg Last 3 (no
  links in v1) stay plain.
- The table gets `id="standings-table"` so the JS can target it.
- Scoped `<style>` block (L5 precedent; `static/dashboard.css`
  untouched): cursor pointer, muted ↕ on sortable headers (replaces
  the lost link affordance), ▲/▼ on the active one. Arrows are CSS
  escapes (`\2195`/`\25B2`/`\25BC`), so the template stays ASCII.

**Sorter (static/js/hello.js):**
- Vanilla JS, no library, IIFE, guarded with `if (!table)` (L5's
  `if (ctx)` precedent).
- First click sorts **descending** — v1's server-side sorts were all
  DESC (`application.py:132–146`); a second click on the same header
  flips to ascending; clicking a different header starts descending
  again.
- Numeric sort (all six columns are plain numbers); ties keep the
  official standings order (each row's original position), so the
  result is the same no matter what was sorted before.
- The Rank cell is the team's official rank, not its row position —
  it travels with the team when rows move.
- `aria-sort` on the active header. The 2018 `myFunction()` (the
  "New Features" button) is kept, byte-for-byte.

**v1 quirk not replicated:** v1's `/average_score` route actually
sorted by `total_points` (shared branch, `application.py:136–137`).
v2 sorts Average Score by `averageScore`.

**Verified** (one-off scripts, deleted after running):
- Both seasons: no `<a>` left in the standings table; exactly six
  sortable headers in the right positions; all 12 owners present; no
  Jinja leftovers; valid UTF-8 ("Davíd Huisken" intact).
- The rendered `hello.js` passes `node --check`, then ran in node
  against a minimal fake DOM built from the rendered table: simulated
  clicks verified all six columns in both directions, the toggle
  behaviour, ties by rank — including a history-independence case
  where Average Score orders the H2H-8 group differently than rank —
  indicator/`aria-sort` state, Owner/Avg Last 3 inert (no handler),
  and rank cells staying with their team. Expected orders
  independently re-derived from the JSON.
- No L6 markers in playoffs.html / graph.html.
- Determinism: two consecutive builds byte-identical (both seasons).
- `docs/static/js/hello.js` byte-identical to `static/js/hello.js`.

**Deferred / flagged (not L6's tasks):**
- The 2019 "JS Table" demo (dummy "Row 1, Coloumn 1" data) and the
  "New Features" / Hello World button remain — the author's 2018
  work, and the task does not ask for their removal. The sorter
  targets only `#standings-table`. For the owner to decide (L8
  cleanup?).
- home.html's mobile nav (`/`, `/playoffs`, `/stats`) and week
  pagination (`/1`–`/13`) remain dead route links — unassigned (L4's
  flag stands).
- Sort headers are click-only (no keyboard access); v1's links were
  keyboard-focusable. Possible future a11y enhancement.

**Next: L7 — GitHub Action + Pages.** Not started.

### 2026-09-22 — Repo re-baseline (L7 prerequisite)

New repo `tuura032/LeagueStatsReloaded` created. The first push of the
full clone was **blocked by GitHub Push Protection**: secret scanning
flagged the Heroku Postgres URL in `application.py` across the 2018
commits — the dead credential §8 had already documented.

**Owner decision (supersedes §8's "history comes with it"):** start
fresh. The 2018–19 history does not ride into the new repo; it stays
intact in the private `tuura032/LeagueStats`. A fresh baseline also
removes the push-protection problem at the root — the secret never
enters the new repo's history. No fork, no history rewrite: re-`git
init` in place (local `master` was exactly at the old `origin/master`,
no stashes, nothing unpushed).

**Done:**
- Secret-scanned the working tree: the Postgres URL was the only
  credential (other hits: prose, and the 2018 `#secretnav` CSS id).
- Deleted per §8: `application.py`, `getApiData.py`, `Procfile`,
  `__pycache__/` (all preserved in the private repo).
- `requirements.txt` shrunk to `requests` + `jinja2` (§2/§8 line, done
  at re-baseline so the L7 workflow doesn't install dead Flask deps).
- Minimal `.gitignore` (`__pycache__/`, `*.pyc`) so the pycache Python
  recreates can't ride into a `git add -A`.
- `SPEC.md` §8 updated to record the fresh-history decision.
- Fresh `git init -b main` + one baseline commit of the v2 tree.

**Remaining (owner's terminal):**
`git remote add origin https://github.com/tuura032/LeagueStatsReloaded.git`
then `git push -u origin main`.

**Next: L7 — GitHub Action + Pages.** Not started.
