# Task queue

The single source of the current task and the tasks after it. Project status (commits, live site, milestone) is in [`docs/PROJECT_STATUS.md`](../docs/PROJECT_STATUS.md); rules, roles and the report format in [`AGENTS.md`](../AGENTS.md).

How to use it: one task is **Current**. The coordinator (ChatGPT, through the user) adds and orders tasks; the user approves them. An agent starts only the current task, moves it to **Done** with a link to its pull request or report when the user has accepted it, and does not start the next one without approval. A task that needs more than a few lines gets a spec in `.agent/tasks/<task-id>.md`.

Updated 2026-11-08.

## Current

| ID | Task | Owner | Status | Needs approval for |
| --- | --- | --- | --- | --- |
| m0-desktop-checks | The remaining manual desktop checks in [TEST_PLAN.md §4](../docs/TEST_PLAN.md), results recorded. First, by hand: "Sit down?" with the mouse, the HUD button, E, Enter and Y. Automated simulated mouse presses did not activate it (1 of 40, then 0 of 40). In the manual session, the mouse on 'Sit down?' failed; the cause is not confirmed. | User, with Claude Code recording | Current — paused; awaiting explicit owner approval to resume. Paused 2026-11-04 by the user; no task is active until then. Started and not finished; detailed results are private and are not reported here, and testing resumes from the recorded stopping point. M15 stays open. 2026-11-08: a fix (`p0-sit-down-prompt`, below) passed the owner's manual Chrome checks of "Sit down?" with the mouse (Yes and No), E and the HUD buttons, and of "Get off the train?"; the rest of this checklist has not resumed | Resuming; any fix is a separate pull request |

## Up next

In order. `ci-browser-timeout-90` and `p0-sit-down-prompt` are under way; apart from them and the part of `m0-devices` noted below, none of these has started. `m1-save` depends on M0 being closed; `m1a-save-safety` and `m1b-save` went ahead before that as approved exceptions.

