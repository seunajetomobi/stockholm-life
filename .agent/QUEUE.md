# Task queue

The single source of the current task and the tasks after it. Project status (commits, live site, milestone) is in [`docs/PROJECT_STATUS.md`](../docs/PROJECT_STATUS.md); rules, roles and the report format in [`AGENTS.md`](../AGENTS.md).

How to use it: one task is **Current**. The coordinator (ChatGPT, through the user) adds and orders tasks; the user approves them. An agent starts only the current task, moves it to **Done** with a link to its pull request or report when the user has accepted it, and does not start the next one without approval. A task that needs more than a few lines gets a spec in `.agent/tasks/<task-id>.md`.

Updated 2026-11-17.

## Current

| ID | Task | Owner | Status | Needs approval for |
| --- | --- | --- | --- | --- |
| m0-desktop-checks | The remaining manual desktop checks in [TEST_PLAN.md §4](../docs/TEST_PLAN.md), results recorded. First, by hand: "Sit down?" with the mouse, the HUD button, E, Enter and Y. Automated simulated mouse presses did not activate it (1 of 40, then 0 of 40). In the manual session, the mouse on 'Sit down?' failed; the cause is not confirmed. | User, with Claude Code recording | Current — paused; awaiting explicit owner approval to resume. Paused 2026-11-04 by the user; no task is active until then. Started and not finished; detailed results are private and are not reported here, and testing resumes from the recorded stopping point. M15 stays open | Resuming; any fix is a separate pull request |

## Up next

In order. Apart from the part of `m0-devices` noted below, none of these has started. `m1-save` depends on M0 being closed; `m1a-save-safety` went ahead before that as an approved exception.

