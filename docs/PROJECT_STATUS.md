# Project status

The single authoritative status of Stockholm Life. Other documents link here instead of keeping their own status summaries. The current task and the tasks after it are in [`.agent/QUEUE.md`](../.agent/QUEUE.md).

**Verified 2026-11-04 at `main` `492a8e5`** (GitHub API, `git ls-remote`, the live `version.txt`). Refreshed with the next meaningful project or documentation update, not after every merge, so check the date and SHA before relying on it.

## Code and release

| | Commit | Notes |
| --- | --- | --- |
| `main` | `492a8e5e1c2177d65468096cf283b023543660ae` | Merge of PR #11 (status update after PR #10), 2026-11-03 10:35 Z |
| Live site | `870fe309543c6eb375e6e150423002a09763a3db` | `version.txt` on GitHub Pages; last successful deployment `7465401024` (run `41249126992`), 2026-10-31 22:58:50 Z |
| Merged, **not deployed** | | PR #3 pendeltåg camera and phone message strip (`40d913e`); PR #4 strip clear of every control (`3d04635`); PR #6 strip follows layout changes (`d9b8882`). PR #5 (documentation, `b0ad590`), PR #7 (agent workspace, `bb93709`), PR #8 (live verification tool, `d91a5d4`: `tools/`, `tests/` and documentation only), PR #9 (documentation, `3ac8b53`), PR #10 (documentation, `2d9d753`) and PR #11 (documentation, `492a8e5`) do not change the published files |
| Open pull requests | | None when verified. M1a is on branch `feat/m1-save-safety`, with a pull request opened after this check; not merged (see below) |

Publishing happens only through the manual "Deploy to GitHub Pages" workflow with the `github-pages` approval; merging into `main` does not change the live site ([TECHNICAL_ARCHITECTURE.md §4](TECHNICAL_ARCHITECTURE.md)).

## Milestone

