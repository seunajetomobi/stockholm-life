# M2 specification: an independent, consistent game-time model

Status: **partly superseded on 2026-11-21 by [REALTIME_SPEC.md](REALTIME_SPEC.md) (real Stockholm time replaces the 4x rate); originally preparation only** (written 2026-11-18 at `main` `7066e60`). M2 is not started and is blocked (§7). This document records how game time works today, what a unified clock must preserve, and what the owner must still decide. It changes no game behaviour. The tests that pin the current behaviour are in [`tests/test_time_rules.py`](../tests/test_time_rules.py).

Tags: **[V]** verified in the code and pinned by a test (the test name is given), **[S]** verified in the code, not pinned, **[P]** proposed future behaviour, **[?]** open decision for the owner. Line numbers are those of `index.html` at `7066e60` and move with edits; search for the names.

## 1. Purpose and boundaries (proposed, [P])
M2 in [MASTER_ROADMAP.md](MASTER_ROADMAP.md): one explicit game clock that schedules can rely on; time that passes while standing still; one clock for city, station and train; opening hours, schedules, need drain and day change read from it.

In scope for M2 (when unblocked): the clock, the day change, the needs drain, rent, salary, bills, opening hours, the station and train clock. Out of scope: a new save format beyond what M1 provides, traffic, weather, the world's lighting (it reads the hour), and balance changes unless the owner decides them (§6).

## 2. How time works today

### 2.1 State [V]
- Time is two plain numbers in the one global `S`: `S.day` (an integer, day 1 = Saturday 24 October 2026, `START`, `dateOf(d)`) and `S.hour` (a number of hours, 0 to 24, not an integer). There is no minutes field and no clock object. `today()` is `dateOf(S.day)`. (`test_calendar_days`)
- Both are saved with the rest of `S` under `stockholm-life-v4`. [S]

