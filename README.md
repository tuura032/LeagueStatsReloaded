# LeagueStats

Standings page for **FFF** ("Fantasy Football Fantasy", ESPN league
`877873`) that computes a scoring system ESPN cannot compute itself.

v1 (2018–19) was Flask + Postgres on Heroku. It died when Heroku dropped free
Postgres. The frontend survived — only the data layer is replaced here: three
small Python scripts feed the same templates, and the result is a static site
on GitHub Pages. No database, no server, no secrets.

Live site: <https://tuura032.github.io/LeagueStatsReloaded/> — standings
(click a column header to sort), playoffs and prizes, and a weekly-scoring
chart.

## The scoring rule

Each week, every team can earn up to **2 points**:

| Point | Condition |
| --- | --- |
| 1 | Win your head-to-head matchup |
| 1 | Finish in the **top half** of the league in raw points that week |

Twelve teams, six matchups, so each week distributes 6 H2H points and 6
top-half points. ESPN shows W/L and points-for and leaves the second point
uncomputed — that gap is the product.

**Top half** is decided by the *score to beat*: sort the weekly scores
ascending; index `[n // 2 - 1]` is the threshold — the highest score that
missed the top half (index `[5]` for this 12-team league). A team earns the
point by scoring **strictly greater** than it.

Ties (matching v1's strictly-greater comparison):

- Exact H2H tie → no point to either team.
- Exact tie at the top-half boundary (6th and 7th identical) → no point to
  either, so the league awards 5 top-half points that week rather than 7.

**Regular season only.** Dual points stop after week `matchupPeriodCount`
(14) — read from the ESPN API, never hardcoded. Weeks 15–17 are the playoff
bracket and accumulate no dual points — but they *are* parsed, separately,
to record who actually won the league (see below).

## Champions

Weeks 15–17 carry ESPN's `playoffTierType`. `compute.py` reads the
`WINNERS_BRACKET` entries and records the winner of the final as that
season's champion, under a `playoffs` key on
`data/standings-<season>.json` (`null` until the final is decided).

This matters because "finished #1 in the regular season" and "won the
league" are different things and the site used to conflate them — Career
Stats counted regular-season firsts and called them titles, which named
the wrong owner for four of the five seasons on file. **Titles** 🏆 and
**Reg #1** are now separate columns.

Standings sort by total points, then points-for.

## Stats, records and awards

The Stats page is built entirely from the weekly scores already on file —
no extra ESPN call, nothing stored beyond `standings-<season>.json`.

- **All-play record** — your record if you had played every other team
  every week, i.e. the schedule removed. The gap between it and your real
  record is the cleanest measure of schedule luck, and it is the continuous
  version of the league's own top-half point.
- **Swing** — standard deviation of weekly scores.
- **Robbed / Stole It** — weeks scoring top-half and losing, and weeks
  winning from the bottom half.
- **Season records** — biggest blowout, closest game, high and low scores,
  best score in a loss, worst score in a win, highest and lowest combined.
- **Season awards** — ten named superlatives, ties shown as co-winners.

Awards are computed by fixed rules and are **not randomised**: `build.py`
must stay deterministic so the daily workflow commits only when the data
actually changed.

## How it works

```
fetch.py     ESPN API → data/raw-<season>.json      3 public calls, 1s apart
compute.py   raw  → data/standings-<season>.json    the dual-point math
build.py     standings + templates/ → docs/         static render, no server
```

`compute.py` and `build.py` never touch the network, so they re-run offline
against a committed raw file. The JSON files are the source of truth — diff
two commits to see exactly what moved.

## Local development

Python 3.11+. Dependencies: `requests`, `jinja2` — that's it for the data
pipeline.

```
pip install -r requirements.txt

python fetch.py --season 2026     # --season defaults to the current year
python compute.py --season 2026
python build.py --season 2026
```

Or via the task runner (stdlib only, no extra dependency):

```
python tasks.py all        # recompute every season on file, rebuild, test
python tasks.py build      # just re-render docs/
python tasks.py refresh    # fetch this season too (hits the network)
python tasks.py test
```

Open `docs/index.html` in a browser.

### Frontend (Tailwind CSS)

The site is styled with Tailwind CSS, compiled at dev time from
`src/tailwind.css` to `static/css/app.css`. That compiled file **is
committed** — GitHub Pages has no build step, so `static/` has to be
served as real files, same as `static/js/hello.js`. Only needed after
editing a template's class names or `src/tailwind.css`:

```
npm install
npm run build:css      # one-shot
npm run watch:css       # rebuilds on save, for template work
```

Rebuild it and re-run `python build.py` before committing a template
change, or the deployed CSS won't match the markup.

Tests (the dual-point math — the only file with real logic):

```
python -m unittest test_compute -v
```

`build.py` output is deterministic (no timestamps), so a rebuild changes
`docs/` only when the data changes.

## Deployment

GitHub Pages serves `docs/` from the `main` branch. A GitHub Actions workflow
runs daily at ~8am ET and on manual dispatch: fetch → compute → build, then
**commits only if the output changed**. Daily rather than weekly: ESPN issues
stat corrections for a day or two after games, and a daily idempotent run
absorbs them.

**Known limitation:** GitHub disables scheduled workflows on public repos
after **60 days of repository inactivity**. In-season the job commits
regularly and stays alive; February–August it goes dormant and needs one
manual re-enable each August.

## Files

| Path | What |
| --- | --- |
| `fetch.py` | ESPN API → `data/raw-<season>.json` (verbatim, no transform) |
| `compute.py` | raw → `data/standings-<season>.json` (the dual-point math + playoff bracket), plus the render-time rivalry/career/season-stats derivations |
| `build.py` | renders `templates/` to `docs/`, copies `static/` |
| `test_compute.py` | unit tests for the scoring rule |
| `data/` | committed raw + computed JSON per season |
| `data/prizes.json` | the league pot — labels, amounts, and which result each prize is awarded on |
| `tasks.py` | one-command wrappers for fetch/compute/build/test |
| `BENCH_POINTS.md` | outside UI/UX + product consult, 2026-09-22 |
| `docs/` | the rendered static site (what Pages serves) |
| `SPEC.md` | the v2 spec — scoring rule, architecture, task list |
