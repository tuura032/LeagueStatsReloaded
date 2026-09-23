# Roadmap — bugs, polish, and fun stuff

A full pass over the current build (post-L9). Ranked by category, sized by
effort (XS/S/M/L) and payoff (Low/Med/High/🔥). Nothing here is committed to —
it's a menu, not a backlog. Picks at the bottom.

---

## Shipped since this was written (verified against the code, 2026-09-22)

- **B1, B2** — playoffs "Wins to Clinch" hardcoding and "Games Back" sign fixed (`728f420`)
- **B6** — dead "Week N Scores" block deleted during the `home.html` rewrite
- **F1 Luck Index + F5 Streaks** — standings page (`728f420`)
- **F2 Rivalry matrix** — new Rivalries page, all-time head-to-head grid (`b42a3ef`)
- **F9 All-time leaderboard** (absorbed F8's career-stats half) — new Career Stats page (`119c5dd`), now sortable (`f76b1d6`)
- **F10 On-the-bubble indicator** — playoff-line divider row on the standings table (`f76b1d6`)
- **U1 Highlight my row** — click-to-pin a row, remembered via `localStorage` (`f76b1d6`)
- **U2 Color H2H/Top-Six cells** — green/red tint by whether the owner is above or below 50% that stat (`f76b1d6`)
- **U6 Dark mode** — system preference + manual toggle (`642ab05`)
- **U3 Mobile pass** (partial→done) — nav bug fixed, full responsive redesign came with the Tailwind rewrite
- **M1 Modernization** — full Tailwind CSS rewrite, Bootstrap 4/jQuery/Popper dropped entirely (`4efac06`)
- Bonus, found along the way: `build.py`'s static-file copy no longer leaves stale orphans behind (`4efac06`); the Playoffs table also got click-to-sort for parity with Home/Career Stats (`9fc6699`)

Rows below marked **DONE** are confirmed shipped and kept only for history — treat
everything still marked open as the real to-do list.

**2026-09-22 bug sweep.** An outside consult (`BENCH_POINTS.md`) found five
defects that were not on this list, all now fixed and written up as BUG-003
through BUG-007 in `BUGS.md`: the site credited the **wrong champion** (weeks
15-17 were discarded, so "Titles" silently meant regular-season #1 — four of
five stars named the wrong owner); click-to-sort was **dead on the Home page**;
the Stats chart rendered as a **filled blob** with throwing tooltips;
`score_to_beat()` hardcoded a 12-team field; and leading an unfinished season
counted as a title. Same pass closed B3, B4, B5, U4, U7, M3, Q1, Q3 and Q5.

---

## 1. Bugs (real, found while reading the templates)

| # | Where | What's wrong | Effort | Payoff | Status |
|---|---|---|---|---|---|
| B1 | `playoffs.html` | "Wins to Clinch" hardcoded a 12-team league. | XS | Med | **DONE** |
| B2 | `playoffs.html` | "Games Back" rendered negative for everyone but the leader. | XS | Med | **DONE** |
| B3 | `playoffs.html` | Week columns unguarded — rendered "Week -1 / Week 0" early season. | XS | Low | **DONE** 2026-09-22 |
| B4 | `playoffs.html` | Prize amounts hardcoded in the template. | S | Med | **DONE** 2026-09-22 — moved to `data/prizes.json`; header *and* body both loop it, and each prize names its own `award` so winners resolve by key, not column position |
| B5 | `home.html` | `avgLast3` rendered as an integer beside `averageScore`'s one decimal. | XS | Low | **DONE** 2026-09-22 — also fixed the same truncation on Playoffs week scores |
| B6 | `home.html` | Dead "Week N Scores" block, never populated by `build.py`. | XS | Low | **DONE** — deleted in the dead-link cleanup pass |

All six are now closed. The bugs that actually mattered were not in this
table — see the 2026-09-22 sweep note above and `BUGS.md` BUG-003..007.

---

## 2. UI / UX polish

| # | Idea | Effort | Payoff | Status |
|---|---|---|---|---|
| U1 | Highlight the current user's row in the standings table. | S | High | **DONE** — click-to-pin row, `localStorage`-remembered |
| U2 | Color the H2H/Top-Six cells green/red by whether the owner is over or under 50% that stat. | S | High | **DONE** |
| U3 | Mobile pass — responsive table reflow. | M | High | **DONE** — came with the Tailwind rewrite |
| U4 | Sortable columns undiscoverable. | XS | Low | **DONE** 2026-09-22 — "Click a column header to sort." on Home |
| U5 | Favicon/branding refresh — `static/fffIcon.png` is still referenced in `layout.html:26`, still the old placeholder. | XS | Med | Open |
| U6 | Dark mode via `prefers-color-scheme`. | S | Med | **DONE** |
| U7 | No preseason/empty state on `home.html` / `playoffs.html`. | XS | Low | **DONE** 2026-09-22 — both guard on `throughWeek == 0`; Playoffs also stops indexing `standings[0..2]` unguarded |

---

## 3. New stats & features — the fun part

Your data (`weeks[].games`, `weeks[].teams` with `h2h`/`topHalf`/`weekPoints`
per team per week) is already rich enough for all of this — none of it needs
a new ESPN call. This is the highest-payoff bucket because it's *content*,
not scaffolding — it's the stuff people actually screenshot into the group
chat.

| # | Idea | What it shows | Effort | Payoff | Status |
|---|---|---|---|---|---|
| F1 | **Luck Index** | H2H record vs. points-scored-relative-to-field. | S | 🔥 | **DONE** — standings page |
| F2 | **Head-to-head matrix / rivalry record** | All-time record between every owner pair. | M | 🔥 | **DONE** — new Rivalries page |
| F3 | **Matchup visualizer** | Per-week matchup cards: two teams, scores, a bar comparing them, W/L + top-half badges. Basically a "box score" page per week instead of just the aggregate table. Pairs well with F6. | M | High | Open |
| F4 | **Closest games & biggest blowouts** | Sort all-time (or season) matchups by margin — "closest game ever," "biggest blowout." Trivial once `games[]` is flattened across seasons; no new fetch needed. | S | High | Open |
| F5 | **Streaks** | Win/loss streak per owner, badge on standings. | S | High | **DONE** |
| F6 | **Weekly recap / "power rankings" blurb** | Auto-generated one-paragraph recap per week: top scorer, biggest upset, score-to-beat, week MVP. A templated (non-AI) fill-in-the-blank recap reads as "content" instead of "a spreadsheet." | M | High | Open |
| F7 | **Championship simulator** | Monte Carlo over remaining games for live playoff-odds %. Needs `compute.py` work, not just template work. | L | 🔥 | Open |
| F8 | **Owner profile / manager card page** | Per-owner page: career record across seasons, best/worst week ever, a fun "manager rating." Career Stats (F9, done) covers the aggregate-leaderboard half; a dedicated per-owner page (`player1.html` still exists, still has stray `</br>` tags — see M3) hasn't been built. | M | High | Open (partially covered by F9) |
| F9 | **All-time / dynasty leaderboard** | Aggregate totals across all seasons. | S | High | **DONE** — Career Stats page, now sortable |
| F10 | **"On the bubble" indicator** | Flag the teams at the playoff line. | XS | Med | **DONE** — playoff-line divider row |

Remaining open: F3, F4, F6, F7, F8. F4 (closest games/blowouts) is still the
cheapest "look what I found" content left on the list — pure derived data,
no new fetch, no `compute.py` changes needed if done as a template-side sort
over the existing `weeks[].games`.

---

## 4. Quality of life / dev experience

| # | Idea | Effort | Payoff | Status |
|---|---|---|---|---|
| Q1 | `data/raw-*.json` sensitivity review. | XS | Low | **DONE** 2026-09-22 — 354 distinct keys scanned across all 5 raw files, zero matching email/phone/address/token/auth/cookie/SWID patterns |
| Q2 | `__pycache__/*.pyc` in `.gitignore`. | XS | Low | **DONE** — `.gitignore` covers `__pycache__/` and `*.pyc` |
| Q3 | CI: run the tests, not just fetch→compute→build. | S | Med | **DONE** 2026-09-22 — test step runs *before* the fetch, so broken math never reaches production |
| Q4 | `build.py --check` mode that fails if `docs/` would change on a clean rebuild — catches template/data drift early. | S | Low | Open |
| Q5 | One-command task runner wrapping fetch/compute/build. | XS | Med | **DONE** 2026-09-22 — `tasks.py` (stdlib only). A Makefile was written first and discarded: `make` is not installed on the Windows dev box, and a runner you cannot run is not a runner |

---

## 5. Modernization (lower priority — it's static and it works)

| # | Idea | Effort | Payoff | Status |
|---|---|---|---|---|
| M1 | Drop Bootstrap 4/jQuery/Popper, modernize the stack. | L | Low | **DONE** — full Tailwind rewrite |
| M2 | Chart.js 2.7.1 → 4.x. | M | Low | Open — still 2.7.1, but the two *bugs* it was masking (fill-blob, 3.x tooltip API on a 2.x build) are fixed, and it now loads only on `graph.html`. Upgrading is a want, not a need |
| M3 | `player1.html`'s literal `</br></br></br></br>`. | XS | Low | **DONE** 2026-09-22 |

---

## 6. Scaling to more leagues

You mentioned this matters less than the fun UI stuff, so just the shape of
it: right now `league="877873"` and the owner-name mapping live in
`fetch.py`/`compute.py` args and ESPN's own team data — nothing is
FFF-specific in the templates themselves (they're already fully data-driven
per L5/L9). The real work is:

- A config file (`leagues.yaml` or similar) mapping league ID → display name
  → output path, so `build.py` produces `docs/<league-slug>/...` instead of
  assuming one league at the root.
- A landing page listing leagues, since right now the root *is* the one
  league's home page.
- ~~B1 above (the hardcoded `standings[6]`) needs fixing first~~ — done. As of
  2026-09-22 the playoff cut comes from `scheduleSettings.playoffTeamCount`
  (surfaced through `standings-<season>.json`) on both Home and Playoffs, and
  `score_to_beat()` derives the top-half boundary from the field size instead
  of hardcoding the 6th-lowest of 12 (BUG-006). The scoring math no longer
  assumes a 12-team league anywhere.
- Still league-specific: `LEAGUE_ID` in `fetch.py`/`compute.py`, and the
  literal string "Fantasy Football Fantasy" in 9 templates —
  `mSettings.settings.name` is already fetched and now carried on
  `standings-<season>.json` as `leagueName`, so the templates just need to
  use it.

This is genuinely a different, smaller project once the single-league site
is fun and finished — I'd sequence it last.

---

## My picks — what's next now (updated 2026-09-22 after the bug sweep)

Everything in sections 1, 2 (except U5) and 4 (except Q4) is closed. What is
left is features, not defects. Ranked:

1. **F4 Closest games / blowouts** — still the cheapest, highest-payoff item
   on the board. Pure derived data over `weeks[].games`.
2. **League Rules page** — new, and the biggest value-per-hour item found in
   the consult. `fetch.py` already downloads `mSettings` every morning and the
   site uses exactly one field from it (`matchupPeriodCount`); the rest is the
   whole rulebook — PPR, auction draft, $200 FAAB, 2 keepers, 6 playoff teams,
   trade deadline, $25 entry fee. No new call, no new data source.
3. **Team logos + abbreviations** — `teams[].logo` and `teams[].abbrev` are
   already in every raw file. Cosmetic, trivial, and the single biggest jump
   in perceived quality available.
4. **OG/meta tags** — this link gets pasted into the league chat weekly and
   currently unfurls as a bare URL.
5. **F6 Weekly recap**, then **F3 matchup visualizer**, then **F8 owner
   pages** (which would also give the dead "Owners" sidebar accordion
   somewhere to link to).
6. **F7 Championship simulator** — biggest payoff left, wants more of the
   season played out first.

Multi-league (section 6) is now genuinely unblocked: BUG-006 fixed the one
piece of *math* that assumed 12 teams, and `playoffTeamCount` is read from
the league's own settings instead of guessed. What remains is packaging —
league ID into config, the league name out of 9 templates, and
`docs/<league>/<season>/`.

---

## Previous picks (superseded, kept for history)

U1, U2, F1, F2, F5, F9, F10, M1 are all shipped — the earlier picks list is
mostly done. What's actually left, ranked:

1. **F4 Closest games / blowouts** — still the cheapest, highest-payoff item
   on the whole board. Pure derived data over `weeks[].games`, no new fetch,
   no `compute.py` change strictly required. Best group-chat content per
   unit of effort.
2. **B3, B4, B5** — three small, well-isolated template bugs, good work to
   queue up for a local model to chew on independently:
   - B3: guard the negative week-number columns in `playoffs.html`.
   - B4: move the hardcoded prize amounts out of `playoffs.html` into data
     (even a small `prizes.json` or a `--prizes` build arg).
   - B5: make `avgLast3` render with the same one-decimal precision as
     `averageScore` in `home.html`.
3. **Q3 CI test step** — add `python -m unittest test_compute` to
   `.github/workflows/update-standings.yml`. Cheap insurance, still missing.
4. **F3 Matchup visualizer** — per-week box-score cards; pairs with F6 if a
   real "content" page is wanted instead of just tables.
5. **U5 Favicon/branding refresh** — still the placeholder `fffIcon.png`.
6. Later, once weeks pile up: **F7 Championship simulator** — biggest single
   payoff left on the list, but wants more of the season played out first.

Good candidates to hand to a smaller/local model for unattended work: B3, B4,
B5, U5, Q3, Q4, Q5, M3 — all narrowly scoped, low-ambiguity, and don't touch
`compute.py`'s core logic. F3/F4/F6/F7/F8 need more judgment (data shape,
design decisions) and are better kept for a session with the owner.

Section 6 (multi-league) is unblocked now that B1 is fixed, but still makes
sense to sequence last, same reasoning as before.
