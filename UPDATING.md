# Keeping everything in sync

One file is maintained by hand. Everything else is generated from it.


## The architecture

```
                      ┌─────────────────────────┐
                      │     progress.json       │   the source of truth   
                      │  (this repo, root)      │
                      └───────────┬─────────────┘
                                  │
                    python3 sync_progress.py
                                  │
              ┌───────────────────┼───────────────────┐
              ▼                   ▼                   ▼
   ┌──────────────────┐  ┌────────────────┐  ┌──────────────────┐
   │ github.io/       │  │ index.html     │  │ Energy Systems   │
   │ progress.json    │  │ FALLBACK block │  │ Academy/         │
   │                  │  │                │  │ portfolio-       │
   │ live site reads  │  │ shown if the   │  │ progress.js      │
   │ this on load     │  │ fetch fails    │  │                  │
   └──────────────────┘  └────────────────┘  └──────────────────┘
         PUBLIC                PUBLIC              PRIVATE
```

**Why a script instead of everything fetching one URL:** the Academy dashboard opens
as a local file (`file://`), and browsers block cross-origin `fetch` from local files.
A generated `.js` file loaded with `<script src>` works everywhere, always.

---

## Site builds are automatic now

The site repo has a GitHub Action (`.github/workflows/build.yml`) that runs
`npm run build` and commits the generated HTML on every push, so for the
notes section you only ever push markdown. A second workflow drafts a weekly
reading round-up from daily.dev bookmarks every Sunday (`status: queued`,
never auto-published) — see `chiharum38.github.io/EDITING.md` for the flow.

## The weekly ritual · 3 minutes, Sunday

```bash
cd ~/power-systems-portfolio

# 1. tick off what you actually did
open progress.json        # or: code progress.json

# 2. check + propagate
python3 sync_progress.py

# 3. publish
git add progress.json && git commit -m "Update progress" && git push
cd chiharum38.github.io
git add -A && git commit -m "Update progress" && git push
```

That's it. The site updates in about a minute, and your private dashboard is already current.

---

## What to edit in `progress.json`

### Tick a milestone

```json
{ "name": "PyPSA network built", "done": true }
```

**`percent` is computed from milestones automatically**: you don't need to touch it.
The script recalculates and overwrites whatever number is there.

### Move a project's status

```json
"status": "planned"      "active"      "complete"
```

| Status | Site badge | Bar colour | Use when |
|---|---|---|---|
| `planned` | Planned | sand | Scaffolded, not started |
| `active` | In progress | terracotta | You're working on it right now |
| `complete` | Complete | sage | All milestones ticked, write-up published |

>  The script **refuses to sync** if a project is marked `complete` below 100%, or sits
> at 100% without being marked complete. That guard exists so the public site can't
> quietly overstate where you are.

### Update the learning stats

```json
"current_week": 7,
"hours_studied": 68,
"papers_read": 6,
"now_reading": "Kirschen & Strbac Ch 4. Participating in Markets",
"now_building": "02 · Offshore Wind. PyPSA network"
```

These feed the Academy dashboard panel. `now_reading` / `now_building` are the two
that make the panel feel alive.

---

## Useful commands

```bash
python3 sync_progress.py --check       # validate, print status, write nothing
python3 sync_progress.py               # full sync
python3 sync_progress.py --academy /some/other/path
```

`--check` prints a summary like:

```
  portfolio  1/5 shipped · 31% overall
    ● 01 ████████████████████ 100%  N-1 Contingency Screening + Wind Integration
    ◐ 02 ███░░░░░░░░░░░░░░░░░  14%  Offshore Wind Farm Grid Integration Study
    ○ 03 ███░░░░░░░░░░░░░░░░░  14%  ML-Based Grid Fault Detection and Location
```

---

## How the three layers relate

| Layer | Location | Purpose | Who sees it |
|---|---|---|---|
|  **Energy Systems Academy** | `~/Desktop` | Weekly plan, reading, papers, courses, reflection | You |
|  **power-systems-portfolio** | this repo | The actual code and results | Public, technical |
|  **chiharum38.github.io** | `chiharum38.github.io/` | The story, for recruiters | Public, everyone |

`progress.json` is the seam between them. It carries only the facts all three need:
what's done, how far along, and what you're working on now.

**Keep the boundary clean:**

- Reflections, doubts, grades, salary research  Academy only. Never here.
- Code, data, notebooks  this repo.
- Narrative, framing, CV  the site.

---

## The honesty rule

The badges are only worth having if they're true.

A recruiter who sees "In progress" on four empty folders learns that you overstate.
A recruiter who sees `14% · next: ENTSO-E API access` learns that you ship, track,
and tell the truth about where you are. **The second is far more persuasive**, and it
costs nothing except updating this file honestly.

If a project stalls, set it back to `planned` and move the milestones. That is a
completely acceptable thing for the world to see. Silently leaving it at "In progress"
for eight months is not.

---

## If something breaks

| Symptom | Cause | Fix |
|---|---|---|
| Site shows old numbers | GitHub Pages cache | Wait ~1 min, then hard refresh (⌘R) |
| Site shows the fallback | `progress.json` didn't get committed to the site repo | `cd chiharum38.github.io && git add -A && git push` |
| Academy panel empty | `portfolio-progress.js` not generated | Run `sync_progress.py`; check the `--academy` path |
| ` progress.json is not valid JSON` | Trailing comma, usually | The error prints the line number |
| Percent looks wrong | Milestones disagree with `percent` | Milestones win by design, tick the right ones |
