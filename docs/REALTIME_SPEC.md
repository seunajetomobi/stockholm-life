# Real Stockholm time: decision and plan

Status: **decided by the owner on 2026-11-21; not started.** Supersedes decisions 1 to 3 of [M2_SPEC.md](M2_SPEC.md) §6 (the 4x rate, the forced nod-off at 24:00 and pausing); the others (needs rates, date events, single clock writer, ambient world) are revisited below.

## The decision
Game time, date, season, daylight and weather are **Stockholm right now** (zone `Europe/Stockholm`, real speed 1x, daylight saving included). Actions take their real duration. Long ones (a work shift, sleeping) run as **timed activities** the player can wait through or leave and come back to; they finish by the real clock, also while the page is closed.

Today, for comparison: weather is real when online (Open-Meteo); the clock and calendar are the game's own (day 1 = 24 Oct 2026, 08:00; sun and season from that invented date); there are 96 `S.hour` and 200 `S.day` references, 46 `spendTime` calls and 16 `sleep` calls.

## Design (proposed, [P])
- **One time service.** `gameNow()` returns the Stockholm date, hour and minute and the life day count. Every rule asks it; nothing writes the hour. Tests replace it with a fake clock (a test-only override), so no test waits for real time.
- **Life day.** `S.day` becomes the number of Stockholm calendar days since the life began (derived, not stored as the clock). Rent, salary, bills and the Kronofogden steps keep working on calendar days.
- **Timed activities.** An action has a duration. If it is longer than a short threshold it becomes a task `{act, start, end}` stored in the save; effects apply when `end` passes, with the needs drained for the elapsed time. One task at a time; the player can do free things (phone, look around) meanwhile, not other timed actions.
- **Offline catch-up.** On load, tasks that ended while away are completed, and needs drain for the time away up to a cap (to be decided, [?]) so a week away is not a death sentence.
- **Opening hours** use the real clock: a shop really is shut at 03:00. This is deliberate realism.
- **World.** Season, daylight, sun position, sky and weather follow the real date and time; the weather fallback offline uses the real month, not the invented date.
- **Stations and trains** use the real clock; timetables are already real; the 4x station clock and its 23.98 cap are removed.

## Stages (one branch and PR each; full browser run before every push)
1. **R0** this document and the decision recorded (docs only).
2. **R1** the time service in `src/rules/clock.js` with a fake clock for tests; the save gains the life start (a version bump with a migration, reviewed by the save-system role; old lives are anchored so they keep their day count and needs).
3. **R2** the world follows real time (date, season, sun, sky, offline weather, opening hours, bills and mail by calendar day). Nothing becomes timed yet.
4. **R3** the timed-activity engine, with sleep as the first use, and offline catch-up.
5. **R4** convert the other time-spending actions in groups (work, study, errands, trips), several PRs.
6. **R5** needs rates rebalanced to real hours; **R6** stations and trains on the one clock; **R7** acceptance and polish (daylight-saving days of 23 and 25 hours, time zones, offline, long sessions).

Dependencies: M1c is done (slots and saves). M2 Stage 1 (tests) is merged, Stage 2 (clock constants module) is PR #41; both stay useful (the characterisation tests describe the behaviour being replaced and will be rewritten per stage).

## Open questions for the owner ([?])
1. Offline catch-up cap for needs (suggest a few hours' worth, so leaving for a day is not fatal).
2. Whether the player abroad or at start should also follow Stockholm time (suggest yes, always Stockholm).
3. How the timed activity is shown while waiting (suggest a visible progress bar with the finish time and a notification when done).
4. Whether a "skip" exists for testing only (suggest a developer-only fake clock, never in the live game).

## Risks
A full redesign of the core loop: balance (needs, money, jobs) must be re-tuned, many tests pin the old behaviour, saves change version, and a player who opens the game at 03:00 will find it asleep. Mitigation: staged PRs, a fake clock for tests, a save migration with backups (the M1 machinery), and owner review of balance at R5.
