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

**Top half** is decided by the *score to beat*: sort the 12 weekly scores
ascending; index `[5]` is the threshold — the highest score that missed the
top six. A team earns the point by scoring **strictly greater** than it.

Ties (matching v1's strictly-greater comparison):

- Exact H2H tie → no point to either team.
- Exact tie at the top-half boundary (6th and 7th identical) → no point to
  either, so the league awards 5 top-half points that week rather than 7.

**Regular season only.** Dual points stop after week `matchupPeriodCount`
(14) — read from the ESPN API, never hardcoded. Weeks 15–17 are the playoff
bracket and accumulate nothing.

Standings sort by total points, then points-for.

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

Python 3.11+. Dependencies: `requests`, `jinja2` — that's it.

```
pip install -r requirements.txt

python fetch.py --season 2026     # --season defaults to the current year
python compute.py --season 2026
python build.py --season 2026
```

Open `docs/index.html` in a browser.

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
| `compute.py` | raw → `data/standings-<season>.json` (the dual-point math) |
| `build.py` | renders `templates/` to `docs/`, copies `static/` |
| `test_compute.py` | unit tests for the scoring rule |
| `data/` | committed raw + computed JSON per season |
| `docs/` | the rendered static site (what Pages serves) |
| `SPEC.md` | the v2 spec — scoring rule, architecture, task list |
| `WORKLOG.md` | one entry per work session |
