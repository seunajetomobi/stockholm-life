# R2 "the world follows real time": plan

Status: **proposal, 2026-11-26; Q0 decided the same day.** Slice (a) is implemented on `feat/r2-world-realtime`. Slices (b) and (c) have not started. Stage R2 of [REALTIME_SPEC.md](REALTIME_SPEC.md); the writers of the hour are in [REALTIME_WRITERS.md](REALTIME_WRITERS.md). Line numbers are `index.html` at `1389ee6`.

## 1. The premise has changed: real time is already on by default
REALTIME_SPEC ("Design of R2 and R3 together") assumes the flag `REALTIME` is **off** by default, so that R2 can hide behind it until R3. On `main` it is **on**:
- `REALTIME=RTIME.enabled(location.search, localStorage, true)` (1263). The `true` is the default.
- It came from commit `4c1b010` (2026-11-22). That commit was on PR #53, which was closed, and was merged inside **PR #56** on 2026-11-25. **It is not live**: `live` is `76ec825`, which does not contain it.
- The tests keep the old clock: `tests/game.py` `new_context` writes `stockholmsliv-realtime='0'` unless a test asks for `realtime=True`.

Consequences:
1. **Most of the world already follows real time under `REALTIME`.** `today()` (1254) is `realDate()` (1265), the real Stockholm date of the life day. `syncClock()` (1264, every second at 6324) makes `S.hour` the Stockholm hour. So sunrise, sunset and day length (1269–1272), the season and `winter()` (1275, 4828, 4856), the tree and grass colours, opening hours (`openDay`, 759; `isOpen`, 765) and the offline weather month (`rollWeather`, 1304) are already real.
2. The spec's reason not to ship R2 without R3 ("a real sky over a game hour") no longer applies under `REALTIME`, because the hour is real. What is still incoherent is that actions take no time. That is R3's problem, and `main` already has it.
3. **Owner decision Q0 (2026-11-26): the corrections of slice (a) apply to the real-time mode itself, with no separate switch.** The first version of this plan put them behind a new switch, `rtworld`; that was removed. Separately, real time must not be the default in a public release until R3 is implemented and verified (Q0, part 2); the change of default is to be documented for review before it is made.

## 2. What is still wrong under `REALTIME` on `main`
| Item | Where | Under real time today |
| --- | --- | --- |
| City sky hour `shownHour` | `tick` 5872, `lightAt` 4807 | It eases towards `S.hour` by at most 0.075 per frame (`dt≤0.05`, 5798). At midnight `S.hour` drops from 23.99 to 0, so the sky **sweeps back through the whole day** (a flash of daylight). On a walk it runs up to 3 h ahead. |
| Start-up order | `start` 6313–6323 | The world is built (6317) before `syncClock()` (6323), so the sky starts at the saved hour (08:00 for a new life) and slides to the real hour. |
| Offline weather | `rollWeather` 1304 | Rolled only at a sleep and in `newGame`. A day that passes while playing, or a save loaded weeks later, keeps the old weather. |
| Dates of life days | `nextElectionDay` 1071, `fmtElection` 1224 | Still `dateOf` (the invented calendar): the election is put on an invented Sunday and shown with the invented date. |
| Red days outside `openDay` | `showPoi` 2567, hover 3627, `careOpen` 2087, lunch 992, `rushNow` 1689, `rushInfo` 3322 | These use `today().getDay()`, so a public holiday acts as a weekday. |
| Paperwork | `sleep` 2585–2623, `processBills` 2544, letters 2608–2610, `lifeDaily` 2626 | Runs once per calendar day, **only when the player sleeps**. Nothing happens on a day without a sleep, nor for days the page was closed. |
| Station and train clock | `csClk` 4961, `csFlush` 5369 | `CS.pend` grows at 4× and is thrown away every 20 s: a saw-tooth clock. Left for R6. |

## 3. Slices (one pull request each)
**(a) Date, season, sun, sky and offline weather: implemented, under `REALTIME` (owner, Q0).**
1. The city sky shows `S.hour` every frame. The station keeps `csClk` until R6.
2. The clock is derived before the first render and before the world is built (`rtWorldStart`), and in `newGame`.
3. Offline weather is rolled for the real month when the Stockholm day changes while playing, and on load when a day has passed since the save. A new life is already rolled in `newGame`.
4. `lifeDate(d)` gives the real date of life day `d`, for the election.

- **Save:** no format change; no new field.
- **Tests:** `tests/test_realtime_world.py` (6 browser tests under a fake real time) and `tests/test_realtime.py` (the named switch).
- **Risks:** a reload after a day away re-rolls offline weather at random. An existing life keeps its stored `S.civ.next`, which may now fall on a weekday until the next election is placed. The sun's azimuth stays the old approximation.

