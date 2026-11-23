# Real time: every writer of the game hour and day, and what each becomes

Status: **proposal for Codex's review; nothing implemented.** Written 2026-11-22 after Codex's assignment 1 asked for the writers to be mapped before any is changed ([REALTIME_SPEC.md](REALTIME_SPEC.md)). Counts come from a search of `index.html` at `bd046ad` (`S.hour`/`S.day` written with `=`, `+=`, `-=`, `++`); they replace the "six writers" in earlier documents, which counted groups loosely.

**Result: `S.hour` is written at 16 places in 8 groups; `S.day` is written in exactly one place (`sleep()`, `S.day++`).** `S` is also rebuilt wholesale in `newGame` and in a fallback near the end of the script. There are 16 `sleep(` calls, 46 `spendTime(` calls and 5 `needsTick(` calls.

Rule for all rows: **with `REALTIME` off, nothing changes** (Codex, 2026-11-22: do not turn writers into no-ops yet). With it on, `S.day` and `S.hour` are views derived from `t0` and the Stockholm clock in the tick; the right-hand column says what each writer's job becomes then.

| # | Where (line at `bd046ad`) | Today | With REALTIME on |
| --- | --- | --- | --- |
| 1 | Doctor drop-in wait (590): `S.hour+=1.5` | an unlisted patient waits 1.5 h | a timed task of 1.5 h at the vårdcentral; effects (sick days, mood) at its end |
| 2 | `__slDrive` (1045): `S.hour+=min/60` | driving costs time by distance | no write: the clock runs while the car moves; fuel and needs follow elapsed time in the tick |
| 3 | Walking (1047): `S.hour+=min/60` | walking costs time by distance (80 m/min, run 160) | no write for real walking. **Open issue:** auto-walk and `openTravel` move the avatar faster than 80 m/min, so real time would pass faster than the cost shown; either slow those or make them timed tasks of the distance's duration |
| 4 | `spendTime(h)` (1320), 46 callers | adds `h`, drains needs, at 24:00 forces `sleep(true)` (nod off on the night bus) | `startTask({hours:h})`; the forced nod-off goes (a tired player just runs low on energy) |
| 5 | Trip return (1447): `sleep(false,'trip')` per night then `S.hour=Math.max(S.hour,17)` | nights pass at once; back at 17:00 at the earliest | a task of the trip's nights, ending on arrival; the 17:00 floor becomes the arrival time |
| 6 | `sleep()` wake times (2299–2308): hospital 9, cell 10, jail 7, trip 8, shelter 7, out 6.5, friend 8, passed-out 8, home 7 | jump the hour to a fixed wake time | a task ending at the next occurrence of that clock time; energy, hygiene and the mode's effects apply once at the end |
| 7 | Signalfel event (2340): `S.hour+=1` | "an hour gone" | a 1 h delay task |
| 8 | `csFlush` (4932): station minutes at 4× real time, capped at 23.98 | the station and train run a faster clock | removed with `CRATE`; the station reads the one real clock (stage R6) |
| D | `sleep()` (2296): `S.day++` and everything the day change runs | rent, queue, bills (`processBills`), `crimeDaily`, weather, `invTick`, mail, payday | a `dayRollover()` run once per Stockholm calendar day, derived from `t0`, including days missed while the page was closed (catch-up) |

## What must be settled before step 4 of the plan
1. **`sleep()` mixes two jobs.** Its daily bookkeeping (bills, mail, payday, queue, weather, crime, investments) must move into `dayRollover()` and be idempotent per calendar day (store the last day rolled in the save). Its night's-rest effects stay with the sleep task. Today both run in one call, so the order of effects (the `S.sunToday` check, `wasSick`, the 25th and 1st of the month) must be preserved by tests before the split.
2. **Midnight transition.** `spendTime` forces `sleep(true)` at 24:00; real time has no such event. The test fixtures that cross midnight (`tests/test_time_rules.py`) describe the old behaviour and are rewritten per stage, not deleted.
3. **Calendar anchoring.** `today()` is `dateOf(S.day)` from a fixed start (24 Oct 2026). Under real time the date is the real date; rent, payday and holidays read it. `life-start.js` anchors an existing life so its day count survives.
4. **Catch-up.** Needs drain at a quarter rate with a floor of 15 for at most 24 h away (Codex accepted, 2026-11-22); rent, bills and mail follow calendar days and are not capped.
5. **Order of work (Codex's assignments).** (1) flag plus `t0` in the save (`t0` is in PR #48); (2) the clock service and first read-only consumers (calendar, daylight, opening hours); only then (3) tasks for writers 1, 4, 5, 6, 7, (4) `dayRollover()` and catch-up, (5) travel (writers 2, 3), (6) the station (writer 8).
