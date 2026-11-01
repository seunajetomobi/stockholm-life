# Master roadmap

The order of work from today's game to the [product vision](PRODUCT_VISION.md). It replaces the earlier audit roadmap (`IMPLEMENTATION_ROADMAP.md`, never committed); what that roadmap delivered is under "History" at the end.

Status as of 2026-11-01, `main` at `40d913e`.

## Guiding rules

1. **Foundations before features.** Durable state, an explicit game clock and a registry of places and people come before new gameplay that depends on them.
2. **One complete slice before breadth.** The first-week slice (M4) must work end to end before systems are expanded city-wide.
3. **Move before you change.** Moving code into modules (M3) happens in separate pull requests from behaviour changes, each guarded by the test suite.
4. **Every milestone ships through the pipeline.** Pull request with the required checks (`tests-syntax`, `tests-browser`), review, merge, then a manual, approved deployment.
5. **Keep three.js r128 and no-build static hosting** until a later, explicit decision.

## Dependencies

```
M0 Stabilise
 └─ M1 Save and state ─┬─ M2 Time model ──┐
                       └─ M3 Modularise ──┴─ M4 First-week slice ── M5 Simulation systems ── M6 World expansion
                          M3 ── M7 Visual and performance (measure first)
            M1 + M2 + M3 + M5 ── M8 Multiplayer preparation (long term)
```

## M0 — Stabilise (in progress)