**M0 — Stabilise: in progress.** No milestone is complete. Scope and acceptance: [MASTER_ROADMAP.md](MASTER_ROADMAP.md#m0--stabilise).

| M0 item | Status | Evidence |
| --- | --- | --- |
| Automated tests in CI as required checks; approval-gated manual deployment; Pages published by GitHub Actions; `main` protected by a ruleset; Actions hardened | Done | PR #1, PR #2; ruleset "Protect main" (`tests-syntax`, `tests-browser`, strict up-to-date) |
| Pendeltåg camera and M14 merged | Done | PR #3 (`40d913e`) |
| Message strip clear of every control | Done | PR #4 (`3d04635`); timing fix PR #6 (`d9b8882`), KNOWN_ISSUES M16, M17 |
| Project documentation in the repository | Done | PR #5 (`b0ad590`) |
| Real-device check of the camera and the message strip | **Not complete** | Seated-train frame-rate comparison finished on one laptop ([TEST_PLAN.md §6](TEST_PLAN.md)). A manual desktop session took place on 2026-11-02. Remaining manual desktop checks and physical-device checks have not yet been completed. No physical iPhone, Android or tablet test has run. Checklist in [TEST_PLAN.md §4](TEST_PLAN.md); KNOWN_ISSUES M15, M18 |
| Live verification tool | Done (merged; a tool, not part of the published site) | PR #8 (`d91a5d4`): `tools/live_check.py` and `tests/test_live_check.py` |
| Deploy `main` and verify it live | **Not done** | Live is `870fe30` (above); verify with `tools/live_check.py --expect <sha> --rounds 4 --interval 300` |
| Flights relay redeployed with `/waittime` | **Not done** | Probed 2026-11-01: `/waittime` answers with the old help text listing only `/flights` and `/news`; needs a redeploy and the `SWEDAVIA_KEY` secret (KNOWN_ISSUES M1) |

## Current task and next steps

- **Current:** M1a save safety (`m1a-save-safety`), which the user approved on 2026-11-04 as a narrow exception to "M1 after M0". It does not change the save format. Not merged and not deployed. `m0-deploy` can still ship an earlier exact commit from `main` without it.
- **Paused:** the remaining manual desktop checks (`m0-desktop-checks`), started and paused by the user; they resume from the recorded stopping point.
- **Next:** see [`.agent/QUEUE.md`](../.agent/QUEUE.md). In short: finish M0 (remaining manual desktop checks, physical-device checks, deploying `main` and checking it with the tool, the relay), each with the user's approval, then the rest of M1 (save and state).

## Latest verification results

| What | Result |
| --- | --- |
| M15 seated-train frame-rate comparison, 2026-11-03 (`870fe30` against `3ac8b53`, one Intel UHD 620 laptop; not an M7 test) | **Comparison complete; M15 overall not complete.** All 18 required results exist; 22 sessions ran, and 4 are preserved as invalid and excluded. Same camera: no meaningful difference in any tested scene, Rich or Fast. Above ground, You camera against Eyes: −5 fps on Fast, −3 fps on Rich. Each arm's lowest 1-second window is below 30 fps in every scene; typical fps is above 30 only on Fast above ground in the first-person arms. Rich above ground, `870fe30` against You: inconclusive. Evidence is private and outside this repository. Details and limitations: [TEST_PLAN.md §6](TEST_PLAN.md) |
| M1a, branch `feat/m1-save-safety`, local with system Chrome (2026-11-04), before a final correction to two comments | Full suite 217 passed, 1 xpassed (L10) in 58 min, pytest exit code 0. Negative control on `492a8e5`: 40 of 47 new tests fail. CI results are on the pull request. Hidden tab and back/forward cache are simulated; no manual check has run |
| PR #10 CI on `dcb8521` (run `41610491896`) | `tests-syntax` 3 passed; `tests-browser` 171 passed, 1 xfailed (L10) in 26 min; GitGuardian passed. `main` `2d9d753` merges exactly this head |
| `tools/live_check.py` against the live site, 2026-11-01 | `--expect 870fe30`: PASS (12 of 12 files match by blob ID; data valid; game started in headless Chromium with all 11 same-origin files verified). `--expect bb93709`: `version.txt` and `index.html` differ, 10 data files match; one round, so INCONCLUSIVE ("unconfirmed mismatch") as designed |
| PR #8 CI on `7931618` (run `41387669915`) | `tests-syntax` 3 passed; `tests-browser` 171 passed, 1 xfailed (L10) in 30 min; GitGuardian passed. `main` `d91a5d4` merges exactly this head |
| Full suite with the live-check tests (local, `7931618`'s files) | 171 passed, 1 xfailed (L10) in 31 min, pytest exit code 0. Of three full runs, the first had one failure in `test_m14.py::test_strip_avoids_controls_phone_tablet` (details not captured); it passed alone and in the other two runs, and PR #8 does not touch the game or that test. `test_live_check.py` also passed (139) offline, in a network namespace with only loopback. Earlier, on `4ff1aa4`: 158 passed, 1 xfailed |
| PR #6 CI on `9ac0dcf` (run `41291235894`) | `tests-syntax` 3 passed; `tests-browser` 32 passed, 1 xpassed (L10); GitGuardian passed. `main` `d9b8882` has the same tree as `9ac0dcf` |
| PR #6 regression test `test_strip_follows_layout_changes` | Fails on `3d04635` (negative control); passed 5 of 5 repeats with the fix |
| PR #5 CI on `c9575c7` (run `41273927661`) | Attempt 1: one browser test failed (the M17 timing defect); attempt 2: 31 passed, 1 xpassed |
| Known flaky result | `test_place_label_after_getting_off` is an `xfail` for L10 that passes in some runs |
| Not verified | Real devices; frame rate beyond this one laptop's seated-train comparison; a full pendeltåg ride between stations (TEST_PLAN.md §3) |

## Where merged work came from

| Branch | Commit | Merged as |
| --- | --- | --- |
| `fix-m14-phone-message-strip`, `pendeltag-camera` | `742403b`, `df54793` | Original M14 and camera commits, integrated by cherry-pick in PR #3 (`40d913e`) |
| `fix/m14-short-screen` | `081682f` | PR #4, `3d04635` |
| `docs/project-baseline` | `c9575c7` | PR #5, `b0ad590` |
| `fix/m14-layout-recalculation` | `9ac0dcf` | PR #6, `d9b8882` |
| `chore/agent-workspace` | `d75ea07` | PR #7, `bb93709` |
| `feat/live-check` | `7931618` | PR #8, `d91a5d4` |
| `docs/status-after-pr8` | `115539e` | PR #9, `3ac8b53` |
| `docs/m15-three-arm` | `dcb8521` | PR #10, `2d9d753` |
| `docs/status-after-pr10` | `75dc8cc` | PR #11, `492a8e5` |
