# LeagueStats — v2 spec

A standings page for **FFF** (ESPN league `877873`, "Fantasy Football Fantasy"),
computing a scoring system ESPN cannot compute itself.

v1 (2018–19) was Flask + Postgres on Heroku. It died when Heroku dropped free
Postgres. **The frontend never died — only the backend did.**

**This is an enhancement, not a rewrite.** The templates, the Bootstrap layout,
the CSS and the standings table all stay. What changes is where the data comes
from and how the page is served.

---

## 0. Working protocol — READ THIS FIRST, EVERY SESSION

**One task per session. Stop when it is done.**

1. **Get context.** Read this spec's §9 task list and `WORKLOG.md`. Identify
   the first task not marked done.
2. **Do exactly that one task.** Nothing else.
3. **Document it.** Append an entry to `WORKLOG.md`: what you changed, which
   files, what you verified, anything you deferred or found surprising.
4. **Stop.** Say which task is next and end the session. **Do not begin it.**

### Rules that override any instinct to be helpful

- **Do not start the next task**, even when it looks small, obvious, or like a
  natural continuation. Finishing early is correct behaviour, not a reason to
  continue.
- **Do not build anything the task does not ask for.** No extra scripts, no
  helper abstractions, no "while I was here" refactors, no config frameworks.
- **If anything is ambiguous, STOP and ask.** Do not guess and do not invent a
  design. Every decision in this document is already made; a gap is a bug in
  the spec, not an invitation.
- **Do not add dependencies.** The list in §2 is complete.
- **Do not touch `templates/` or `static/` except where a task explicitly says
  to.** That is the author's 2018 work and it is being kept on purpose.

> This protocol exists for a measured reason. Handed a single task on a sibling
> project, this model completed it and then continued into the *next* two tasks
> unprompted, including writing files nobody asked for. The work was not bad —
> it just was not requested, and reviewing unrequested work costs more than it
> saves. One task, then stop.

---

## 1. The scoring rule — the whole reason the project exists

Each week, every team can earn **up to 2 points**:

| Point | Condition |
| --- | --- |
| **1** | Win your head-to-head matchup |
| **1** | Finish in the **top half** of the league in raw points that week |

Twelve teams, six matchups, so each week distributes 6 H2H points and 6
top-half points.

**ESPN does not support this natively** — it shows W/L and points-for and leaves
the second point uncomputed. That gap is the product, and it is why this repo
exists at all.

### Exact math

For each week:
1. Collect all 12 team scores.
2. **H2H:** in each of the 6 matchups, the higher score takes the point.
3. **Top half:** sort the 12 scores ascending. Index `[5]` is the **threshold** —
   the highest score that missed the top six. A team earns the point by scoring
   **strictly greater** than it.

v1 called that threshold the **"score to beat"** and computed it exactly this
way in `getApiData.py:getScoresToBeat()`. It is correct. Keep the name — it is
what the league calls it.

### Scoring window

**Weeks 1–14 only.** Read the value from
`settings.scheduleSettings.matchupPeriodCount` (currently 14) — do
not hardcode it. Weeks 15–17 are the playoff bracket (6 playoff teams) and must
not accumulate dual points.

### Tie rules — ASSUMPTIONS, flagged for confirmation

Not documented in v1. Defaults chosen to match v1's strictly-greater comparison:

- **Exact H2H tie** → no point to either team.
- **Exact tie at the top-half boundary** (6th and 7th identical) → no point to
  either, so the league awards 5 top-half points that week rather than 7.

Write both as explicit branches with tests, not as a side effect of an operator.
Ask the league before the first public run.

---

## 2. Architecture

**Python 3.11+, keeping Jinja2.** Four scripts, run in order:

```
fetch.py     ESPN → data/raw-<season>.json           one HTTP call, whole season
compute.py   raw  → data/standings-<season>.json     the dual-point math
build.py     standings + templates/ → docs/*.html    static render, no server
```

`compute.py` and `build.py` never touch the network, so they re-run offline
against a committed raw file.

**Dependencies — this list is complete:** `requests`, `jinja2`. That is it.
Flask, flask-session, SQLAlchemy and psycopg2 all go.

**Why Python and not a rewrite in something else:** the templates are Jinja and
they are worth keeping (§4). Rendering them needs Jinja. Anything else means
rewriting the frontend, which is the one part that still works.

---

## 3. Data source

One call returns the **entire season's** schedule with scores:

```
https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/<season>/segments/0/leagues/877873?view=mMatchupScore
```

- **Public league. No cookies, no auth, no secrets in the repo.** This is what
  makes the whole no-credentials design possible.
- A second call with `view=mTeam` gets team names and owners. Sleep 1s between
  each call — it is an unauthenticated public API.