| | |
| --- | --- |
| Objective | A clean, published, documented baseline before new development |
| Scope | Merge the short-screen M14 fix (PR #4); real-device check of the pendeltåg camera and M14; deploy `main`; commit the project documentation; redeploy the flights relay with `/waittime` (KNOWN_ISSUES M1) |
| Dependencies | None |
| Risks | Deployment regressions; the CI Chromium-install step can stall (KNOWN_ISSUES L12) |
| Deliverables | Live site = `main`; documentation in the repository; relay up to date |
| Acceptance | Live verification of the deployed commit passes all rounds (files, identity, browser startup); real-device checklist in TEST_PLAN.md §4 completed and recorded |
| Testing | Existing CI suite; post-deployment live checks |

Done so far: automated tests in CI (required checks), approval-gated manual deployment, Pages published by GitHub Actions, `main` protected by a ruleset, Actions hardened, camera and M14 merged (PR #3). Open: PR #4, real-device check, deployment of `main`, this documentation PR, the relay.

## M1 — Save and state foundation

| | |
| --- | --- |
| Objective | Saves that never silently fail and that restore exactly where the player was |
| Scope | Save envelope v5 (schema version, ordered migrations, timestamp); several slots plus export/import to a file; world state saved (current place: street, interior, station, train, vehicle); visible message when saving fails; save on `pagehide`/`visibilitychange`; a corrupted save is kept under a backup key and reported. A state module owning `S`, with small mutation helpers and change events |
| Dependencies | M0 |
| Risks | Migration bugs that lose existing lives |
| Deliverables | Save module, migrations for v3 → v4 → v5, slot UI |
| Acceptance | Reloading in every place restores the same place and state; v3 and v4 saves migrate; a full storage shows an error; a corrupted save is not overwritten silently |
| Testing | Unit tests for every migration and for the envelope; browser tests that save and reload in each place type |

## M2 — Time model

| | |
| --- | --- |
| Objective | An explicit game clock that schedules can rely on |
| Scope | A game clock that runs independently of walking (pause and speed settings), one clock for city, station and train (replacing the separate station clock), opening hours and schedules read from it; need drain and day change driven by the clock |
| Dependencies | M1 |
| Risks | Balance changes to needs, money and travel times |
| Deliverables | Clock module, documented rules for how time passes |
| Acceptance | Time passes while standing still; existing rules (rent, salary, bills, needs) give the same results at the same game time; the station and the city agree on the time |
| Testing | Unit tests for the clock, needs and day change; browser test of time passing without movement |

## M3 — Modularise along the seams

| | |
| --- | --- |
| Objective | Code that can be changed and tested in parts |
| Scope | Move data tables, rules, saving, live-data clients, phone apps and the sections of the 3D world into native ES modules (no build step); replace the five reassigned core functions (`newGame`, `sleep`, `spendTime`, `addBill`, `log`) with explicit hooks |
| Dependencies | M1 (can run in parallel with M2) |
| Risks | Breakage from moves |
| Deliverables | `index.html` reduced to markup plus a module loader; one module per area (see TECHNICAL_ARCHITECTURE.md §3) |
| Acceptance | Full test suite green after every move; no behaviour change in any move-only pull request |
| Testing | Full suite per move; new unit tests for each moved rules module |

## M4 — First-week slice (core gameplay)

| | |
| --- | --- |
| Objective | The first complete, connected life experience ([vision](PRODUCT_VISION.md)) |
| Scope | Mission system (data-driven steps with triggers and rewards, mission log on the phone); interior definitions (rooms, doors, interaction spots, NPC slots) for four buildings: the sublet, the café, Skatteverket, a grocery store; a playable café shift (orders, serving, performance from timing and needs); grocery shopping into the inventory and cooking at home; a weekly money ledger |
| Dependencies | M1, M2, M3 |
| Risks | Scope creep; area-specific content effort |
| Deliverables | The playable week in Norrmalm/Vasastan for the newcomer origin |
| Acceptance | The week can be completed without menu-only shortcuts for mission steps; each step advances from game state; saving and reloading at every step restores place and progress; the ledger balances; 30 fps on the target laptop and phone |
| Testing | Unit tests for the mission step machine, shift scoring and the ledger; browser tests that drive the week through the test hook with time skips and check mission and save state each day |

## M5 — Simulation systems

| | |
| --- | --- |
| Objective | People who live in the city |
| Scope | NPC registry (name, home, work, timetable, personality) simulated as records away from the player and embodied as characters nearby; relationships tied to these NPCs, with simple memory of shared events; the first-week coworker and neighbour become registry NPCs |
| Dependencies | M2, M4 |
| Risks | Performance with many embodied NPCs |
| Deliverables | NPC registry and scheduler; relationship events |
| Acceptance | NPCs are found where their timetable says at the right game time; relationships change through encounters, not menu actions |
| Testing | Schedule and position tests at fixed game times; relationship unit tests |

## M6 — World expansion

| | |
| --- | --- |
| Objective | More of the city becomes playable, using the proven slice systems |
| Scope | Interior definitions for more building kinds; more playable jobs; the housing queue and moving as missions; buying a home and furnishing it later; further mission chains (Swedish course, driving licence) |
| Dependencies | M4, M5 |
| Risks | Content volume; consistency across areas |
| Deliverables | Each addition built from the M4 templates |
| Acceptance | Each new job, building or mission passes the same acceptance template as M4 |
| Testing | Tests per addition, following the M4 pattern |

## M7 — Visual and performance

| | |
| --- | --- |
| Objective | Smooth play on ordinary laptops and phones, then better visuals |
| Scope | Measure first (debug overlay: fps, draw calls, triangles, memory, loaded tiles); per-tile data loaded on demand and parsed in a Web Worker; phone-specific render settings; facade and street-furniture improvements in the slice area; rebuildable data pipeline |
| Dependencies | M3 |
| Risks | Device variety; data pipeline effort |
| Deliverables | Performance budget recorded per release |
| Acceptance | ≥ 30 fps on the target devices (TEST_PLAN.md §3.4); JS memory under 500 MB; time to playable under 15 s |
| Testing | Performance runs per release on real devices |

## M8 — Multiplayer preparation (long term)

| | |
| --- | --- |
| Objective | An architecture that would allow multiplayer later, without building it |
| Scope | Deterministic, event-sourced simulation core; seeded randomness; authoritative game state separated from the client; a protocol sketch. No server, accounts or networking |
| Dependencies | M1, M2, M3, M5 |
| Risks | Locking in an architecture too early |
| Deliverables | Replayable simulation runs from a seed plus an event log |
| Acceptance | The same seed and events give the same state |
| Testing | Replay and determinism tests |

## Not to build yet

- Multiplayer, servers, accounts, cloud saves.
- Buying or furnishing homes before rented homes have real interiors and saved state.
- City-wide interiors or NPC behaviour before the M4 slice works.
- More menu-only jobs, apps or civic features.
- A city-wide visual overhaul or a three.js upgrade before measuring and modularising.
- A bundler or TypeScript.

## History

The audit roadmap of 2026-10-31 planned a "Phase 1: Safety net", then phases 2–6. Delivered:

| Phase 1 item | Result |
| --- | --- |
| Commit or discard the uncommitted camera change | Committed and merged (PR #3) |
| Smoke test and syntax check in the repository | `tests/` with syntax, smoke, save, layout, M14 and camera tests (PR #2, PR #3) |
| Deployment gated by tests | GitHub Pages published by the manual "Deploy to GitHub Pages" workflow behind the `github-pages` approval gate (PR #2, source switched 2026-10-31) |
| Redeploy the flights relay | Open (M0) |
| Visible save failures, save on `pagehide` | Open (M1) |

Later phases map onto the milestones above: phase 2 → M3, phase 3 → M1, phase 4 → M4, phase 5 → M7, phase 6 → M6.
