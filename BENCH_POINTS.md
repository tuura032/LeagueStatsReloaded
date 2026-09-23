# BENCH POINTS

*An outside consult on LeagueStats — 2026-09-22*

**Bench points** (n.): the points your bench scored while you played someone
else. Potential you already owned and didn't start.

That is this entire review. The app is not short on data, taste, or
engineering. It is short on *starting what it already has on the roster*. You
fetch a JSON payload every morning that contains the league rulebook, team
logos, transaction counts, draft settings, and the full playoff bracket — and
you render about 15% of it.

Below: what's good, what's broken (verified, with evidence), what's sitting on
the bench, and what I'd actually build in what order.

---

## 0. The headline: your app crowns the wrong champion

Start here, because this one will get you yelled at in the group chat.

`compute.py` stops at `matchupPeriodCount` (week 14) and throws away weeks
15–17. But the winners' bracket is right there in `data/raw-2025.json`:

```
wk15  5:136.0  vs  9:177.4   → AWAY
wk15 12:167.8  vs  1:83.1    → HOME
wk16  2:140.9  vs  9:115.8   → HOME
wk16 11:133.1  vs 12:172.4   → AWAY
wk17  2:108.9  vs 12:154.5   → AWAY      ← the 2025 championship game
```

Team 12 is **Davíd Huisken ("Hail Sun God")**, the 3-seed. He won the 2025
title by 45 points.