### 2.2 What moves `S.hour` (every writer)
| Writer | What it does | Evidence |
| --- | --- | --- |
| `spendTime(h)` | `needsTick(h)`, then `S.hour += h`; at 24 or more it logs "nodded off on the night bus" and calls `sleep(true)`. The phone section wraps it (`spendTime = function…`) to add `incomingChats(h)`. About 46 call sites: actions, shifts, travel, the end of every bus, tram and boat ride (`pickBusStop`) | `spendTime` near line 1211; wrapper near 1903. `test_needs_per_hour`, `test_clock_runs_past_midnight_into_sleep` |
| Walking: `window.__slCommit(dist, run, x, z)` | `min = walked*50/80 + ran*50/160`; `S.hour += min/60`; `needsTick(min/60)`; walking tires the player; at 24 logs "nodded off on a bench" and `sleep(true)` | near line 1096. `test_walking_and_driving_advance_the_clock` |
| Driving: `window.__slDrive(dist, x, z)` | `min = dist*50/450`; `S.hour += min/60`; `needsTick`; fuel cost; at 24 `sleep(true)` | near line 1094. same test |
| Station and train: `csFlush` | The station and train clock is separate: `CS.pend` gathers real seconds at 4 times real time (`CRATE`, a game minute every 15 s) while in a station or on a train; `csFlush` moves it into `S.hour` with `needsTick`, but stops at 23.98 and sets `CS.late`; it runs every 20 real seconds, on leaving, and on every save (`placeState`). `jrCine…` skips add to `CS.pend` | near lines 4430, 4839, 4912, 5175, 5356. **Not pinned** (needs the station scene) |
| `sleep(…)` | Sets the hour to the wake-up hour of the way the night passed (07:00 at home, 08:00 elsewhere or passed out, 06:30 outside, 09:00 hospital, 10:00 cell, 07:00 jail or shelter, 08:00 trip or a friend's sofa) | `test_sleep_at_home`, `test_sleep_modes`, `test_sleep_away_from_home_and_out` |
| A few direct edits | A random event adds an hour (`S.hour += 1`); a trip raises the hour to at least 17:00 on return; doctor visits and similar are `spendTime` | near lines 2247, 1338 |

**Standing still: nothing moves the clock.** The render loop reads `S.hour` and smooths the *displayed* hour (`shownHour`) but never advances it. (`test_time_does_not_pass_while_standing_still`)

Two clocks therefore exist: the game's `S.hour` and the station and train clock (`CS.pend`, 4 times faster than real time). They agree only because `csFlush` adds the pending time. The rest of the city has no clock of its own: ambient traffic, trams and boats run on real time and do not read `S.hour` except for lighting and rush-hour density (`rushInfo`, `rushNow`, `lightAt(shownHour)`).

### 2.3 Needs [V]
`needsTick(h)` runs only inside the writers above, never from a timer. Per hour: hunger −6, hygiene −2.8, fun −2.4 (each clamped 0 to 100). After the drop, hunger under 20 costs 1.5 mood an hour, hygiene under 20 0.6, fun under 15 0.8; hunger under 8 costs 2 energy an hour. Zero or negative `h` does nothing. (`test_needs_per_hour`, `test_needs_mood_and_energy_thresholds`)
Energy is not drained by time at all: it falls from walking (`S.flags.walkE`), from actions that list an energy cost, and from hunger under 8, and it rises in `sleep`. [S]

### 2.4 The day change [V]
`sleep(passedOut, mode)` is the only day change. In this order it: applies the day's sunlight mood effect, social −2 and a mood penalty under 15 energy, counts job days, pays sick-leave into the month's pay, then **`S.day++`**, adds housing-queue points, runs **`processBills()`**, `crimeDaily()`, resets the day's flags, rolls the weather, then drops hunger by 18 and hygiene by 8, applies the way the night passed (hour, energy and so on), then reads **`today()` of the new day** for: the 25th (payday and CSN), the 1st (car insurance and rent), 2 January (queue fee), `lifeDaily` (people, wants, civic events, evictions, the 20th child benefit), then logs the date and saves. The phone section wraps `sleep` (`sleep = function…`) to roll the to-do list. A random event and a 12% cold can follow, so tests fix `Math.random`. (`test_sleep_at_home`, `test_sleep_modes`)

### 2.5 Rent, salary, bills [V]
- **Rent** is taken when the new day is the 1st: `HOMES[home].rent`, halved (rounded) if `sambo`; with too little money it becomes a bill `rent for <month>`, −6 mood. Car insurance and tax, 1 100 kr, on the same day for an owned car. 2 January: the queue fee 210 kr if registered. (`test_rent_on_the_first`)
- **Salary**: shifts add to `S.pay` (gross); on the 25th, if `S.pay > 0` and a bank account exists, `pay × (1 − TAX)` (30%) is paid, `S.pay` reset, mood +5, then garnishing. Without a bank account nothing is paid and the pay waits. (`test_payday_on_the_25th`)
- **Garnishing** takes 30% of the net pay for bills at stage 4, fees first. (`test_garnishing_takes_30_percent_of_the_net_pay`)
- **Bills**: `addBill` due in 10 days. `processBills` runs at each day change; when the day reaches `due`: reminder (+60 kr, due +10), inkasso (+180, due +8, −4 mood), Kronofogden order (+680, due +10, −8 mood), utslag (−12 mood, `S.remark`, rent bills get an eviction date 14 days on). The day an eviction date is reached the home is lost (−25 mood). (`test_bill_stages`, `test_bill_stages_by_sleeping`, `test_unpaid_rent_ends_in_eviction`)
- **Child benefit** 1 250 kr per child on the 20th, with a personnummer. (`test_child_benefit_on_the_20th`)

All of these depend on the **date of the new day**, never on elapsed hours: if no `sleep` happens, no rent, salary or bill ever falls due.

### 2.6 Findings that may be defects (observed, not changed, [?] for the owner)
1. **Fixed 2026-11-18 (M26 part 1; the warning now follows the bank-account test).** Before the fix, on every payday with `S.pay > 0` and no CSN, the log said "Lönedag, but your lön can't be paid: you have no bank account." even when the pay was just paid. The `else` belongs to the CSN `if`, not to the bank-account `if`. Pinned as current behaviour until the fix.
2. **Fixed 2026-11-19 (M26 part 2).** CSN study money sat inside the `S.pay > 0` block, so a student with no job received no CSN on the 25th. It is now paid independently of lön, to a student with a residence permit card and personnummer and an active bank account on the day; it stops at the end of the course.
3. `__slCommit` and `__slDrive` cross midnight correctly, but `csFlush` stops at 23.98 and leaves the player to sleep; the three paths do not behave the same way at the end of the day.
Do not fix these inside M2 without a decision; they change money and messages.

## 3. Existing behaviour M2 must preserve
Every rule in §2.3 to §2.5 at the same game time, with the same results; the way each night passes; the date arithmetic from `START`. The tests in `tests/test_time_rules.py` are the executable form. A change to any pinned value is a balance change and needs the owner's approval, and the test must be updated in the same pull request with the reason.

## 4. Which systems should eventually respond to elapsed time ([P])
Needs drain (already by hours), the day change itself (currently a player action; a clock would let a day pass), shifts and opening hours (they read `S.hour` today), rent, salary, bills and queue fees by date, ambient transport schedules (today on real time), the station clock, weather change and lighting (read the hour). Which of these should *change* behaviour is open ([?], §6).

## 5. What the clock changes ([P], not decided)
- Time passing while standing still (the M2 acceptance criterion). Today it does not. `test_time_does_not_pass_while_standing_still` will have to be changed on purpose.
- One clock for city, station and train, in place of `CS.pend` at 4 times.
- Pause and speed settings.

## 6. Decisions for the owner before M2 starts
1. **Rate**: how many real seconds are a game hour while standing still (and whether the station's 15 s per game minute becomes the rate everywhere or stays a station rate). *Why:* every need rate and travel time is balanced for time passing only by action.
2. **Does the day end by itself at night** (forced sleep) or can the player stay up, and what does 24:00 do outdoors?
3. **Pause rules:** menus, modals, interiors and phone, and whether travel and rides run at one rate.
4. **Needs balance:** whether the per-hour rates stay as they are when time also passes idly (most likely they must be re-tuned).
5. **Date-based events** (rent, salary) while idle: fire at midnight by the clock, or only at a sleep as today.
6. **The three observations in §2.6.**
7. **Time of the ambient world** (transport timetables, opening hours) driven by `S.hour`, or left on real time.

## 7. Dependencies
M2 depends on M1 (the roadmap), which depends on closing M0. M0 is paused on the manual desktop checks ([QUEUE.md](../.agent/QUEUE.md)): "Sit down?" with the mouse, the HUD button, E, Enter and Y. M1 so far has the safety slices only (save safety `M1a`, import/export `M1b`); the save slots and the state module are not done. A clock needs somewhere to live: `S` today, the state module (M3 step 7) later, and a save that carries it. Do not start M2 before M1's state and save work is agreed.

## 8. Save compatibility and state
- The clock's state must stay in `S` (or the M1 state module) and in the existing save, with a migration for any new field; old saves must load with the clock at their saved `day` and `hour`. [P]
- `S.hour` and `S.day` meanings must not change for old saves. A new sub-hour precision field would be new state needing a `migrate()` step. [?]
- The station's `CS.pend` is already flushed into `S.hour` on save (M19), so a save never loses station time. [S]
- No save format change is made by this preparation.

## 9. Acceptance criteria for M2 itself ([P], to be agreed)
1. All of `tests/test_time_rules.py` passes unchanged except the standing-still test, which is replaced by one showing time passing at the agreed rate.
2. Standing still for N real seconds advances the clock by the agreed amount and drains needs by the same formula as an action of that length.
3. The station and the city show the same time at all times; entering and leaving a station changes nothing.
4. Rent, salary and bills fall due on the same dates and in the same amounts as before.
5. A journey of a given length costs the same game time as before (unless the owner decides otherwise).
6. A save made before M2 loads and plays to the same results.

## 10. Test coverage and limits
`tests/test_time_rules.py` runs the production functions through `window.__V`, added by the test, with `Math.random` fixed; no wall-clock waits except four animation frames in the standing-still test. **Not covered:** the station and train clock (`CS.pend`, `csFlush`), shifts and `jobPay`, `lifeDaily`'s other events, weather, the random events and the 12% cold, opening-hours checks (`isOpen`), the end of a bus, tram or boat ride (covered by `test_transit_rides.py` and `test_boat_rides.py` for money and time). The first four need scenes or state not worth pinning before the owner's decisions.
