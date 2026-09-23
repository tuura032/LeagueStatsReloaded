# Roadmap — bugs, polish, and fun stuff

A full pass over the current build (post-L9). Ranked by category, sized by
effort (XS/S/M/L) and payoff (Low/Med/High/🔥). Nothing here is committed to —
it's a menu, not a backlog. Picks at the bottom.

---

## 1. Bugs (real, found while reading the templates)

| # | Where | What's wrong | Effort | Payoff |
|---|---|---|---|---|
| B1 | `playoffs.html:40` | "Wins to Clinch" reads `standings[6].points` — hardcodes a 12-team league. Breaks (wrong number, not a crash) the moment a league isn't exactly 12 teams. Same problem for "scale to more leagues" later. | XS | Med |
| B2 | `playoffs.html:41` | "Games Back" computes `info.points - standings[0].points`, which is **negative** for everyone but the leader (see screenshot: -1, -2, -3...). Standard fantasy UI shows this as a positive magnitude ("2.0 GB"). Right now it reads like a penalty, not a gap. | XS | Med |
| B3 | `playoffs.html:28-45` | The 3 week columns are `throughWeek-2 .. throughWeek`, unguarded. At week 1 this renders "Week -1 / Week 0 / Week 1" — negative week numbers on the actual page early in the season. | XS | Low |
| B4 | `playoffs.html:62-69` | Prize amounts ($25/$20/$15/$30/$90/$60/$30/$30) are hardcoded in the template. Any year the pot changes, this is a template edit instead of a data edit. | S | Med |
| B5 | `home.html:81` vs `:79-80` | `avgLast3` is rounded to an int (`176`) while `averageScore`/`pointsFor` show one decimal (`134.0`). Inconsistent precision on adjacent columns in the same row. | XS | Low |
| B6 | `home.html:90-116` | The "Week N Scores" block (`some_week`/`week_scores`/`score_counter`) is never populated by `build.py` — it's dead template code left over from the Flask version. Either wire it up or delete it. | XS | Low |

None of these are urgent — the site works — but B1/B2 are the two to fix before you show this to anyone who'll actually stare at the playoffs page.

---

## 2. UI / UX polish

| # | Idea | Effort | Payoff |
|---|---|---|---|
| U1 | Highlight the current user's row (e.g. "Paul Tuura") in the standings table — sticky/bold row so you find yourself instantly instead of scanning. Could be a `localStorage`-remembered "my team" picker so it works for everyone, not just you. | S | High |
| U2 | Color the H2H/Top-Six/points cells — green tint for "earned the point that week," red/gray for missed — turns the dense number grid into something scannable at a glance. | S | High |
| U3 | Mobile pass: `#secretnav` in `home.html` is a workaround for the sidebar being `d-none` under 768px — works, but the table itself doesn't reflow well on phones (12 rows × 8 columns in `table-responsive` means a lot of sideways scrolling on a phone, which is exactly the device your league mates will check standings from on a Sunday). Card-style rows on mobile would read much better. | M | High |
| U4 | The sortable-column arrows (`home.html` inline `<style>`) are nice but undiscoverable — add a one-line "click a header to sort" hint, or a subtle affordance on load (auto-flash the default sort column). | XS | Low |
| U5 | Favicon/branding refresh — `fffIcon.png` is presumably an old placeholder; a proper league logo/mascot would go a long way for "fun app my league wants to visit." | XS | Med |
| U6 | Dark mode via `prefers-color-scheme` — cheap now since it's all Bootstrap variables + a small custom stylesheet, much more annoying to retrofit later. | S | Med |
| U7 | Loading/empty states — `graph.html` already has a "No weeks of data yet" fallback; extend the same care to `playoffs.html` and `home.html` for week 0 (preseason) so the site doesn't look broken before week 1 posts. | XS | Low |

---

## 3. New stats & features — the fun part

Your data (`weeks[].games`, `weeks[].teams` with `h2h`/`topHalf`/`weekPoints`
per team per week) is already rich enough for all of this — none of it needs
a new ESPN call. This is the highest-payoff bucket because it's *content*,
not scaffolding — it's the stuff people actually screenshot into the group
chat.

