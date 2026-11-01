# Known issues

Current as of 2026-11-01, `main` at `3d04635`. First written in the audit of 2026-10-31 (at `870fe30`); numbering is kept so earlier references stay valid. Severity: **High** = can lose progress, break releases or block the roadmap; **Medium** = visible defect or significant risk; **Low** = minor.

Evidence: **[B]** headless browser run, **[T]** automated test, **[C]** code reading, **[L]** live probe or GitHub API, **[D]** documented in CLAUDE.md.

## Code and release baseline

| Ref | Commit | Contents | Live? |
| --- | --- | --- | --- |
| `main` | `3d04635` | Game of `870fe30` + pendeltåg camera + M14 fix (PR #3) + responsive message-strip placement (PR #4), CI and deployment workflows, tests | **No.** Merged, not yet deployed |
| Live site | game files of `870fe30` | Deployment `7465401024` (run `41249126992`, 2026-10-31 22:58:50 Z), published by GitHub Actions; `version.txt` = `870fe309543c6eb375e6e150423002a09763a3db` | Yes |
| `fix/m14-short-screen` | `081682f` | Responsive message-strip placement (PR #4), merged into `main` as `3d04635` | No (on `main`, not deployed) |
| `fix-m14-phone-message-strip`, `pendeltag-camera` | `742403b`, `df54793` | Original camera and M14 commits (preserved; integrated via cherry-pick in PR #3) | — |

Publishing happens only through the manual "Deploy to GitHub Pages" workflow with approval; merging into `main` does not change the live site.

## High

| # | Issue | Evidence | Suggested fix |
| --- | --- | --- | --- |
| H3 | **Save failures are silent.** `save()` wraps `localStorage.setItem` in an empty `catch`; full or blocked storage loses progress without a message | [C] | Roadmap M1 |
| H4 | **Single save slot in localStorage only.** Clearing site data, private browsing or another browser loses the life; no export | [C][T] | Roadmap M1 |
| H5 | **A corrupted save is overwritten silently** with a fresh start | [T] | Roadmap M1: keep it under a backup key and tell the player |
| H6 | **One 823 kB, 5,340-line file with a 2,950-line closure** (`buildWorld`) makes every change risky and blocks testing parts in isolation | [C] | Roadmap M3 |

## Medium

| # | Issue | Evidence | Suggested fix |
| --- | --- | --- | --- |
| M1 | The deployed flights relay is older than `tools/flights-worker.js`: no `/waittime` route, so Arlanda security queue times are always unavailable | [L] | Redeploy the Worker; add `SWEDAVIA_KEY` (M0) |
| M2 | Below 20 fps the city runs slower than real time (each frame simulates at most 50 ms in `tick`) | [C][B] | Fixed-timestep simulation (M2/M7) |
| M3 | About 0.5 % of auto-walk time passes through building footprints (narrow passages in Gamla stan) | [D] | Navmesh or sidewalk graph |
| M4 | Start-up downloads about 12 MB (37 MB raw) and parses it on the main thread; 194 MB JS heap after boot | [L][B] | Per-tile files, worker parsing (M7) |
| M5 | GPU cost on phones: logarithmic depth buffer, soft shadows, pixel ratio up to 2 | [C] | Measure first (M7) |
| M6 | Leaving the page does not save (no `pagehide`/`visibilitychange` handler) | [C] | M1 |
| M7 | Reloading inside an interior, the station, a train or a car returns you to the street; only Arlanda is restored | [C] | M1 (saved world state) |
| M8 | Five core functions are reassigned later in the file (`newGame`, `sleep`, `spendTime`, `addBill`, `log`), so behaviour depends on script order | [C] | Explicit hooks (M3) |
| M9 | 36 empty `catch(e){}` blocks hide real errors | [C] | Log errors at least (M3) |
| M10 | The main data files (`b`, `r`, `m`, `t`, models) have no generator in the repository | [C] | Commit the pipeline (M7) |
| M11 | three.js r128 via CDN without Subresource Integrity; first load needs cdnjs, jsdelivr and Google Fonts | [C] | SRI or vendored files |
| M12 | Vision gaps: no mission system, no NPC schedules or memory, work is a menu action, interiors are generic and POI-only, no home ownership, time stops when you stand still | [C] | Roadmap M2, M4–M6 |
| M13 | The flights relay's CORS allows only GitHub Pages, `localhost:8000` and `127.0.0.1:8000` | [L][C] | Document, or allow a configurable list |
| M15 | **The pendeltåg camera (PR #3) and the message-strip fixes (PR #3, PR #4) are merged but not deployed**, and not yet checked on a real GPU, phone or tablet | [L] | Real-device checklist (TEST_PLAN.md §4), then deploy `main` (M0) |

## Low

| # | Issue | Evidence | Suggested fix |
| --- | --- | --- | --- |
| L1 | Diary entries are inserted with `innerHTML` and include the player's own name unescaped (self-XSS only) | [C] | Escape log text |
| L2 | GLTFLoader warns repeatedly: "Custom UV sets in KHR_texture_transform not yet supported" | [B] | Re-export the models, or ignore |
| L3 | One external 404 per session: an adsbdb.com route lookup for an unknown callsign (seen: `DFL5980`) | [B] | Treat 404 as "no route" quietly |
| L4 | On phones the developer credit sits partly under the dock | [B] | Move it |
| L5 | About 225 unseeded `Math.random()` calls make runs irreproducible | [C] | Seeded RNG in test mode (M8) |
| L6 | Stockholm City is drawn 26 m deep (35–44 m in reality) with one island platform; track numbers not verified | [D] | Accept or survey |
| L7 | Facts (fees, prices, rules) were checked in October 2026 and will date | [D] | Yearly review |
| L8 | Övre hallen and the long-distance platforms are not built (stated in the game) | [C] | Later |
| L9 | On phones the station/train prompt (`#csPrompt`) and ride HUD (`#csHud`) ignore part of their phone layout: the phone rules come before the base rules, which win (same cause as the original M14). The prompt stays centred and only as wide as its text; from 601 to 640 px it sits at the base position | [C][B] | Same approach as M14 when wanted |
| L10 | After getting off the pendeltåg, the place label sometimes stays on "Pendeltåg 41 · Stockholm City". Intermittent: wrong in most local runs, right in the PR #3 CI run (an `xfail` test records it) | [T] only via a getting-off shortcut, not a real arrival | Check after a real ride; refresh the label in `jrAlight` if confirmed |
| L11 | The console logs "THREE.Color: Unknown color #4" once per session; source not confirmed | [B] | Find the caller |
| L12 | The CI step that installs Playwright's Chromium (`--with-deps`) can stall: in PR #4's first run it hung until the browser job's 45-minute limit and the run was cancelled (normally about 20 s); a re-run passed. The job limit is the only timeout | [L] run `41259068792` (attempt 1 cancelled, attempt 2 passed) | Re-run; consider a timeout on that step (workflow change, needs review) |
| L13 | Rolling back by switching Pages to the legacy branch builder may now be blocked: full-SHA pinning is required for actions, and GitHub's built-in legacy workflow may not pin its actions. Unverified | [C] reasoning only | Prefer rollback through the Deploy workflow (an earlier commit) |
| L14 | Some station/train controls overlap each other (not the message strip): at 768×1024 the ride HUD covers part of the "Next up" card; on phones held sideways (640×360, 844×390) the "Sit down?" prompt and the joystick overlap the ride HUD. At 640×360 a three-line message has no free place at all, so the strip is drawn beneath the Run button (by design: Run stays on top and takes taps) | [B] PR #4 test screenshots | Lay out the ride HUD and prompt for tablets and landscape (with L9) |

## Resolved

| # | Issue | Resolution | Verification | Still open |
| --- | --- | --- | --- | --- |
| H1 | Every push to `main` was a production release | Pages published by GitHub Actions since 2026-10-31; only the manual Deploy workflow publishes, behind the `github-pages` approval gate; `main` protected by the "Protect main" ruleset | [L] the legacy deployments started by merging PR #1 and PR #2 were stopped at the approval gate; merging PR #3 under the Actions source published nothing; the first Actions deployment was verified live | — |
| H2 | No automated tests in the repository | `tests/` (PR #2, PR #3): syntax, smoke, save, layout, M14, train camera; required checks `tests-syntax` and `tests-browser` | [T] 27 passed + 1 xpass on PR #3's CI run; 31 passed + 1 xpass on PR #4's (`41269872906`) | Unit tests of rules (TEST_PLAN.md §3) |
| H7 | Uncommitted pendeltåg camera change in the working tree | Committed as `df54793`, merged via PR #3 (`40d913e`) | [T] camera tests | Real devices (M15) |
| M14 | On phones the message strip stretched over most of the screen (365 px tall at 390×844) | `742403b`: phone rule uses `#csLine`; the strip lifts above an open prompt. Merged via PR #3 | [T] 29–44 px tall at 390 and 520 px; desktop unchanged; the test fails on the old code | Short and tablet screens: resolved as M16; real devices (M15) |
| M16 | The station/train message strip could cover controls on short, tablet and landscape screens: the ride HUD (10 px at 360×640, 19 px at 768×1024), the places bar's Home button (768×1024), the "Next up" card and the prompt (844×390, 1024×768), and it could leave the top of the screen (640×360) | PR #4 (`081682f`, merged as `3d04635`): the strip keeps its CSS place unless it would cover a visible control or leave the screen. `csLineFit()` measures the rendered boxes of every visible control (ride HUD, prompt, top bar, "Next up", places buttons, zoom, joystick, Run, dock, care chip) and moves the strip to the nearest free place: the same height, narrowed between side columns, or moved up or down. With no free place it sits where it overlaps least, beneath the controls. The strip never takes taps (`pointer-events: none`). No control is hidden, disabled, shrunk or moved; desktop positions where nothing is in the way, and the camera and train, are unchanged | [T] 4 new tests check every visible control at 360×640, 375×667, 390×844, 520–768 px wide, 640×360, 844×390, 1024×768 and four desktop sizes (station, boarding with the prompt open and three lines tall, seated; two- and three-line messages), plus an explicit 768×1024 Home-button test and the no-room fallback. They fail on the earlier PR #4 commit `adc765d` (31 of 80 phone/tablet and 20 of 32 desktop layouts covered a control) and pass on `081682f`; CI 31 passed + 1 xpass | Not deployed; real devices including safe-area insets (M15); control-on-control overlaps (L14) |

## Documented exceptions

| # | Exception | Status |
| --- | --- | --- |
| E1 | **Stale legacy Pages build records.** Under the legacy branch builder, merging PR #1 (`dd05829`) and PR #2 (`bb9fb74`) started builds whose deployments were rejected at the approval gate (runs `41219679242`, `41225883718`; deployments `7461220671`, `7462096847`, both `failure`). The build records stayed `building` (build `1330206875` later became `errored`; build `1330356267` remained `building`). The decision: do not repair them; while Pages used the legacy builder, deployment identity could pass on corroborating evidence only when all of these held: the attempted deployment was rejected or failed and the deployments API showed its final failure; the last successful deployment was the expected game commit with no newer success; all 11 live game files matched that commit and were fetched from origin after the operation; browser startup passed. Each such step was verified with 6 live rounds over 17 minutes | **Closed.** Pages switched to GitHub Actions on 2026-10-31 at 22:12:47 Z; identity now comes from the deployments API, and the Pages status read `built` after the first Actions deployment. Kept as a record |

## Not issues (checked)

- All 14 static buttons have handlers; no dead controls.
- Simulated data (Bromma planes without the relay, station timetables, arrivals board, FX fallback, ISK returns, housing queue speed) is labelled as simulated in the game.
- External text from news feeds and chat is HTML-escaped (`esc2`).
- The flights relay is connected: `FLIGHT_RELAY_DEFAULT` points to the deployed Worker and live flights work.
- No duplicate function declarations in `index.html`; `person`, `spot` and `walkTo` are reused as unrelated local helper names, not overrides.