**(b) Opening hours by the real clock.** Under `REALTIME`:
- The place card, the hover label, `careOpen`, the lunch menu, `rushNow` and `rushInfo` use `openDay()`, so a red day counts as a Sunday.
- Optional: read OSM `PH` rules in `parseHours` (they make it give up today) and hours that cross midnight (`18:00-02:00` is never open).
- **Save:** none. **Tests:** a red weekday under a fake time (the place card, the hover and the vårdcentral are closed or on Sunday hours); unchanged with the switch off. Small; it could be merged into (a).

**(c) Bills, rent, pay and letters by calendar day.** Under `REALTIME`: a `dayRollover()` runs for each Stockholm day from `S.flags.rolled+1` to `S.day`, with that day's own date. It runs at midnight while playing and, for days the page was closed, on load. It takes the paperwork out of `sleep()`: queue points, `processBills`, the 25th (pay, CSN), the 1st (rent, car), 2 January (queue fee), `lifeDaily`, the letters, `invTick`, the day's resets and the phone's `todoRoll`. `sleep()` keeps the night's rest.
- **Save:** no format change. It reuses `S.flags.rolled` (written since `4c1b010`) but changes what it means. A starting value is needed for lives without it. **Save-system review required.**
- **Tests:** one roll across midnight (no double rent or pay when sleeping after midnight); a page closed from 24 Jan to 3 Mar rolls 25 Jan, 1 Feb, 25 Feb and 1 Mar in order, with bill stages per day; a same-day reload rolls nothing; the old clock is unchanged (`tests/test_time_rules.py`).
- **Risks:** double charges; a long absence means hundreds of rolls and a flooded log (a summary is needed); random daily things must not be multiplied.
- Split proposed: **(c1)** while playing; **(c2)** catch-up for closed days, with an "away" summary. Also fixed-date events on the real calendar: `FIXED['06-18']` Midsommarafton is wrong in most years (`holidays.js` computes it), and `'11-11'` is called Mårtensafton, normally 10 November (to be checked against a source).

Order: (a) → (b) → (c1) → (c2). (c) touches `sleep()`, which R3 turns into a task, so it should land before R3 or be designed with it.

| Slice | Save | Blocked by |
| --- | --- | --- |
| (a) | none | nothing (Q0 decides only when the switch goes) |
| (b) | none | nothing; Q5 for the optional holiday parsing |
| (c1) | the meaning of `S.flags.rolled`; save review | Q1, Q2 |
| (c2) | as (c1) | Q1–Q4 |

## 4. Decisions needed (owner, or the lead under the 2026-11-22 delegation)
- **Q0. Decided by the owner on 2026-11-26:** the slice (a) corrections apply directly to the real-time mode, with no separate switch. Real time stays available for controlled testing but must not be the default in a public release until R3 is implemented and verified; `main` must not be deployed with real time on by default. The change of default is documented for review first.
- **Q1. When the paperwork runs.** M2_SPEC §6 decision 5 (approved 2026-11-20) said "only at the day change", which then meant a sleep. REALTIME_SPEC supersedes only decisions 1 to 3, but its delegated decision 1 says paperwork follows calendar days. Confirm that rent, pay, bills and letters fire at Stockholm midnight even without a sleep.
- **Q2. What catches up for closed days.** Proposed yes: queue points, bill stages, rent, pay, CSN, child benefit, letters, eviction, investments. Proposed no: `crimeDaily`, random events, colds, the weather, the sunlight mood effect. Undecided: `S.jobDays` and sick pay per day.
- **Q3. Long absences.** Uncapped paperwork means three months away bring three rents, inkasso, Kronofogden and possibly an eviction. Keep that? Or add a grace rule (for example autogiro rent when the money is there) and an "away" summary?
- **Q4. Lives without `S.flags.rolled`.** Proposed: start from the saved `S.day`. A day without a sleep would then skip its paperwork once.
- **Q5. Holiday practice** (sources needed): pay when the 25th is a weekend or red day; OSM `PH` hours.

## 5. Found, outside R2
- R6: the station and train saw-tooth clock (see §2).
- `S.flags.snow` (the first snow, 2658) is never reset, so from a life's second November `winter()` is true all month.
- `TEMP` (1276, the offline monthly temperatures) has no source.
- `RTIME.fakeNow` (`?fakeclock=`) is not wired into the game; tests use `setFakeNow` directly.
- `docs/PROJECT_STATUS.md` does not record that `REALTIME` is on by default on `main`.