Career Stats currently awards the 2025 ★ to **Casey Pirsig** — who finished
regular-season #1 and then *lost that final*. The page says so in the fine
print ("Titles counts regular-season #1 finishes; playoffs aren't tracked
here"), and that disclaimer is honest, but it does not save you. A league
history page that cannot answer *"who won our league?"* is missing the only
question anyone asks at the draft table. Worse, it prints a confident answer
that is wrong.

Everything needed to fix it is already in `data/raw-*.json`. No new API calls,
no new dependencies, no cost. This is a `compute.py` change and a column
rename.

**Also note:** 2025 week 15 has **7** schedule entries, not 6 — the two byes
for seeds 1 and 2 create entries with no `away` side. That is exactly the trap
`SPEC.md` §3 warns about. Your `_played()` guard already handles it correctly
(`if not home or not away: return False`). The groundwork is done; you just
never walked through the door.

---

## 1. What's genuinely good

I want to be specific here, because the rest of this document is a list of
problems and that would give a false impression.

- **The architecture is right.** Fetch/compute/build as three pure stages,
  JSON committed as the source of truth, git as the history layer. §6 of
  `SPEC.md` is one of the better "why no database" arguments I've read, and it
  is *correct for this workload*. Do not let anyone talk you into Postgres.
- **The scoring engine is real software.** 35 passing tests covering tie
  branches, the boundary case, and playoff-week exclusion. `score_to_beat()`
  ports a known-good v1 function and says so. `_played()` handles byes and
  undecided games. This is the part most hobby projects get wrong and you got
  right.
- **Owner-identity matching across seasons** (`build_rivalries`,
  `build_career_stats` keying on owner name, not `teamId`) is a genuinely
  thoughtful call. Team IDs churn; the human doesn't.
- **The dual-point rule is a real product.** "ESPN can't compute this" is an
  actual wedge. Most fantasy side-projects re-display what the platform
  already shows.
- **Dark mode is done properly** — resolved before first paint in an inline
  script, no flash, `localStorage` override on top of system preference. Most
  people ship the flash.
- **The rivalry matrix has a sticky first column** (`sticky left-0` on the row
  headers). Someone thought about horizontal scroll. Credit where due.
- **Deterministic builds + commit-only-if-changed** is exactly how a daily bot
  should behave.
- **Luck index** (H2H minus top-half) is the smartest stat on the site. It is
  the one number that makes people argue, and arguing is the product.

The visual design is clean and modern. Slate/Tailwind, good density, sensible
rank medals, the playoff-line divider is a nice touch. This does not look like
a 2018 Bootstrap app anymore.

---

## 2. Broken right now (verified, not guessed)

### 2.1 Click-to-sort on the Home page does nothing — the flagship interaction on the flagship page

The playoff-line divider is a `<tr>` inside `<tbody>` with a single
`colspan="10"` cell. `static/js/hello.js` collects *every* row in the tbody
and indexes `a.cells[col]` — which is `undefined` for that row.

Verified against the rendered `docs/index.html` (13 rows in tbody; row 6 has 1
cell), then executed:

```
TypeError: Cannot read properties of undefined (reading 'textContent')
```

The exception propagates out of `Array.sort`, so the click handler aborts
before it reorders anything *or* sets the sort arrow. The header appears
inert. Nothing in the console tells the user why.

Careers and Playoffs sort fine — they have no divider row. So this reads as
"sorting works" during testing unless you specifically click Home.

Fix: skip rows without a cell at `col` (`if (!a.cells[col] || !b.cells[col])`),
or better, pin the divider row out of the sort set entirely and re-insert it
at the current playoff cut after each sort. The second is more work and more
correct — the playoff line is meaningless once you've sorted by Points For.

### 2.2 The Stats chart renders as a solid blob

`layout.html` builds a Chart.js `type: 'line'` with
`backgroundColor: color` per dataset. **Chart.js 2.x defaults line datasets to
`fill: true`**, so every series fills to the axis. With 2 weeks of data that is
a giant blue trapezoid, which is exactly what the screenshot shows. The page's
own subtitle promises "the top three teams are shown by default" — you can see
one.

Fix: `'fill': false` in the dataset dict.

### 2.3 Chart tooltips throw on hover

Same script:

```js
return ' ' + item.dataset.label + ': ' + item.yLabel;
```

`item.dataset` is the **Chart.js 3.x** tooltip-item API. You are on **2.7.1**,
where the item exposes `datasetIndex` / `index` and you reach the label via
`data.datasets[item.datasetIndex].label`. The callback receives `(item, data)`
— the second argument is right there, unused.

So: blob you can't read, and hovering it fails silently.

### 2.4 Chart.js 2.7.1 is from 2017

Nine years old, in the `<head>` of **all five pages**, from cdnjs — even though
only `graph.html` has a `<canvas>`. Same for `feather-icons`, loaded
**unversioned** (`unpkg.com/feather-icons/dist/feather.min.js`), meaning a
breaking upstream release silently breaks every icon on your site with no
commit on your end. For a project whose entire thesis is "remove the components
that can expire, rot, or bill you" (`SPEC.md` §6), two unpinned/ancient CDN
dependencies on every page is off-thesis.

Vendor both into `static/`. They're small, you already commit `app.css` for
exactly this reason, and it makes the site work offline and forever.

### 2.5 The in-flight prize refactor is half-wired

Someone (you, mid-session) just moved prize *labels* to `data/prizes.json` and
made the `<thead>` loop over it. The `<tbody>` is still **eight hardcoded
`<td>`s**. Change the number of prizes in the JSON and the header and body
desync immediately. Finish the loop before committing.

### 2.6 Smaller, real

- **Score truncation.** `{{ weekScore(...) | int }}` on Playoffs turns 176.7
  into 176. Stats says 176.7 in the "Biggest single week" tile. Same number,
  two pages, two values. In a league where decimals decide matchups, never
  truncate a score.
- **"Wins to Clinch / 24"** is not a sentence. It reads as a fraction. It's
  "wins available in the rest of the season." Say that.
- **"Heating Up" is 0.0 for everyone** at week 2 — mathematically correct
  (avg-last-3 equals season average when only 2 weeks exist) but useless.
  Hide the column until week 4.
- **"Week 0" column** — already fixed in your working tree, not yet committed.
  Commit it.
- **Nothing shows when the data was last updated.** `standings.json` carries
  `updated`; no template renders it. For a page backed by a daily bot, "as of
  Sun 8:03am ET" is a trust signal you're paying for and not spending.

---

## 3. UI/UX review

### Works
Density is right for the audience. Rank medals, streak pills, and the
conditional green/red on H2H and Top-Six give real at-a-glance scanning. The
playoff-line divider is a genuinely good idea. "Tap your name to pin your row"
with `localStorage` is the correct answer to "there's no login" — cheap,
private, effective.

### Doesn't

**Mobile is where fantasy football is actually consumed, and mobile is the
weaker half.**

- **Tables die at the right edge with no affordance.** On Home you see Rank /
  Owner / Wins / Points / Streak and nothing hints that six more columns exist.
  `overflow-x-auto` scrolls, but nothing *says* it scrolls. Add a fade mask on
  the right edge, or stop using a table on mobile entirely (see below).
- **"Careers" is off-screen in the mobile nav.** Five items in a horizontally
  scrolling bar; on a 390px viewport the fifth is past the edge with no visual
  cut-off cue. Your newest page is the hardest one to find.
- **The rivalry matrix is the wrong component for a phone.** 12×12 with
  rotated vertical headers is a desktop artifact. On mobile, invert it: pick an
  owner, show a ranked list of their records vs. everyone. That's also the
  question people actually ask ("how do I do against Sam?"), not "show me 144
  cells."
- **No sticky table headers.** Scroll to row 12 of Career Stats and the column
  meanings are gone.

**Desktop**

- **Enormous dead space below the fold.** Every page is one table and then
  ~400px of nothing. That's where the context belongs — this week's matchups,
  the score to beat, biggest mover, a sparkline per team.
- **The "Owners" sidebar accordion is a dead end.** It lists 12 owners with
  rank and team name and they aren't links. There are no owner pages, so it
  expands to a list that does nothing. Either build owner pages (see §5) or
  cut it.
- **Nav labels are inconsistent.** Sidebar: "Playoffs and Prizes", "Stats",
  "Career Stats". Mobile: "Playoffs", "Stats", "Careers". And "Stats" points at
  `graph.html`, which is titled "All Points Scored Each Week". Three names for
  one page.
- **No social/OG meta tags.** This is a link that gets pasted into a league
  group chat every Tuesday. Right now it unfurls as a bare URL. An OG image
  with the current top 3 and the week number would make the link itself the
  product. This is maybe 20 lines in `layout.html` plus a static image, and it
  is the highest-leverage cosmetic change available.
- **No empty/preseason state.** `standings[0]`, `[1]`, `[2]` are indexed
  unguarded on Playoffs; a fresh season with zero complete weeks renders a
  table of zeros and a prize table naming whoever sorts first alphabetically.

**Accessibility**

- Sort headers are `<th>` with click handlers — not keyboard reachable. Wrap
  the label in a `<button>`.
- Colour is doing unaided work in the H2H/Top-Six heatmap and the rivalry
  matrix. Red/green with no secondary cue is the single most common
  colour-blind failure. You already chose an Okabe-Ito-ish palette for the
  chart — someone here knows this. Apply it to the tables.
- The pinned-row click target is the whole row with no `role`, no focus style,
  and no keyboard path.

---

## 4. Using this for other leagues

You asked for this explicitly, so: **the app is about 4 hard-coded values away
from being multi-league, and 2 of them are already in the JSON you download.**

| Thing | Now | Should be |
| --- | --- | --- |
| League ID | `LEAGUE_ID = "877873"` in `fetch.py:17` **and** `compute.py:26` | `--league` flag / config file |
| League name | The literal string "Fantasy Football Fantasy" in **9 templates** | `mSettings.settings.name` — *already fetched* |
| Playoff spots | `(standings\|length) // 2` in `home.html` | `scheduleSettings.playoffTeamCount` — *already fetched* |
| Prize structure | `data/prizes.json` (just extracted — good) | keep as config; optionally seed from `financeSettings.entryFee × size` |

That playoff-spots line deserves a callout. `12 // 2 == 6`, and this league's
`playoffTeamCount` **is** 6. It is correct **by coincidence**. A 12-team league
with a 4-team playoff draws the line in the wrong place, and a 10-team league
with 6 spots draws it wrong too. The right value is in a file on your disk
right now.

Other things that assume *this* league:

- `score_to_beat()` hardcodes `sorted(scores)[5]` — the 6th-lowest. That is
  "top half of 12." For a 10-team league it must be `[len(scores)//2 - 1]`.
  **This is the actual scoring rule and it silently computes the wrong answer
  for any league that isn't 12 teams.** Highest-priority multi-league fix,
  and it needs a test.
- `divisions` exists in `scheduleSettings` (this league has 1). Multi-division
  leagues have no representation anywhere in the app.
- `docs/` layout is single-league. Multi-league wants `docs/<league>/<season>/`
  and a league picker next to the season picker.

**The shape I'd aim for:** a `leagues.yml` (or JSON, to keep the two-dependency
rule) listing league IDs + display config, and a build that loops it the same
way it already loops seasons. You solved this problem once for seasons in L9;
this is the same pattern one level up. That is genuinely reusable, and it's the
version you could hand to someone else.

