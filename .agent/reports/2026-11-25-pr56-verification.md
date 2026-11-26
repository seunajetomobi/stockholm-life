# Report: PR #56 CI fixes, verification and review (`pr56-verification`)

- **Task:** `pr56-verification`: find why PR #56 failed in CI, fix it without weakening tests, verify the fixes, and have them reviewed before a merge request
- **Agent:** Claude Code. Independent review by Codex (read-only)
- **Date:** 2026-11-24 to 2026-11-25
- **Commits:** PR head before the fixes `9bad042`; CI fix commit `89824b5e662c4473cb3f1a2e24f713da98b05dd0` (superseded); save fix commit and final head `183227dfc73594b6752605f23d2fd237086edacb`; base `main` `fb15b69`; merged as `8d7409e` (from `git log --first-parent origin/main`, 2026-11-25). This report was updated on 2026-11-25 on the branch `docs/status-2026-11-25`
- **Branch and pull request:** `feat/title-page`, PR #56. **Merged** on 2026-11-25 (GitHub: `mergedAt` 08:26:39 Z, merge commit `8d7409e`, head `183227d`). **Not deployed**: `live` is `76ec825`, the tree of `f10f606`, which does not include #56
- **Files changed by the CI fix commit `89824b5`:** `index.html` (2 lines), `tests/game.py`, `tests/test_name.py`, new `tests/test_harness.py`, and one call site or two in each of `tests/test_boat_rides.py`, `test_city_data.py`, `test_format.py`, `test_geography.py`, `test_save_safety.py`, `test_sun.py`, `test_tables.py`, `test_time_rules.py`, `test_transit_rides.py`, `test_vehicle_lanes.py`

## Summary

PR #56 (title page, new-life form, menus, real Stockholm time by default) failed CI for four separate reasons, none
of them a defect in the game's behaviour for players. One commit fixes all four. The full required CI run on that
exact head passed, and Codex's independent review of the four changes found no issue and recommends merging.
A separate save-safety review of the whole PR then found, and the author reproduced, a blocker outside those four
changes: starting a new life from the title page erases the current life without a warning or a backup. `89824b5`
was therefore **not fit to merge**. Fix commit `183227d` closes that blocker (and a second path, the panel's
"Start over"). It passed CI on its second attempt (the first failed only on the known flaky vehicle-lane test), and
the save-guard, reviewer and Codex reviews found no open blocker or major. The owner approved the merge and PR #56 was merged at that head as `8d7409e`; see "Since the blocker was found" below.

## The failures and their causes