| ID | Task | Owner | Notes | Needs approval for |
| --- | --- | --- | --- | --- |
| ci-browser-timeout-90 | Raise the `tests-browser` job's limit in `.github/workflows/tests.yml` from 60 to 90 minutes | Claude Code | Approved 2026-11-08. The browser suite took 55.1 of its 60 minutes on PR #16 (run `42472593705`), and `p0-sit-down-prompt` adds 17 browser tests. PR #17, open, not merged | Merging |
| p0-sit-down-prompt | Make the world prompts ("Sit down?", "Get off the train?", entering the station) answer the mouse, E, Enter and Y on the first try | Claude Code | The fix for `m0-desktop-checks`. Branch `fix/sit-down-prompt`, prepared locally and not yet on GitHub, brought up to date with `main` after PR #16. 2026-11-08: its 29 focused automated tests passed, and so did the owner's manual Chrome checks (see `m0-desktop-checks`). Follows `ci-browser-timeout-90`, because its CI is expected to run past 60 minutes | Pushing and opening its pull request; merging |
| m0-devices | Real-device checks of the pendeltåg camera and the message strip ([TEST_PLAN.md §4](../docs/TEST_PLAN.md)), results recorded | User, with Claude Code recording | Follows `m0-desktop-checks`. Needs a real iPhone, Android phone and tablet. Seated-train comparison done on one laptop ([TEST_PLAN.md §6](../docs/TEST_PLAN.md)). A manual desktop session took place on 2026-11-02. Remaining manual desktop checks and physical-device checks have not yet been completed. No physical iPhone, Android or tablet test has run; M15 stays open | — |
| m0-deploy | Deploy `main` with the "Deploy to GitHub Pages" workflow and verify it live with `tools/live_check.py` (before: against the live commit; after: against the deployed one, over at least the 10-minute cache window) | User approves; Claude Code verifies | Live is still `870fe30`. `main` now includes M1a and M1b, so deploying it publishes both. Should not go ahead until the "Sit down?" mouse failure from `m0-desktop-checks` is resolved (the fix is `p0-sit-down-prompt`) | Deploying |
| m0-relay | Redeploy the flights relay (`tools/flights-worker.js`) with `/waittime` and the `SWEDAVIA_KEY` secret | User | Needs Cloudflare access; KNOWN_ISSUES M1. Independent of the other M0 tasks, so it can be done at any point | Deploying the Worker |
| m1-save | The rest of the M1 save and state foundation ([MASTER_ROADMAP.md](../docs/MASTER_ROADMAP.md#m1--save-and-state-foundation)): save format v5, slots, export and import, restoring the place, the state module | Claude Code | `m1b-save` delivered save format v5, export and import, and restoring the place; slots and the state module remain. Spec to be written in `.agent/tasks/` when M0 is closed | Starting, then merging |

## Proposed, not approved

Follow-ups from the seated-train comparison ([TEST_PLAN.md §6](../docs/TEST_PLAN.md)). None has started: investigate the You camera's above-ground cost; repeat on a stronger GPU; run the frame-cap-off test; check r02's reading again with GPU clock recorded.

## Later (recorded by the owner on 2026-11-08, not started)

Recorded as future work; none has an approved start. Each starts only with the owner's approval, after everything in Current and Up next unless the owner reorders, with a spec in `.agent/tasks/<task-id>.md` first. Each is its own pull request with regression tests, changes nothing outside its task, and moves code into the modules of [TECHNICAL_ARCHITECTURE.md §3](../docs/TECHNICAL_ARCHITECTURE.md) only where that move is approved; none of these rows authorises a wider refactor. Code references were checked on `main` `ff95989`: "Seen in the code" is what the code shows, "To check" is a hypothesis. Proposed order: as listed.

| ID | Task | Owner | Notes | Needs approval for |
| --- | --- | --- | --- | --- |
| ci-slow-tests | Make `tests/test_m14.py` and `tests/test_save_safety.py` faster, keeping every check and keeping the tests independent of each other | Claude Code | Measured: in CI run `42472593705` (PR #16) they took about 19.7 and 18.4 of the 54.5 test minutes, from the log's timestamps. To check: where the time goes (city loads, fixed waits, repeated layouts), with `--durations`. The same results before and after, and a negative control for any changed test. First because it shortens every later pull request's CI and changes no game code | Starting; merging |
| train-colours | Accurate train colours: review the colours and liveries of each rail service shown (T-bana, pendeltåg, Roslagsbanan, trams and light rail, Arlanda Express, regional and long-distance trains), correct the wrong ones and tell services apart. No change to timetables, routes, rides or other transport | Claude Code | Seen in the code: liveries come from `FLEET` and `transitLook()` (by operator and line) and are drawn by `railCar()`; the X60 at Stockholm Central is `x60Ext()`; departure-board line colours are `slLineCol()`. `trainMesh()` is used only when the transit route data is missing: a fixed dark-blue body with a stripe in one colour per type (one for every T-bana line). To check: which colours are wrong; none has been identified yet. Colours come from SL's, Trafikverket's or the operators' published material, with the date checked | Starting; merging |
| vehicle-road-placement | Road vehicles stay on the carriageway: investigate cars and buses seen on pavements; make them follow valid road surfaces and lanes, never use pedestrian areas, pavements or buildings as routes, and behave correctly at junctions, turns, bridges and road connections. Traffic rules (lights, give way, högerregeln, keeping a distance) stay as they are | Claude Code | Seen in the code: the streets each kind of vehicle may use are set in `OKF` (cars: road classes 4–10, primary to `living_street`; buses 4–7); vehicles follow street centre lines (`agentEdge`, `edgePts`, `nextEdge`, `mayEnter`) with lane offsets (`lanesOf`, lane counts from `data/o.json`) and move in `carStep`; the drawn road comes from `roadGeo`. To check: reproduce it with recorded positions, measure how often and where vehicles leave the drawn carriageway, then test the possible causes: lane offsets wider than the drawn road, centre lines that differ from the drawn surface, corners cut at junctions | Starting; merging |
| road-markings | Road markings that match the road: lane dividers, edge lines, pedestrian crossings, stop lines, turning arrows and junction markings, aligned with the road geometry and visible at sensible distances | Claude Code | Seen in the code: lane lines are drawn in `roadGeo` from the real lane counts (a centre line on two-way streets, dashed lines between lanes going the same way), with a snow variant; crossings, stop lines and give-way markings are collected in `furnBucket` (`zebra`, `stop`, `teeth`). To check: edge lines and turning arrows seem not to be drawn (a search found no code for them). After `vehicle-road-placement`, so markings and vehicle lanes share the same lane positions. Marking rules from Trafikverket's published rules, with the date checked; the frame-rate and memory cost measured on Fast and Rich (M7) | Starting; merging |

## Done

| ID | Result |
| --- | --- |
| local-qualification | An isolated local test runner qualified, 2026-11-05 to 2026-11-07: injected runtime and syntax errors detected, and the full suite passed on `6e9ac76` (syntax 3 passed; 218 collected, 217 passed, 1 xpassed for L10), with the checkouts and earlier results unchanged. The runner is kept outside this repository; adding it is an open decision. [Report](reports/2026-11-07-local-qualification.md); [TEST_PLAN.md §7](../docs/TEST_PLAN.md). Not a game change, so M0 is unaffected |
| m1b-save | PR #16, merged as `ff95989` (head `7d5643e`; not deployed). Save version 5: a reload restores the place (Stockholm Central, the pendeltåg, interiors), and a life can be exported to a file and imported. Went ahead before M0 closed with the owner's approval, like M1a. Slots and the state module remain in `m1-save` |
| ci-browser-timeout-60 | PR #14, merged as `40fe29f` (the browser test limit raised from 45 to 60 minutes) |
| status-after-pr12 | PR #13, merged as `6e9ac76` |
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