---

## 5. Bench points — what ESPN already hands you

Every item below is in `data/raw-2026.json` **right now**. Zero new API calls.
Zero cost. `fetch.py` already downloads all three views.

### Free, high-impact, already on disk

| Field | What you'd build |
| --- | --- |
| `teams[].logo` | Team avatars in every table. Instantly makes it look like a real product. Every team has one. |
| `teams[].abbrev` | 4-char names for mobile columns — fixes half the mobile table problem |
| `playoffTierType` + weeks 15–17 | **Real champions.** A bracket page. A true "Titles" column. §0. |
| `transactionCounter` | Acquisitions / drops / trades / **FAAB spent**. "Most Active Manager", "Waiver Warrior", "Set-and-Forget Award" |
| `currentProjectedRank` vs `draftDayProjectedRank` | "Biggest riser / biggest bust vs. draft day" — pure content |
| `home.pointsByScoringPeriod` | Per-period scoring detail behind each matchup |
| `record.streakType` / `streakLength` | ESPN's own streak, to cross-check yours |
| `teams[].eliminated` | "Mathematically eliminated" badge — people love/hate this |

### The whole rulebook you're ignoring

`mSettings` is fetched on every run and you use **exactly one field** from it
(`matchupPeriodCount`). Here is what's in the other 99%, for *this* league:

- **PPR scoring**, 43 `scoringItems` with per-position overrides
- **Auction draft**, $200 budget, 120s per pick
- **2 keepers** (`keeperCount: 2`)
- **$200 FAAB**, traditional waivers, 24h, processed Wed/Thu/Fri/Sat
- **6 playoff teams**, seeded by `TOTAL_POINTS_SCORED`, no reseeding
- **$25 entry fee** × 12 = a $300 pot (which is *exactly* what your prize table
  sums to — nice)
- **Trade deadline** as a real timestamp, 4 veto votes required

You told me you want a place to "view custom league rules." **You are already
downloading the complete rulebook every single morning and throwing it away.**
A "League Rules" page built from `mSettings` is the single highest
value-per-hour item on this list, it needs no new data source, and it's the
feature most likely to make someone from another league ask for their own copy.

Worth updating your roadmap note on keepers: keeper *stats* are indeed out of
scope (no roster data). Keeper *rules* — count, order type, auction budget —
are right there.

### Worth one more endpoint

`view=mRoster` would unlock lineup-level data: points left on the bench
(literal bench points), optimal-lineup analysis, "you started the wrong QB"
regret metrics. Same public league, same no-auth call, one more `time.sleep(1)`.
This is the biggest *genuinely new* capability available and it stays free. It
is also the one that makes the git-history model earn its keep, since roster
state is only observable live — once the week passes, ESPN's view of it moves
on and your commits become the only record.

---

## 6. Features people would actually use

Filtered hard for "would a real league member open this on a Tuesday."

**Tier 1 — the reasons someone opens the site**

1. **Weekly Recap.** Auto-generated, one screen: biggest blowout, closest game,
   highest scorer, the score to beat, who got unlucky (lost while scoring
   top-half), who backed in (won while scoring bottom-half). This is the
   group-chat-paste feature. All of it computes from data you already store.
2. **Owner pages.** `/owner/<name>` — career arc, season-by-season, best/worst
   weeks, full H2H list, title count. It's what the dead sidebar accordion is
   already promising. It also makes the site *linkable*: "look at my record
   against you."
3. **League Rules page** (§5). The thing you asked for.
4. **Playoff odds.** Not a full Monte Carlo — even a simple "you control your
   own destiny / need help" plus magic number is enough. Your "Wins to Clinch"
   column is reaching for this already but the label undersells it.

**Tier 2 — the fun stuff**

5. **Records book.** Highest score ever, biggest blowout, closest win, longest
   streak, most points in a loss. League lore.
6. **Awards / superlatives.** End-of-season, auto-computed. "The Bridesmaid"
   (most top-3 finishes, no title). "The Landlord" (best record vs. one
   opponent). "Luckiest Man Alive" (highest luck index). You already compute
   luck — it's begging for this.
7. **Power rankings** with movement arrows, weighted toward recent scoring.
   Every real fantasy site has these; yours would be actually principled given
   the dual-point rule.
8. **Head-to-head "compare" view.** Pick two owners, full history side by side.

**Tier 3**

9. Draft-day expectations vs. reality (`draftDayProjectedRank`).
10. "This week in league history" — the git-history play, below.

---

## 7. On history and git

Your instinct here is right and I want to reinforce it rather than
second-guess it.

Git *is* the correct store for this workload, for the reason `SPEC.md` §6
gives: append-only, timestamped, diffable, free, and it cannot expire or bill
you. For ~170 numbers a week it is not a compromise.

