# Project status

The single authoritative status of Stockholm Life. Other documents link here instead of keeping their own status summaries. The current task and the tasks after it are in [`.agent/QUEUE.md`](../.agent/QUEUE.md).

**Verified 2026-11-08 at `main` `23906b7`** (GitHub API, `git ls-remote`, the live `version.txt`). Refreshed with the next meaningful project or documentation update, not after every merge, so check the date and SHA before relying on it.

## Code and release

| | Commit | Notes |
| --- | --- | --- |
| `main` | `23906b75872ac1398a5bd95e2e9ff791e05296c4` | Merge of PR #18 (the "Sit down?" prompt fix), 2026-11-08 17:32 Z |
| Live site | `870fe309543c6eb375e6e150423002a09763a3db` | `version.txt` on GitHub Pages; last successful deployment `7465401024` (run `41249126992`), 2026-10-31 22:58:50 Z. 49 commits behind `main`; it does not include the merged work below |
| Locally qualified | `6e9ac76ba8f07051fe96b620e0c3e03cec5343cc` | The commit the isolated local test runner was qualified on, 2026-11-07, when it was `main` ([TEST_PLAN.md §7](TEST_PLAN.md)). `main` has moved on since (PR #14, #16, #17, #18); the latest full-suite evidence is CI run `42496081159` below |
| Merged, **not deployed** | | Game changes: PR #3 pendeltåg camera and phone message strip (`40d913e`); PR #4 strip clear of every control (`3d04635`); PR #6 strip follows layout changes (`d9b8882`); PR #12 M1a save safety (`44c455d`); PR #16 M1b save version 5, restoring the place, export and import (`ff95989`); PR #18 the "Sit down?" prompt fix (`23906b7`). PR #5 (documentation, `b0ad590`), PR #7 (agent workspace, `bb93709`), PR #8 (live verification tool, `d91a5d4`: `tools/`, `tests/` and documentation only), PR #9 (documentation, `3ac8b53`), PR #10 (documentation, `2d9d753`), PR #11 (documentation, `492a8e5`), PR #13 (documentation, `6e9ac76`), PR #14 (browser test limit 60 minutes, `40fe29f`) and PR #17 (browser test limit 90 minutes, `0809b6a`) do not change the published files |
| Open pull requests | | PR #15 (`docs/local-qualification`, this documentation). Its first Tests run (`42379965558`, 2026-11-07) never started: GitHub reported that the account was locked because of a billing issue. PR #14's first run had also failed within seconds, before any test ran (cause not recorded); PR #14 merged after its re-run passed |

Publishing happens only through the manual "Deploy to GitHub Pages" workflow with the `github-pages` approval; merging into `main` does not change the live site ([TECHNICAL_ARCHITECTURE.md §4](TECHNICAL_ARCHITECTURE.md)).

## Milestone

**M0 — Stabilise: in progress.** No milestone is complete. M1a and M1b are merged as the first slices of M1, by approved exceptions; M1 itself is not complete (save slots and the state module remain). Scope and acceptance: [MASTER_ROADMAP.md](MASTER_ROADMAP.md#m0--stabilise).

| M0 item | Status | Evidence |
| --- | --- | --- |
| Automated tests in CI as required checks; approval-gated manual deployment; Pages published by GitHub Actions; `main` protected by a ruleset; Actions hardened | Done | PR #1, PR #2; ruleset "Protect main" (`tests-syntax`, `tests-browser`, strict up-to-date) |
| Pendeltåg camera and M14 merged | Done | PR #3 (`40d913e`) |
| Message strip clear of every control | Done | PR #4 (`3d04635`); timing fix PR #6 (`d9b8882`), KNOWN_ISSUES M16, M17 |
| Project documentation in the repository | Done | PR #5 (`b0ad590`) |
| "Sit down?" and the other station and train prompts answer the mouse and keys on the first try | Done (merged, not deployed) | PR #18 (`23906b7`). **Accepted by the owner on 2026-11-08 with its qualification limitation documented; Gate 2 of its qualification remains NOT PASSED** (details under "Latest verification results") |
| Real-device check of the camera and the message strip | **Not complete** | Seated-train frame-rate comparison finished on one laptop ([TEST_PLAN.md §6](TEST_PLAN.md)). A manual desktop session took place on 2026-11-02. Remaining manual desktop checks and physical-device checks have not yet been completed. No physical iPhone, Android or tablet test has run. Checklist in [TEST_PLAN.md §4](TEST_PLAN.md); KNOWN_ISSUES M15, M18 |
| Live verification tool | Done (merged; a tool, not part of the published site) | PR #8 (`d91a5d4`): `tools/live_check.py` and `tests/test_live_check.py` |
| Deploy `main` and verify it live | **Not done** | Live is `870fe30` (above); verify with `tools/live_check.py --expect <sha> --rounds 4 --interval 300` |
| Flights relay redeployed with `/waittime` | **Not done** | Probed 2026-11-01: `/waittime` answers with the old help text listing only `/flights` and `/news`; needs a redeploy and the `SWEDAVIA_KEY` secret (KNOWN_ISSUES M1) |

## Current task and next steps

- **Current — paused; awaiting explicit owner approval to resume:** the remaining manual desktop checks (`m0-desktop-checks`), started and paused by the user. They resume from the recorded stopping point. The "Sit down?" part is fixed (PR #18) and was checked by hand on 2026-11-08; the rest of the checklist has not resumed.
- **Finished:** the "Sit down?" prompt fix (`p0-sit-down-prompt`), merged in PR #18 on 2026-11-08 and not deployed; accepted by the owner with its qualification limitation documented; Gate 2 remains NOT PASSED.
- **Finished:** M1b (`m1b-save`), approved as a further exception to "M1 after M0": save version 5 with the same storage key, restoring the place after a reload (Stockholm Central, the pendeltåg, interiors), export and import of a life. Merged in PR #16 on 2026-11-08 and not deployed. Deploying `main` now publishes M1a, M1b and the prompt fix.
- **Finished:** qualification of an isolated local test runner (`local-qualification`), 2026-11-07, with the full suite passing on `6e9ac76`; the runner is kept outside this repository ([TEST_PLAN.md §7](TEST_PLAN.md)).
- **Finished:** M1a save safety (`m1a-save-safety`), which the user approved on 2026-11-04 as a narrow exception to "M1 after M0". Merged in PR #12 and not deployed. It does not change the save format. Its limits are KNOWN_ISSUES M19 and M20; in particular, multi-tab saving is not race-free. Deploying `main` now also publishes M1a.
- **Next:** see [`.agent/QUEUE.md`](../.agent/QUEUE.md). In short: finish M0 (remaining manual desktop checks, physical-device checks, deploying `main` and checking it with the tool, the relay), each with the user's approval, then the rest of M1 (save and state).

## Latest verification results

| What | Result |
| --- | --- |
| PR #18 CI on `e9c6ff9` (run `42496081159`) | `tests-syntax` passed; `tests-browser` 244 collected, 243 passed, 1 xfailed (L10), 0 failed, browser job 50 min 47 s of its 90-minute limit; GitGuardian passed. `main` `23906b7` merges exactly this head. The first full-suite run of the prompt fix together with M1b |
| Qualification of the prompt fix (PR #18) | **Gate 1: PASS** (2026-11-07, full suite on the isolated local runner at `a350214`: 235 collected, 234 passed, 1 xpassed). **Gate 2: NOT PASSED** (2026-11-07): N1, the mouse tests against the unfixed code, failed its original checklist at one assertion and was accepted only under an approved correction made after the run; N2, five broken keyboard handlers, failed its original checklist (all five detected; one knock-on failure); these results are unchanged. Later, separate evidence (2026-11-08): 29 focused automated checks passed, and the owner's 5 manual checks in Chrome 157 passed; whether uncaught console errors appeared in that session was not confirmed. **The owner accepted the fix on 2026-11-08 with this qualification limitation documented.** Evidence is private and outside this repository |
| PR #17 CI on `5e81766` (run `42484272554`) | `tests-syntax` passed; `tests-browser` 227 collected, 226 passed, 1 xfailed (L10), browser job 53 min 16 s; GitGuardian passed. `main` `0809b6a` merges exactly this head |
| PR #16 CI on `7d5643e` (run `42472593705`) | `tests-syntax` passed; `tests-browser` 226 passed, 1 xfailed (L10), pytest 54.5 min, browser job 55.1 min of its 60-minute limit at the time; GitGuardian passed. An earlier run on `c5187cd` (`42455453697`) was stopped by the 45-minute limit then in force. `main` `ff95989` merges `7d5643e` |
| Isolated local test runner, full suite on `6e9ac76` cloned from a local worktree (2026-11-07) | `RESULT=PASS`: syntax 3 passed; browser stage 218 collected, 217 passed, 1 xpassed (L10), 0 failed, in 56 minutes. The runner also detected an injected runtime error and an injected syntax error, and the checkouts and earlier results were unchanged afterwards. This qualifies the runner; it does not show that the game works beyond what the suite tests. Details and limitations: [TEST_PLAN.md §7](TEST_PLAN.md); report: [`.agent/reports/2026-11-07-local-qualification.md`](../.agent/reports/2026-11-07-local-qualification.md) |
| M15 seated-train frame-rate comparison, 2026-11-03 (`870fe30` against `3ac8b53`, one Intel UHD 620 laptop; not an M7 test) | **Comparison complete; M15 overall not complete.** All 18 required results exist; 22 sessions ran, and 4 are preserved as invalid and excluded. Same camera: no meaningful difference in any tested scene, Rich or Fast. Above ground, You camera against Eyes: −5 fps on Fast, −3 fps on Rich. Each arm's lowest 1-second window is below 30 fps in every scene; typical fps is above 30 only on Fast above ground in the first-person arms. Rich above ground, `870fe30` against You: inconclusive. Evidence is private and outside this repository. Details and limitations: [TEST_PLAN.md §6](TEST_PLAN.md) |
| PR #12 CI on `c5eb610` (run `41879069686`) | `tests-syntax` 3 passed; `tests-browser` 217 passed, 1 xpassed (L10) in about 31 min; GitGuardian passed. `main` `44c455d` merges exactly this head, with the same file tree; CI did not run separately on the merge commit |
| M1a, local with system Chrome (2026-11-04), before the final commit corrected two comments | Full suite 217 passed, 1 xpassed (L10) in 58 min, pytest exit code 0. Negative control on `492a8e5`: 40 of 47 new tests fail. After the correction, only the syntax checks were rerun locally (3 passed). Hidden tab and back/forward cache are simulated; no manual check has run |
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
| `feat/m1-save-safety` | `c5eb610` | PR #12, `44c455d` |
| `docs/status-after-pr12` | `1662a78` | PR #13, `6e9ac76` |
| `ci/browser-timeout-60` | `c456b8e` | PR #14, `40fe29f` |
| `feat/m1b-save` | `7d5643e` | PR #16, `ff95989` |
| `ci/browser-timeout-90` | `5e81766` | PR #17, `0809b6a` |
| `fix/sit-down-prompt` | `e9c6ff9` | PR #18, `23906b7` |