Run [45375413224](https://github.com/seunajetomobi/stockholm-life/actions/runs/45375413224) on `5c9b1b3`:
`44 failed, 525 passed, 1 xfailed, 51 errors in 9291.96s (2:34:51)`. Run
[45416429408](https://github.com/seunajetomobi/stockholm-life/actions/runs/45416429408) on `9bad042` was cancelled at
the 180-minute job limit, about 92 % through, with the same files failing plus `test_name.py` and
`test_loading_flash.py`.

| | Cause | Tests affected | Fix |
| --- | --- | --- | --- |
| A | #56 makes the title page and real time the defaults. `tests/game.py new_page` set the opt-outs, but 15 contexts in 10 files were made with `browser.new_context()` directly and met the title page and the real clock | 51 set-up errors (time_rules 35, boat_rides 7, transit_rides 7, vehicle_lanes 2) and most save-test failures | One helper `game.new_context()` used everywhere; `tests/test_harness.py` fails if a test calls `browser.new_context(` directly |
| B | Chromium 145 (the CI browser), with Playwright request interception active, reports a network `HEAD` as `net::ERR_ABORTED` although the response arrives. `syncServerTime()` used a `HEAD` of the page | every test that asserts no failed local request (smoke boot, each module's `test_game_uses_the_module`, save round trips) | The server time comes from the `Date` header of a small `GET` of `manifest.webmanifest` |
| C | The new Quit button makes the map-button column five buttons tall; at 360×640 it reaches the station message strip's place, so the strip was moved | `test_m14.py::test_strip_follows_layout_changes` | On phones the strip ends left of the button column (`right:62px`) |
| D | Owner request: the first O of the loading wordmark is the progress indicator, so the exact markup in `test_name.py` no longer exists | `test_name.py::test_title_and_visible_names_say_stockholmsliv` | The test checks the wordmark's text instead of its markup |

## Tests and results

Local, with the CI's browser and test library (Chromium 145.0.7632.6, Playwright 1.58.0):

| Run | Result |
| --- | --- |
| Fix A alone on `9bad042`: harness guard, 3 save tests, `test_transit_rides.py` | 11 passed |
| Fix B alone: smoke boot, `test_sun::test_game_uses_the_module`, a save round trip | 3 passed |
| Fix C alone: `test_m14::test_strip_follows_layout_changes` | 1 passed |
| Unmodified `9bad042`: `test_loading_flash.py`, `test_name.py` | 1 failed (the markup check), 3 passed |
| Guard on unmodified `9bad042` | fails, listing the direct calls |
| All fixes, full suite | 264 of 271 passed before the run was stopped by its time limit; the rest run separately passed, except the known flaky vehicle-lane test (below) and `test_name.py` before its update |
| `89824b5`: `test_name.py`, `test_harness.py` (2026-11-25) | 3 passed |

CI on the exact head, run [45465374434](https://github.com/seunajetomobi/stockholm-life/actions/runs/45465374434):

| Check | Required | Result |
| --- | --- | --- |
| `tests-syntax` | yes | success, 5 passed |
| `tests-browser` | yes | success, `622 passed, 1 xfailed in 7333.05s (2:02:13)`; the xfail is `test_traincam.py::test_place_label_after_getting_off` (KNOWN_ISSUES L10) |
| Workers Builds: stockholmsliv | no | failure; it also fails on `main` and is not part of the ruleset |

## Independent review

**Codex** (Codex CLI 0.171.0-alpha.13.2, read-only sandbox, 2026-11-25), given the full diff `fb15b69..89824b5`,
the fix commit, this evidence and the four questions:

| Change | Codex finding |
| --- | --- |
| 1. `tests/test_name.py` | No issue. The text check still requires `Stockholmsliv`; the brand and hero checks remain |
| 2. `index.html:536` `right:62px` | No issue. Matches 42 px buttons + 16 px edge + 4 px gap; at 320 px the strip keeps 250 px, above the placer's 160 px minimum; applies to both control types. Keep the inset aligned if the controls change size |
| 3. `game.new_context` and guard | No issue with the converted call sites; init scripts run before page scripts, also after reloads. The text guard does not catch aliases (`b.new_context`), `conftest.py` or other support files: a limited guard (informational) |
| 4. Manifest `GET` | No issue. The file is published (not in `.assetsignore`), fetched with a cache-busting query and `no-store`; the midpoint calculation is unchanged; nothing else used the old `HEAD` |
| Verdict | **MERGE**. Codex reviewed the fix commit only, not the rest of the PR |

**Save safety** of the whole PR (a Claude Code review agent following the save-system reviewer role, 2026-11-25;
not independent of the author's model). Verdict: **unsafe as it stands**, one blocker. The save format is unchanged
(`migrate()`, the keys and `v:6` with `t0` are as on `main`).

| Severity | Finding | Status |
| --- | --- | --- |
| **Blocker** | Title page → Start → "Start a new life" while a life is active (`startChoice`, `index.html:5879`) goes straight to the new-life form; submitting it runs `lifeFromForm` → `newGame()` (`index.html:1290–1300`), which ends in `save()` over the active slot. No warning and no `slotBackup(…,'before-replace')` copy. The warning text exists (`newTitle`/`newBody`, "Your current life in Stockholm will be lost…") in `titleNewLife()` (`index.html:6072`), but nothing calls that function. The Saves screen's "Start over" (`slotRestart`, `index.html:1486–1488`) does make a verified copy first | **Reproduced** by the author in the browser at `89824b5`: a life "Erik" was saved (`stockholm-life-v4` and `stockholm-life-slots-v1` held it); after "Start a new life" no `localStorage` key held it, no dialog or warning appeared. `main` has no such path, so #56 introduces it |
| Minor | "Save and quit" reloads even when `save()` writes nothing (journey, arrest, driving lesson, or a pending/blocked/superseded save state; `index.html:1384–1387`, `6123`), without telling the player | Reported by the agent; not reproduced |
| Minor | A device clock that is behind, with the server-time sync failing, rebases `t0` to the saved day, so elapsed days are dropped (no money lost) | Reported; not reproduced |
| Minor | A migrated life has no `S.flags.rolled`, so the first sleep after the upgrade may repeat that day's bookkeeping once | Reported; not reproduced. Comes from the #53 commits |
| Informational | Bookkeeping runs only in `sleep()` and once however many days passed (known: the midnight-rollover slice is not built) | Known limitation |
| Test gap | No test covers "Quit without saving" (`SV.noSave`) or a new life over an existing one | Confirmed by search |

Checked by the author on 2026-11-25: the live site returns 404 for `manifest.webmanifest` because the file is new in
#56 (commit `9bee5b6`) and live runs an older version; the 404 still carries a `Date` header. It is published once
#56 is deployed.

## Since the blocker was found (2026-11-25)

**Fix commit `183227d`** (`183227dfc73594b6752605f23d2fd237086edacb`) on `feat/title-page`:

- `lifeReplaceCopy()` makes a verified `before-replace` copy of the current life before the title page's new-life
  form or the panel's "Start over" replaces it. The newest 3 copies are kept (`savePrune`, `SLOT_KEEP`).
- If the copy cannot be made (storage full, or a busy or gated slot), nothing changes and the form or modal shows why.
- The title page now asks first (`titleNewLife`).
- Five new tests in `tests/test_save_slot_ui.py`:
  `test_title_new_life_asks_first_and_keeps_a_copy`, `test_title_new_life_with_a_failed_copy_changes_nothing`,
  `test_panel_start_over_keeps_a_copy`, `test_panel_start_over_with_a_failed_copy_changes_nothing`,
  `test_title_new_life_keeps_the_newest_three_copies`. They fail on `89824b5` and pass on `183227d`.

**Reviews of `183227d`:**

| Reviewer | Verdict |
| --- | --- |
| Save-guard agent (Claude Code review agent) | SAFE. It found the panel "Start over" path as a second major, which was then guarded too |
| Reviewer agent (Claude Code) | No blocker, no major |
| Codex (independent) | MERGE, no findings (after the pruning test was added) |

**CI on `183227d`**, run [45521784213](https://github.com/seunajetomobi/stockholm-life/actions/runs/45521784213):

| Attempt | Result |
| --- | --- |
| 1 | Failed only `tests/test_vehicle_lanes.py::test_traffic_stays_on_carriageways` ("cars on road classes 4 to 9 outside the carriageway: [[9, -0.0228, 0.2745]]"), the known flaky test (about 1 run in 21): `1 failed, 626 passed, 1 xpassed in 9293.15s (2:34:53)` |
| 2 | The failed job was rerun without changing any test: `627 passed, 1 xpassed in 6665.10s (1:51:05)` |

`tests-syntax` and `tests-browser` are success on `183227d`.

**Release agent gate check:** READY. The head matches, the required checks are green on the exact head, the branch is
up to date with `main` (`fb15b69`), and there are no secrets or conflict markers. One minor: `tests/test_title_page.py`
line 39 writes a debug screenshot to a `/tmp` path; to be changed to `game.shot()` in a follow-up after the merge, not
in #56 (a change now would restart a 2-hour CI run).

**Status (2026-11-25):** merged as `8d7409e` at head `183227d`, as the owner approved. Not deployed. The merge command used is not recorded here (not verified); GitHub shows the merge commit and the head.

**Related pull requests, state on 2026-11-26 (GitHub)**

| PR | State |
| --- | --- |
| #59 CI in six parallel browser shards | Merged `0ce3ec0`, head `e0be1cc`, run `45576401745` (about 28 minutes) |
| #58 car lane offset fix | Merged `201caa9`, head `3240c74`, run `45583536768` |
| #54 search-engine basics | Merged `90c30eb`, head `70cce01`, run `45588928081` |
| #55 accounts, events and game rooms proposal (documentation) | Merged `51010b8`, head `accdf3a`, run `45596597307` |
| #57 arrivals hall | Merged `1389ee6`, head `7ff2ceb`, run `45621575885` (the earlier draft noted a conflict with #56 in `index.html`; how it was resolved is not verified) |
| #60 proof for #59 | Closed, not merged (its run `45578326828` failed as intended) |
| #61 title menu | Merged `6e6e9a3` on 2026-11-26, head `bdea3ab` (its first head `6d525a9` failed in shard 5, `test_title_page.py::test_top_widgets_language_and_options`) |
| #62 click outside menus | Open, head `853ed3b`; run `45783926234` failed in shard 6 on the known flaky `test_vehicle_lanes.py::test_traffic_stays_on_carriageways` (KNOWN_ISSUES M27) |
| #63 to #67 | Open, green on 2026-11-25, behind `main` |

## Other actions in this task

- PR #53 closed as superseded (owner approval): its head `4c1a9b9` is an ancestor of `89824b5` (and so of `183227d`). Branch kept. GitHub shows it CLOSED, not merged.
- PR #19 closed as stale (owner approval); GitHub shows it closed on 2026-11-24 23:42 Z, not merged. Branch kept.

## Known problems and limitations

- `test_vehicle_lanes.py::test_traffic_stays_on_carriageways` fails intermittently on unmodified `main` (1 of 2 local
  runs; a vehicle about 10 m off the carriageway). Pre-existing; passed in run 45465374434. It failed again in
  attempt 1 of run 45521784213 (about 1 run in 21) and passed on rerun.
- `tests/test_title_page.py` line 39 writes a debug screenshot to a `/tmp` path (minor; follow-up after the merge).
- `test_loading_flash.py` failed once in run 45416429408 and has passed every time since. Not explained; no fix made.
- The `right:62px` inset is tied to today's 42 px map buttons. The interface branch (`feat/ui-v2`) changes those
  buttons on short phones; its integration must re-run `test_m14.py`.
- The CI browser is a software renderer; nothing here measures real devices.

## Outstanding work

1. Done: the save blocker is fixed in `183227d` and merged in #56 (`8d7409e`).
2. Not done: change the `/tmp` screenshot in `tests/test_title_page.py` to `game.shot()` (not verified whether #61 or any later pull request did this; #61 is merged).
3. Open pull requests and their state: `.agent/QUEUE.md`. Real time is on by default on `main` since #56; the owner decided on 2026-11-26 that it must not be the default in a public release until R3 is verified (task `realtime-default`).
4. Deployment: nothing from #56 is live. Moving `live` needs the owner's approval.
5. Not verified in this update: the Codex and agent review verdicts above are copied from the author's earlier record and were not re-run; the arrivals-hall corrections and the graphics branch `feat/gfx-lighting` have no pull request that this update could check.

## Recommended next action

Do not promote `main` to `live` while real time is the default. Ask the owner about the #62 re-run.
