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

## Decisions taken on the owner's delegation (2026-11-22: "choose the best for the game")
The four open questions above, answered by Claude as lead. Each is reversible before R7.
1. **Catch-up cap.** Needs drain for time away at a quarter of the normal rate and never below a floor (energy, mood, food and hygiene stop at 15), for at most 24 hours of away time; longer absences count only the first 24 hours. A week away is not a death sentence. Rent, bills and mail still follow calendar days, because they are paperwork, not bodies.
2. **Time zone.** Always Stockholm, wherever the player is in the game and wherever the browser is. The clock chip shows "Stockholm 14:05".
3. **Waiting.** A timed activity shows a card with the name, a progress bar, the finish time and "leave it running"; a notification (the phone, and the browser title) tells the player when it is done. Free actions (phone, looking, walking, shopping) stay possible meanwhile; other timed actions wait.
4. **Skip.** A fake clock exists for tests (`StockholmLife['stockholm-time'].setFakeNow`, already built) and, for the owner only, through a `?fakeclock=` URL parameter that is ignored unless `localStorage` has a developer flag. The live game has no skip.

## Design of R2 and R3 together (they cannot ship apart: a real sky over a game hour is incoherent)
**Switch.** Everything below sits behind one flag, `REALTIME` (default off; `?realtime=1` or a developer flag turns it on). With the flag off the game behaves exactly as today and every existing test stays valid; with it on, a second set of tests runs. R7 flips the default and deletes the old path. This lets each stage merge after one CI run without a half-converted game.
**Derived time.** With the flag on, `S.day` is `lifeDay(S.t0, now)` and `S.hour` is the Stockholm hour at `now` (both recomputed by the main tick), never written. The six direct writers (`spendTime`, `sleep` and its `S.hour=` wake times, the signal-failure event, `__slDrive`, walking in `needsTick` pairs, `csFlush`) are replaced:
- `spendTime(h)` becomes `startTask({act, hours})`: it records `{act, start, end}` in `S.task` and applies the action's effects at `end`; needs drain by elapsed real time in the tick (`needsTick(dt)` already takes hours).
- Walking, driving and rides advance time only through their real duration, so `needsTick` is called by the tick, not by the action.
- `sleep()` becomes a task that ends at the next wake time (07:00, or the mode's time), with its energy and hygiene effects applied at `end`. The forced nod-off at 24:00 is removed; a tired player simply runs low on energy.
- The hospital, cell, jail, shelter, trip and friend modes become tasks of their stated length.
**Catch-up.** On load, finished tasks are completed in order, then needs drain by the cap above. The migration of an old life uses `t0` from PR #48.
**World.** `dateOf` takes the real date for the season, sun and sky; the weather fallback uses the real month; opening hours use the real hour and the red-day rule already merged; trains and the station use the one clock (`CRATE` goes).
**Order of work.** (1) the flag, the clock source and the derived `S.day`/`S.hour`, with tests under the fake clock; (2) `startTask` and sleep; (3) the other writers in groups; (4) catch-up; (5) the world; (6) balance and R7 acceptance, then flip the flag. One PR each, every PR with a full browser run.