- A third call with `view=mSettings` carries the regular-season length —
  `settings.scheduleSettings.matchupPeriodCount`. Neither `mMatchupScore` nor
  `mTeam` includes a `settings` object, so L2 needs this view.
- Shape:
  ```jsonc
  { "schedule": [
      { "matchupPeriodId": 5,
        "home": { "teamId": 1, "totalPoints": 143.8 },
        "away": { "teamId": 4, "totalPoints": 117.4 } } ] }
  ```

### Two traps inherited from v1 — do not re-introduce

1. **Do not index `schedule` by arithmetic.** v1 used `(week-1)*6 + matchup`,
   assuming exactly 6 ordered entries per week. True for weeks 1–14, **false in
   the playoffs** — week 15 of 2025 has 7 entries. Always filter on
   `matchupPeriodId`.

2. **`getApiData.py:getWeeklyScores()` is broken.** It indexes `schedule[0]`
   inside a loop over `matchup`, and assigns the home team twice so away never
   lands — every team gets week 1's home score. Do not port it. Read
   `getScoresToBeat()` in the same file first; that one is correct and is the
   model to follow.

---

## 4. The frontend — kept, not replaced

`templates/` and `static/dashboard.css` are v1's work and they stay. The
standings table in `home.html` **already has the right columns**:

```
Rank | Owner | Total Wins | Total Points | Average Score | Avg Last 3 | H2H Wins | Top Six Finishes
```

`info.wins` is the H2H count and `info.top6` the top-half count. The UI already
models the dual-point system correctly. Only its data source changes.

### Total Flask coupling: five lines

```
templates/layout.html:12   url_for('static', filename='fffIcon.png')
templates/layout.html:18   url_for('home')
templates/layout.html:97   get_flashed_messages()
templates/layout.html:100  get_flashed_messages()
templates/home.html:144    url_for('static', filename='js/hello.js')
```

Replace `url_for(...)` with plain relative paths; delete the
`get_flashed_messages()` block. Everything else — `{% extends %}`,
`{% block %}`, `{% for %}`, filters, `loop.index` — is standard Jinja and
renders unchanged.

### The one structural change: sorting

v1's column headers link to Flask routes (`/total_wins`, `/h2h`, `/top6`,
`/average_score`) that re-queried and re-sorted server-side. **A static site has
no routes.** Replace with client-side sorting: keep the `<th>` elements, drop
the `<a href>`, sort the table in JavaScript on click.

`static/js/hello.js` is a stub from an unfinished "new js table" commit — this
is that commit, finished. Vanilla JS, no library.

### Pages to render

`home.html` is the priority. `playoffs.html`, `player1.html`, `graph.html`,
`weeklyupdate.html`, `update.html`, `welcome.html`, `error.html` exist in
`templates/`; `update.html` and `error.html` were admin/Flask concerns and can
be dropped. Render the rest only if the data supports them — **do not invent
data to fill a template.** If a page needs something `standings.json` does not
have, note it in `WORKLOG.md` and leave the page unrendered.

Note: `layout.html` hardcodes 2018 owner names in the sidebar and a 2018 Chart.js
dataset. Both should come from the data. That is a task (§9 L5), not something
to fix opportunistically.

---

## 5. Output shape

`data/standings-<season>.json` — the committed artifact the page renders from.

```jsonc
{
  "season": 2025,
  "league": "877873",
  "updated": "2026-09-18T13:04:11Z",
  "regularSeasonWeeks": 14,
  "throughWeek": 14,
  "weeks": [
    { "week": 5,
      "scoreToBeat": 108.9,
      "games": [ { "home": 1, "away": 4, "homeScore": 143.8, "awayScore": 117.4, "winner": 1 } ],
      "teams": [ { "teamId": 1, "score": 143.8, "h2h": 1, "topHalf": 1, "weekPoints": 2 } ] }
  ],
  "standings": [
    { "rank": 1, "teamId": 1, "name": "…", "owner": "…",
      "points": 21, "h2hPoints": 11, "topHalfPoints": 10,
      "record": "11-3", "pointsFor": 1698.4, "pointsAgainst": 1502.1,
      "averageScore": 121.3, "avgLast3": 118.0 }
  ]
}
```

Keep the per-week detail — it is what makes a weekly-recap view possible later
without re-fetching, and it is how you audit a standings change by diffing two
commits.

**Standings sort:** `points` desc, then `pointsFor` desc.

---

## 6. Why no database

Not effort. The workload has none of the properties a database is for:

- **No queries.** Exactly one view. A database earns its keep when you need to
  ask questions you did not anticipate.