| # | Idea | What it shows | Effort | Payoff |
|---|---|---|---|---|
| F1 | **Luck Index** | For each team: `h2hPoints` vs. what their record "should" be based on points scored relative to the league that week (i.e., did you win despite scoring below the field, or lose despite scoring well?). Classic fantasy trash-talk stat — "most unlucky" and "luckiest" owner, ranked. You already compute `scoreToBeat` per week; this is a derived column, not new data. | S | 🔥 |
| F2 | **Head-to-head matrix / rivalry record** | A 12×12 grid: every owner's all-time record against every other owner (win-loss, avg margin). Rendered as a heatmap grid (dataviz-friendly) or a simple table. This is the "who's my rival" page league mates ask for by week 3 every year. | M | 🔥 |
| F3 | **Matchup visualizer** (your instinct) | Per-week matchup cards: two teams, their scores, a bar comparing them, W/L + top-half badges, maybe a mini sparkline of both teams' last-3 trend. Basically a "box score" page per week instead of just the aggregate table. Pairs well with F6 (weekly recap). | M | High |
| F4 | **Closest games & biggest blowouts** | Sort all-time (or season) matchups by margin. "Closest game ever: 0.4 points, Week 6 2024." Blowouts are the other trash-talk staple. Trivial once you have all `games[]` flattened across seasons. | S | High |
| F5 | **Streaks** | Current win streak / losing streak / "on a heater" (top-half streak) per owner, shown right on the standings page as a badge (🔥 3W or ❄️ 2L). | S | High |
| F6 | **Weekly recap / "power rankings" blurb** | Auto-generated one-paragraph recap per week: top scorer, biggest upset (lowest seed win by points), score-to-beat, week MVP. Even a templated (non-AI) fill-in-the-blank recap reads as "content" instead of "a spreadsheet." | M | High |
| F7 | **Championship simulator** | Monte Carlo over remaining games (even a dumb one — sample each team's own past scores) to give live playoff-odds %. This is the single most-checked stat on real fantasy platforms in weeks 8–14. Needs `compute.py` work, not just template work. | L | 🔥 |
| F8 | **Owner profile / manager card page** (`player1.html` is sitting there unused) | Per-owner page: career record across all seasons, best/worst week ever, championships, a fun "manager rating." `player1.html` literally already exists for this — it just needs roster-shaped data, which you don't have; a career-stats version doesn't need rosters at all and could ship today. | M | High |
| F9 | **All-time / dynasty leaderboard** | You already build every season 2022–2025+ into separate `standings-<season>.json`. A page that aggregates across all of them (most championships, best career average, most top-six finishes ever) is a build.py loop away — no new data. | S | High |
| F10 | **"On the bubble" indicator** | On the standings page, flag the teams right at the 6th/7th playoff line — the boundary that already drives your `scoreToBeat` math. Cheap, and it's exactly what people care about in weeks 10-14. | XS | Med |

If you build one thing from this list, F1 (Luck Index) + F5 (Streaks) are a single afternoon combined and immediately make the standings page 10x more interesting to argue about, and F2/F4 (rivalries/blowouts) are the best "look what I found" content for a league group chat.

---

## 4. Quality of life / dev experience

| # | Idea | Effort | Payoff |
|---|---|---|---|
| Q1 | `data/raw-*.json` and cached ESPN responses aren't in `.gitignore` review — worth double-checking nothing sensitive (there shouldn't be, public league) sneaks in as data grows across seasons. | XS | Low |
| Q2 | `__pycache__/*.pyc` showing up in `git status` (untracked) — add `__pycache__/` to `.gitignore` if it isn't already covering it. | XS | Low |
| Q3 | CI: add a step that runs `python -m unittest test_compute` on every PR/push, not just locally — cheap insurance since `compute.py` is "the only file with real logic" per your own SPEC. | S | Med |
| Q4 | `build.py` output diffing — you already rely on deterministic output for the daily Action; a small `--check` mode that fails CI if `docs/` would change on a clean rebuild catches template/data drift early. | S | Low |
| Q5 | Add a `Makefile`/`justfile`/`npm`-free task runner (`fetch`, `compute`, `build`, `all`) so the three-script pipeline is one command instead of three, for you and for future contributors (e.g. if a league mate wants to help). | XS | Med |

---

## 5. Modernization (lower priority — it's static and it works)

| # | Idea | Effort | Payoff |
|---|---|---|---|
| M1 | Bootstrap 4.1.3 + jQuery 3.3.1 + Popper 1.14.3, all pinned to 2018-era CDN URLs (`stackpath.bootstrapcdn.com`, `unpkg.com`, `code.jquery.com`, `cdnjs`) — none of this is broken, but it's five external CDN dependencies for a static site that could be almost entirely vanilla CSS/JS at this point (Bootstrap 4 is EOL). Not urgent; flag it as tech-debt interest, not principal. | L | Low |
| M2 | Chart.js 2.7.1 → 4.x — mainly matters if you want newer chart types (radar for "team strengths," etc.) for the fun stats above. | M | Low |
| M3 | `player1.html`'s `</br></br></br></br>` (literal, `home.html`/`playoffs.html` don't have this) — cosmetic leftover, fix whenever that page gets built out (F8). | XS | Low |

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

## My picks — what I'd actually do next

1. **B1 + B2** (wins-to-clinch hardcoding, games-back sign) — 20 minutes,
   removes the two things that'll make an attentive league mate go "wait,
   that's wrong."
2. **F1 Luck Index + F5 Streaks** — one sitting, and it's the single biggest
   "come argue about this" upgrade to the existing standings page.
3. **U1 + U2** (highlight my row, color the point cells) — makes the table
   you already have dramatically easier to read on a phone during a game.
4. **F2 Rivalry matrix** or **F4 Closest games/blowouts** — whichever
   sounds more fun to build; both are pure derived-data pages, no new
   fetch, and they're the "I found something" content that gets
   screenshotted into the group chat.
5. Later, once weeks pile up: **F7 Playoff simulator** — this is the one
   that turns "check the site once" into "check the site every week in
   November."

Everything in §6 (multi-league) can wait until the above makes the FFF site
itself something you're proud to link people to.