But you are **storing** history and not **reading** it. Nothing in the app ever
looks at a previous commit. Everything renders from the current JSON. The
history is an archive, not a feature.

Two things unlock it, both cheap:

- **Rank movement.** "Up 2 spots this week" needs last week's standings, which
  is one `git show HEAD~7:data/standings-2026.json` away. Arrows next to every
  rank. Enormous perceived-liveness gain for very little code.
- **Preserve what ESPN forgets.** ESPN's API is a *current-state* view.
  Rosters, waiver order, FAAB balances, projections — those move on and the old
  values are gone. Your daily commit is the only place they'd persist. That is
  the genuine argument for the git model over a database, and it gets stronger
  the more `mRoster`-shaped data you capture.

Keep the JSON as the source of truth. If you ever want cross-season queries,
load the committed files into an in-memory SQLite at build time and query that
— you get SQL without operating a database, and the files stay canonical. That
respects your §6 rule ("a DB sink is additive, never authoritative") exactly.

**Do not** stand up Postgres. It's what killed v1 and nothing here needs it.

---

## 8. What I'd do, in order

Ordered by (impact ÷ effort), not by interest.

**Fix first — these are bugs, and two of them are embarrassing**

1. Home sort crash (§2.1) — one guard clause
2. Chart `fill: false` + tooltip callback (§2.2, §2.3) — two lines
3. Finish the prizes `<tbody>` loop (§2.5) — it's half-committed right now
4. Commit the Week-0 fix already in your tree
5. Stop truncating scores with `| int` (§2.6)

**Then — highest value per hour**

6. **Playoff bracket + real champions** (§0). Biggest correctness win on the
   site. Rename "Titles" → "Reg. Season #1" and add a true "Championships."
7. **League Rules page** from `mSettings` (§5). You asked for it; the data's
   already local.
8. **Team logos + abbreviations.** Cosmetic, trivial, transforms perceived
   quality.
9. **OG meta tags** (§3). Makes the link you paste weekly into the product.
10. **"Last updated" stamp.** One line, real trust.

**Then — the multi-league work**

11. `score_to_beat()` generalized off `len(scores)` + a test (§4). This is a
    *correctness* bug for any non-12-team league, not a feature.
12. League ID / name / playoff count to config, sourced from `mSettings`
13. `docs/<league>/<season>/` and a league picker

**Then — the features**

14. Weekly Recap · 15. Owner pages · 16. Rank movement from git history ·
17. Records book · 18. Awards · 19. `mRoster` and real bench points

**Mobile, threaded throughout:** scroll affordances, sticky headers, the
rivalry matrix rethink, the nav that hides Careers.

---

## 9. What I would NOT build

Consulting is mostly saying no.

- **A database.** §6 of your spec is right. Revisit only if you add player-level
  weekly history for multiple leagues, and even then try SQLite-at-build-time
  first.
- **A JS framework.** Five static pages and three interactions. Vanilla is
  correct and you already won this argument.
- **User accounts / login.** The `localStorage` pin is the right 95% answer at
  0% of the cost, and it keeps you on the free tier and out of GDPR.
- **Live in-game scoring.** ESPN rate-limits it, you'd need polling, and it
  breaks the static model — for a product whose actual job is *settling
  arguments after the fact*.
- **Projections.** ESPN's are bad, yours would be worse, and nobody trusts
  either.
- **Writing tests for templates.** You have 35 good tests on the code that has
  logic. Rendering is verified by looking at it. The screenshot baseline you
  added is the right tool; don't unit-test Jinja.

---

## 10. Bottom line

You have built the hard part. The scoring engine is correct and tested, the
architecture is honest, the pipeline is idempotent and free, and it no longer
looks like 2018. That's the 80% most projects never reach.

What's holding it back is not capability, it's *distribution of attention* —
four real bugs shipped to production, and a daily download of a rich data
payload that gets 15% used. Fix the five bugs in an afternoon. Spend the next
weekend on the playoff bracket and the rules page. After that you have
something worth handing to another league, and the multi-league refactor is
mostly moving four constants into a config file.

One last time, because it's the thing I'd want to know: **your app currently
tells the league that Casey Pirsig won 2025. Davíd Huisken won 2025.** Start
there.

---

*Verified against commit `9fc6699` screenshots, `data/raw-*.json`
(2022–2026), and a live `build.py` run. Bugs in §2 were reproduced, not
inferred — the sort crash was executed, the champion mismatch was read out of
the raw bracket.*