- **No mutation.** Every run recomputes ~170 numbers from scratch in
  milliseconds. No incremental state, transactions, or concurrency.
- **Git is already the right database for this shape** — append-only,
  timestamped, versioned. Diff two commits to see exactly what moved.
- **A database is what killed v1.** Removing the server removes the only
  component that can expire, rot, or bill you.

**Revisit if:** arbitrary cross-season queries, more than one writer, features
with real relational shape (trades, player-level weekly history), or data that
outgrows a git-diffable file.

An optional DB *sink* is fine later — write to it **in addition to** the JSON,
never instead. The site must keep rendering when it is down.

---

## 7. Deploy

**GitHub Pages** serving `/docs` from the default branch. **GitHub Actions** on
a schedule:

```yaml
on:
  schedule:
    - cron: '0 13 * * *'    # daily ~8am ET
  workflow_dispatch:         # manual "run now"
```

Run fetch → compute → build, then **commit only if output changed**.

Daily rather than weekly: ESPN issues stat corrections for a day or two after
games, and a daily idempotent run absorbs them. One missed run then costs
nothing.

**Known limitation, document it in the README:** GitHub disables scheduled
workflows on public repos after **60 days of repository inactivity**. In-season
the job commits regularly and stays alive; Feb–Aug it goes dormant and needs one
manual re-enable each August.

---

## 8. Repo setup

This work goes to a **new remote** — `LeagueStatsReloaded`. The original
`tuura032/LeagueStats` is being made **private** and kept as-is.

- **Fresh history (owner decision, 2026-09-22).** The new repo starts from a
  clean `git init`; the 2018–19 commits do not ride along. GitHub Push
  Protection blocked the first push (the old history carries the Postgres
  URL below), and the owner chose a fresh baseline over unblocking the
  secret or rewriting history. The 2018 lineage stays readable in the
  private repo.
- **`application.py` carried a hardcoded Postgres URL.** It is deleted
  before the first commit, so the secret exists only in the private repo's
  history. The database is long dead.
- Deleted from the working tree before the first commit (the private repo
  keeps them): `application.py`, `getApiData.py`, `Procfile`,
  `__pycache__/`. `getApiData.py:getScoresToBeat()` — the §1 reference
  implementation — was read and ported into `compute.py` in L2.
- `requirements.txt` shrinks to `requests` and `jinja2`.

---

## 9. Task list

One per session. Mark done in `WORKLOG.md`, not here.

- **L1 — `fetch.py`.** Three ESPN calls (`mMatchupScore`, `mTeam`, `mSettings`),
  1s apart, written verbatim to `data/raw-<season>.json`. No transform.
  `--season` flag defaulting to the current year.

- **L2 — `compute.py`.** Raw → `data/standings-<season>.json` per §1 and §5.
  Pure, no network. **Tests are mandatory — this is the only file with real
  logic.** Cover: a normal week, an H2H tie, a top-half boundary tie, and that
  weeks 15–17 contribute no dual points.

- **L3 — De-Flask the templates.** The five lines in §4, plus swap the
  DB-shaped variable names (`sortedbywin`, `info.wins`, `info.top6`,
  `current_week`) for the JSON's keys. No visual change — the page should look
  identical.

- **L4 — `build.py`.** Render templates to `docs/`. Static, no server.
  `home.html` first.

- **L5 — Data-drive the sidebar and chart.** `layout.html` hardcodes 2018 owner
  names and a 2018 Chart.js dataset; both come from `standings.json`.

- **L6 — Client-side table sorting.** Replace the dead `/total_wins`, `/h2h`,
  `/top6`, `/average_score` route links with vanilla JS column sorting in
  `static/js/`. Finishes the abandoned "new js table" commit.

- **L7 — GitHub Action + Pages.** Per §7, commit-only-if-changed.

- **L8 — README + cleanup.** Per §8. Explain the scoring rule, local dev, and
  the 60-day workflow caveat.

- **L9 (optional) — Multi-season archive.** The endpoint takes any season and
  FFF has history to 2022. Once one season works this is a loop plus a season
  picker. **Do not start before L1–L8 are done.**

---

## 10. Decisions — do not re-litigate

- **Enhancement, not rewrite.** The frontend stays. (§4)
- **No database, no server, no secrets.** (§6)
- **Static output committed to the repo**, served by Pages. (§7)
- **Files are the source of truth.** Any future DB is an additive sink.
- **Two dependencies**, `requests` and `jinja2`. (§2)
- **Scoring covers the regular season only**, length read from the API. (§1)
- **Self-hosting was considered and declined** for this site — it is a static
  page that free hosting serves better, and a 36TB NAS is the wrong machine to
  expose. Self-host things that benefit from being local; this does not.