| ID | Task | Owner | Notes | Needs approval for |
| --- | --- | --- | --- | --- |
| m0-devices | Real-device checks of the pendeltåg camera and the message strip ([TEST_PLAN.md §4](../docs/TEST_PLAN.md)), results recorded | User, with Claude Code recording | Follows `m0-desktop-checks`. Needs a real iPhone, Android phone and tablet. Seated-train comparison done on one laptop ([TEST_PLAN.md §6](../docs/TEST_PLAN.md)). A manual desktop session took place on 2026-11-02. Remaining manual desktop checks and physical-device checks have not yet been completed. No physical iPhone, Android or tablet test has run; M15 stays open | — |
| tram-journeys | Playable trams: at a `tram_stop` (Nockebybanan, Spårväg City) or at a station that a tram serves (Tvärbanan, Lidingöbanan) the player can take a tram to a later stop, paying the SL fare as for a bus; the bus-journey system is reused (`transitLinesAt`, `busRide` with rail cars and no kerb shift); `tests/test_transit_rides.py`. **Status: implemented and tested locally (2026-11-18); on its pull request, awaiting CI and review. Not merged, not deployed.** Branch `feat/tram-journeys` from `main` `4b2e88a`. No change to saves, the clock or traffic. Commuter boats are a separate later feature | Claude Code | Does not replace `m0-desktop-checks`. Limits in KNOWN_ISSUES L16 | Merging, any deployment |
| fix-bus-pavement | Vehicles on the pavement (the owner's standing defect). Investigated in the browser: ordinary cars stay inside the carriageway (948 of 948 samples); buses were moved out of the street by their kerb shift (24 of 540 samples, up to 3.7 m). Fix: the shift is capped by the depth of the route line inside the carriageway (`busKerb` in `index.html`); `tests/test_vehicle_lanes.py`; KNOWN_ISSUES M25 and M24. **Status: implemented and tested locally (2026-11-17); on its pull request, awaiting CI and review. Not merged, not deployed.** Branch `fix/vehicles-on-pavements` from `main` `2cd7a9a`. No change to saves, the clock or traffic rules | Claude Code | Does not replace `m0-desktop-checks`. Bus route lines that are themselves off the modelled carriageway (M24) are not changed | Merging, any deployment |
| m0-deploy | Deploy `main` with the "Deploy to GitHub Pages" workflow and verify it live with `tools/live_check.py` (before: against the live commit; after: against the deployed one, over at least the 10-minute cache window) | User approves; Claude Code verifies | Live is still `870fe30`. `main` now includes M1a, so deploying it publishes M1a too. Should not go ahead until the "Sit down?" mouse failure from `m0-desktop-checks` is resolved | Deploying |
| m0-relay | Redeploy the flights relay (`tools/flights-worker.js`) with `/waittime` and the `SWEDAVIA_KEY` secret | User | Needs Cloudflare access; KNOWN_ISSUES M1. Independent of the other M0 tasks, so it can be done at any point | Deploying the Worker |
| m3-sun-rules | M3 step 3 ([MODULES.md §6](../docs/MODULES.md)): the sun and daylight rules (`sunInfo`, `daylight`, `sunrise`, `sunset`, `isLight`) and the WMO weather-code tables moved out of `index.html` into `src/rules/sun.js`, behaviour-preserving, with `tests/test_sun.py`. **Status: implemented and tested locally (2026-11-17); on its pull request, awaiting CI and review. Not merged, not deployed.** Branch `refactor/sun-rules` from `main` `2cd7a9a`. Does not touch saves, the game clock or M0/M1 | Claude Code | Approved by the owner on 2026-11-17. Does not replace `m0-desktop-checks`, which stays Current and paused. M2 is not started | Merging, any deployment |
| m1-save | The rest of the M1 save and state foundation ([MASTER_ROADMAP.md](../docs/MASTER_ROADMAP.md#m1--save-and-state-foundation)): save format v5, slots, export and import, restoring the place, the state module | Claude Code | Spec to be written in `.agent/tasks/` when M0 is closed | Starting, then merging |

## Proposed, not approved

Follow-ups from the seated-train comparison ([TEST_PLAN.md §6](../docs/TEST_PLAN.md)). None has started: investigate the You camera's above-ground cost; repeat on a stronger GPU; run the frame-cap-off test; check r02's reading again with GPU clock recorded.

## Done

| ID | Result |
| --- | --- |
| save-fixtures | PR #21, merged as `2cd7a9a` on 2026-11-17 (head `9f0cd50`, one commit kept; **not deployed**). A7, the save compatibility gate before the rest of M1: seven fixtures (six written by the real game at `55c196b`, `870fe30` and `3eb5711`; one synthetic v3), `tests/test_save_fixtures.py` (13 tests), a generator and negative controls; tests, fixtures and documentation only, no game code. CI on the head: run `43693961090`, `tests-browser` 275 collected, 274 passed, 1 xpassed (L10), 0 failed, 1 h 01 min 9 s. Local qualification on 2026-11-17: 8 of 8 negative controls detected, a `docs` mutant caught by the new assertion, and a `slUntil` differential showing it catches a save-side omission the earlier checks miss ([PROJECT_STATUS.md](../docs/PROJECT_STATUS.md)). Limit: `migrate-not-idempotent` fails first on the `points` change, so it does not independently prove the later idempotence assertion |
| m3-modules-first | PR #20, merged as `b3305d3` on 2026-11-14 (head `b010ad1`, four commits kept; **not deployed**). The first two steps of M3: `src/geography.js` and `src/util/format.js` as classic scripts, and `deploy.yml` and `tools/live_check.py` publish and verify `src/` ([MODULES.md](../docs/MODULES.md)). CI on the head: run `43639764164`, `tests-browser` 262 collected, 261 passed, 1 xpassed (L10), 46 min 6 s. M3 overall stays open |
| local-qualification | An isolated local test runner qualified, 2026-11-05 to 2026-11-07: injected runtime and syntax errors detected, and the full suite passed on `6e9ac76` (syntax 3 passed; 218 collected, 217 passed, 1 xpassed for L10), with the checkouts and earlier results unchanged. The runner is kept outside this repository; adding it is an open decision. [Report](reports/2026-11-07-local-qualification.md); [TEST_PLAN.md §7](../docs/TEST_PLAN.md). Not a game change, so M0 is unaffected |
| m1a-save-safety | PR #12, merged as `44c455d` (head `c5eb610`; not deployed). First slice of M1, approved on 2026-11-04 as a narrow exception to "M1 after M0"; no change to the save format. Limits are in KNOWN_ISSUES M19 and M20. The rest of M1 still waits for M0 |
| status-after-pr10 | PR #11, merged as `492a8e5` |
| m15-docs | PR #10, merged as `2d9d753` (documentation only, not deployed), with the L15 row. M15 overall stays open |
| m15-three-arm | Automated seated-train comparison complete: 22 sessions ran, all 18 required results exist, 4 invalid sessions preserved and excluded ([TEST_PLAN.md §6](../docs/TEST_PLAN.md); evidence private, outside this repository). M15 overall stays open |
| status-after-pr8 | PR #9, merged as `3ac8b53` |
| m0-live-check | PR #8, merged as `d91a5d4` (a tool and its tests; it does not change the published files) |
| agent-workspace | PR #7, merged as `bb93709` |
| local-cleanup | The user's local checkout brought up to `main` `bb93709` (2026-11-01); local files kept in the user's private backup; local branches kept |
| m14-layout-timing | PR #6, merged as `d9b8882` (not deployed) |
| project-docs | PR #5, merged as `b0ad590` |
