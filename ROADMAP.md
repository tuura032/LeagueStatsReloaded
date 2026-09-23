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
everything still marked open as the real to-do list. `BUGS.md` has nothing open;
its entries were build-time spec gaps (L1/L2), unrelated to the bugs tracked here.

---

## 1. Bugs (real, found while reading the templates)

| # | Where | What's wrong | Effort | Payoff | Status |
|---|---|---|---|---|---|
| B1 | `playoffs.html` | "Wins to Clinch" hardcoded a 12-team league. | XS | Med | **DONE** |
| B2 | `playoffs.html` | "Games Back" rendered negative for everyone but the leader. | XS | Med | **DONE** |
| B3 | `playoffs.html:47-49` | The 3 week columns are still `Week {{ throughWeek - 2 }}` / `- 1` / `{{ throughWeek }}`, unguarded. At week 1 this renders "Week -1 / Week 0 / Week 1" on the live page. | XS | Low | Open |
| B4 | `playoffs.html:80-87` | Prize amounts ($25/$20/$15/$30/$90/$60/$30/$30) are still hardcoded in the template header text. Any year the pot changes, this is a template edit instead of a data edit. | S | Med | Open |
| B5 | `home.html:77-78` | `avgLast3` still renders `| round | int` (integer) while `averageScore` on the same row renders its raw one-decimal value. Inconsistent precision on adjacent columns. | XS | Low | Open |
| B6 | `home.html` | Dead "Week N Scores" block, never populated by `build.py`. | XS | Low | **DONE** — deleted in the dead-link cleanup pass |

B3/B4/B5 are the real remaining bugs — all small, well-isolated template edits, good candidates to hand off.

---

## 2. UI / UX polish

| # | Idea | Effort | Payoff | Status |
|---|---|---|---|---|
| U1 | Highlight the current user's row in the standings table. | S | High | **DONE** — click-to-pin row, `localStorage`-remembered |
| U2 | Color the H2H/Top-Six cells green/red by whether the owner is over or under 50% that stat. | S | High | **DONE** |
| U3 | Mobile pass — responsive table reflow. | M | High | **DONE** — came with the Tailwind rewrite |
| U4 | The sortable-column arrows are nice but undiscoverable — add a one-line "click a header to sort" hint, or a subtle affordance on load. | XS | Low | Open — no hint text found anywhere in the templates |
| U5 | Favicon/branding refresh — `static/fffIcon.png` is still referenced in `layout.html:26`, still the old placeholder. | XS | Med | Open |
| U6 | Dark mode via `prefers-color-scheme`. | S | Med | **DONE** |
| U7 | Loading/empty states for week 0 (preseason) — `graph.html` has a "No weeks of data yet." fallback; `home.html` and `playoffs.html` still have no such guard and would render zeros/blank rows before week 1 posts. | XS | Low | Open |

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
| Q1 | `data/raw-*.json` sensitivity review — double-check nothing sensitive sneaks in as data grows. | XS | Low | Open (never actually re-checked, just low-risk) |
| Q2 | `__pycache__/*.pyc` in `.gitignore`. | XS | Low | **DONE** — `.gitignore` covers `__pycache__/` and `*.pyc` |
| Q3 | CI: run `python -m unittest test_compute` on every push, not just locally. | S | Med | Open — `.github/workflows/update-standings.yml` only runs fetch→compute→build, no test step |
| Q4 | `build.py --check` mode that fails if `docs/` would change on a clean rebuild — catches template/data drift early. | S | Low | Open |
| Q5 | One-command task runner (`Makefile`/`justfile`) wrapping fetch/compute/build. | XS | Med | Open |

---

## 5. Modernization (lower priority — it's static and it works)

| # | Idea | Effort | Payoff | Status |
|---|---|---|---|---|
| M1 | Drop Bootstrap 4/jQuery/Popper, modernize the stack. | L | Low | **DONE** — full Tailwind rewrite |
| M2 | Chart.js 2.7.1 → 4.x. | M | Low | Open — `layout.html` still loads `Chart.js/2.7.1` from cdnjs |
| M3 | `player1.html`'s `</br></br></br></br>` (literal) — cosmetic leftover, fix whenever that page gets built out (F8). | XS | Low | Open — page is still unrendered so it's invisible, but the stray tags are still there |

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
- B1 above (the hardcoded `standings[6]`) needs fixing first — it's the one
  piece of template logic that silently assumes "12 teams," which won't hold
  across leagues.

This is genuinely a different, smaller project once the single-league site
is fun and finished — I'd sequence it last.

---

## My picks — what's next now (updated 2026-09-22, re-verified against the code)

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
