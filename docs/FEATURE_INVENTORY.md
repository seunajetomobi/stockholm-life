# Feature inventory

What the game does today, measured on `main` at `3d04635` (2026-11-01). The live site serves the game files of `870fe30`: the pendeltåg camera and the message-strip changes on `main` (PR #3 `40d913e`, PR #4 `3d04635`, and PR #6 `d9b8882`, merged after this measurement) are merged but not yet deployed; current status in [PROJECT_STATUS.md](PROJECT_STATUS.md). M1a save safety (PR #12, `44c455d`) was merged after this measurement and is not deployed; it is reflected here only where it resolved H3 (2026-11-07), and the rest of this inventory has not been measured again. M1b (PR #16, `ff95989`) and the "Sit down?" prompt fix (PR #18, `23906b7`) were merged on 2026-11-08 and are not deployed; they are reflected only in the saving and phone rows and the summary (2026-11-08). First written in the audit of 2026-10-31.

## How to read this

**Maturity**

| Level | Meaning |
| --- | --- |
| PRODUCTION-READY | Complete for its purpose, tested, nothing significant missing |
| FUNCTIONAL | The underlying behaviour works and is exercised by tests or verified use |
| PARTIALLY FUNCTIONAL | Real behaviour exists, but important parts are missing or menu-only |
| PROTOTYPE | A first version or a menu/visual stand-in; the behaviour the vision needs is mostly absent |
| NOT STARTED | Nothing in the code |
| PLANNED | Agreed in the roadmap, nothing built yet (used in the planned-features list) |
| UNVERIFIED | Code exists, but no test or observation has confirmed that it works (used in the detail tables) |

A system is not counted as functional because a button, menu or visual exists; only working behaviour counts.

**Evidence:** **[C]** read in `index.html` (search for the names given); **[T]** covered by the automated tests in `tests/`; **[B]** observed in a headless browser run; **[B-hook]** observed in a test that reaches the station or train through the test hook rather than by playing there; **[L]** a live service or the GitHub API probed. Headless runs use software rendering, so they say nothing about frame rate or feel on real devices.

## Status at a glance

| Status | What it covers today |
| --- | --- |
| **Implemented and working** | Loading the city; character creation; save, reload and v3 migration; live weather; SL departures and ferries; all phone apps open (40 on `main`); the travel picker; one prompt at a time in the station and train, answered by the mouse and keys on the first try on `main` (PR #18, not deployed); the approval-gated release pipeline; the automated test suite |
| **Implemented but incomplete** (works, but not deployed, not verified on real devices, or a defined part missing) | Pendeltåg camera and station/train message strip (merged, not deployed, headless only); saving (one slot; on `main`, failures are reported since M1a, and the place is restored and lives can be exported and imported since M1b, both merged but not deployed, so the live site still fails silently and returns you to the street); live flights (security queue times unavailable until the relay is redeployed) |
| **Prototype or partially functional** | City and world, movement, employment (menu shifts), economy, housing (renting only), transport (rides abstracted), time (stops when you stand still), interiors (generic rooms), NPCs (ambient only), relationships (records only), inventory, missions (goals only) |
| **Code exists, unverified** | Arlanda arrivals and customs, driving lessons and test, a full pendeltåg ride between stations, start-up fallback messages |
| **Planned, not implemented** | Mission system, independent game clock, save slots, the state module, modules, playable work, NPC schedules and memory, buying and furnishing homes, performance overlay, multiplayer preparation (see [MASTER_ROADMAP.md](MASTER_ROADMAP.md)) |
| **Known issues** | [KNOWN_ISSUES.md](KNOWN_ISSUES.md); the most important: one save slot (H4), the monolithic file (H6), the out-of-date relay (M1), merged work not deployed (M15) |

## System maturity

| # | System | Maturity | Evidence |
| --- | --- | --- | --- |
| 1 | Player and character | PARTIALLY FUNCTIONAL | Character creation with 3 backgrounds (`BG`), many origin countries and appearance options [C][T]; avatar models; W/A/S/D, joystick and tap-to-walk on real streets [C]. Movement slows below 20 fps (50 ms step cap); auto-walk can pass through building footprints in narrow passages; the city camera is an orbit camera |
| 2 | City and world | PARTIALLY FUNCTIONAL | About 84,000 OSM buildings in 1,101 streamed tiles, streets with lanes and signals, rail, water, parks, POIs with opening hours [C][B]. Low visual fidelity (box extrusions); main data files cannot be regenerated from the repository |
| 3 | Buildings and interiors | PROTOTYPE | Only POIs that `kindFor` maps (about 13 kinds) are enterable, each as one generic room (`buildRoom`) [C]. Purpose-built interiors only for Stockholm Central and Arlanda. Interior state is not saved |
| 4 | NPCs and society | PROTOTYPE | 20–36 ambient pedestrians plus cars and bikes spawned around the player (`ensureAgents`) [C]; no homes, jobs, schedules or memory. Elections, movements and demonstrations are menu flows |
| 5 | Employment and careers | PARTIALLY FUNCTIONAL (menu-driven) | 14 jobs with requirements and applications (`JOBS`); a shift is a 4-hour action (`workAct`); performance from needs (`afterShift`); promotion after 10×level shifts; sick-pay rules [C]. No playable work |
| 6 | Economy and finances | PARTIALLY FUNCTIONAL | Gross pay collected in `S.pay` and paid on the 25th at about 30 % flat tax, only with a bank account; rent on the 1st; bills escalate reminder → inkasso → Kronofogden with garnishing (`processBills`); CSN loans; ISK funds as a random walk [C] |
| 7 | Housing | PARTIALLY FUNCTIONAL (renting only) | 10 homes (`HOMES`), housing queue at 20× speed, sublets and first-hand contracts, rent [C]. No purchase, no customisation; the home interior is a generic room by type |
| 8 | Inventory and shopping | PROTOTYPE | 8 items (`ITEMS`) with use effects (`useItem`), the bag, shop menus [C][T: bag opens] |
| 9 | Relationships | PROTOTYPE | `S.people` records with a trait label and numeric friendship and romance values, decaying when absent (`peopleDaily`); dating, chats, calls [C][T: apps open]. People are not present in the world; no memory |
| 10 | Transportation | PARTIALLY FUNCTIONAL | Transit vehicles move on real lines (`updateTransit`); rides are abstracted (`ride`, `busRide`); one detailed pendeltåg ride from Stockholm Central with the train camera [B-hook][T]; live SL departures [L][T]; driving lessons and test (`startLesson`) [C]; taxis. Most journeys are a travel card that skips time |
| 11 | Time and calendar | PARTIALLY FUNCTIONAL | Time advances only with walking, driving and actions (`spendTime`); standing still stops time; real calendar dates; weekdays only used for healthcare opening hours; a separate station clock (`csClk`) [C] |
| 12 | Weather and seasons | FUNCTIONAL | Live Open-Meteo weather drives sky, rain, snow, fog and wind, clothing advice and mood effects (rain without a coat, darkness) [C][L][T: Weather app]; seasons from the real date |
| 13 | Missions and progression | PROTOTYPE | Five long-term goals, daily wants, "next steps" advice, to-do list, Arlanda guide [C][T: tabs render]. No mission system |
| 14 | Phone and interface | FUNCTIONAL | All phone apps open without errors (40 on `main`, including the M1b "Save file" app; the smoke test requires at least 39); live data apps (weather, departures, ferries, flights, news) [T]. Some apps are information screens. The station/train message strip keeps its place unless it would cover a visible control or leave the screen, then moves to the nearest free place; where none exists (a three-line message at 640×360) it sits beneath the controls, which stay visible and tappable (PR #4) [T][B-hook]; phone-layout leftovers L9 and L14 (KNOWN_ISSUES) |
| 15 | Saving and persistence | PARTIALLY FUNCTIONAL | One localStorage key (`stockholm-life-v4`; loading falls back to `stockholm-life-v3`), migration from v3 (`migrate`) [T]; save failures reported and retried on `main` since M1a (PR #12, merged, not deployed; KNOWN_ISSUES H3 resolved) [T], still silent on the live site; on `main` since M1a, saving also happens when the page is left or the tab hidden; on `main` since M1b (PR #16, merged, not deployed): save version 5 under the same key, the place restored after a reload (Stockholm Central, the pendeltåg, interiors; cars and buses return to the street), and export and import of a life with a SHA-256 check [T]; no save slots |
| 16 | Performance and optimisation | PARTIALLY FUNCTIONAL | Tile streaming, culling, instancing, Fast/Rich presets with auto-switch [C]. About 12 MB parsed at start; never measured on real devices |
| 17 | Testing and reliability | FUNCTIONAL (for its scope) | 33 tests in CI, required for merging (syntax, smoke, save, layout, M14, train camera) [T]. No unit tests of rules; no tests of day change, economy, jobs or housing |
| 18 | Multiplayer preparation | NOT STARTED | No networking; global mutable state, unseeded randomness and movement-driven time [C] |
| — | Release pipeline | FUNCTIONAL | Approval-gated manual deployment of an exact commit, tests before deploying, rollback to any commit on `main`, live verification [L] |

## Details by area

### Boot, onboarding and persistence

| Feature | Status | Notes |
| --- | --- | --- |
| Loading screen and city data | FUNCTIONAL | [T] loads in 10–25 s locally; about 12 MB from GitHub Pages [L] |
| Fallback messages (no data, no WebGL, `file://`) | UNVERIFIED | [C] in `start()`, never triggered in tests |
| Character creation (`intro`) | FUNCTIONAL | [T] default "Born in Stockholm" life; the newcomer and "elsewhere in Sweden" origins are not covered by tests |
| Save and load | PARTIALLY FUNCTIONAL | [T] reload restores name, day, hour, money and position; see system 15 |
| Corrupted save | FUNCTIONAL | [T] starts a fresh life without errors; the broken save is overwritten without warning |
| Migration of v3 saves | FUNCTIONAL | [T] |

### Player, camera and movement

| Feature | Status | Notes |
| --- | --- | --- |
| Avatar (models, outfit, skin, hair, headwear, beard, glasses, height, build) | FUNCTIONAL | [C][B] |
| Keyboard and joystick | PARTIALLY FUNCTIONAL | [B] speed tied to frame rate; touch joystick not exercised |
| Tap-to-walk on real streets | PARTIALLY FUNCTIONAL | [C] occasional passage through building footprints |
| City camera | PARTIALLY FUNCTIONAL | [C] orbit camera that pulls in when blocked; no follow camera with collision |
| Pendeltåg camera (seated "You", "Eyes", standing) | FUNCTIONAL (headless; merged, not deployed) | [T][B-hook] camera inside the car and clear of posts, poles and cab walls at all 60 tested seats × 24 yaws × 3 pitches and 17 standing spots; "Eyes" unchanged; standing resets pitch; walking with W keeps the camera following. **Feel, frame rate and touch dragging on real devices not verified** |
| Interaction prompts | FUNCTIONAL | [T] one prompt at a time in the station and train (`promptFor`/`promptSet`) |
| Station/train message strip | FUNCTIONAL (headless; merged, not deployed) | [T][B-hook] a short bar that keeps its CSS place unless it would cover a visible control or leave the screen, then moves to the nearest free place measured from the rendered controls. If no free place exists it is placed beneath the controls, which stay visible and interactive (the strip has `pointer-events: none`); the documented case is a three-line message at 640×360, where it sits under Run (PR #4; KNOWN_ISSUES M16, L14). **Real phones and tablets not verified** |

### World

| Feature | Status | Notes |
| --- | --- | --- |
| Buildings, tile streaming, labels | FUNCTIONAL | [C][B] low visual fidelity |
| Streets, lanes, signals, bridges, tunnels | UNVERIFIED in tests | [C] |
| Parks, water, trees, seasons; day and night | UNVERIFIED in tests | [C] |
| Live weather | FUNCTIONAL | [L][T] |
| Billboards with sponsor slots; landmarks (Sergels torg, Centralen facade) | UNVERIFIED | [C] |

### Buildings and interiors

| Feature | Status | Notes |
| --- | --- | --- |
| Enter a POI building | PROTOTYPE | [C] about 13 kinds, generic rooms, static staff |
| Stockholm Central and Stockholm City | PARTIALLY FUNCTIONAL | [B-hook][T] station mode, messages and prompts work; walking in, tickets, gates and the exchange are not tested. Övre hallen and long-distance platforms are not built (stated in the game) |
| Arlanda arrivals (belt, suitcase, customs) | UNVERIFIED | [C] reached only through the "moving from abroad" origin, not tested |

### Transport

| Feature | Status | Notes |
| --- | --- | --- |
| Travel picker (walk, transit, taxi with time and cost) | FUNCTIONAL | [T] |
| Transit vehicles on real lines; rides | PARTIALLY FUNCTIONAL | [C] rides are abstracted |
| Pendeltåg journey (departing, tunnels, arriving, getting off at a real stop) | UNVERIFIED | [B-hook] boarding and getting off by shortcut are tested; a full ride between stations is not |
| SL live departures and ferries | FUNCTIONAL | [L][T] |
| Driving, lessons and test | UNVERIFIED | [C] |
| Live flights; security queue times | FUNCTIONAL / not available | [L] queue times need the relay redeployed (KNOWN_ISSUES M1) |

### Phone apps

All 39 tiles open without errors [T]: Phone, Chatt, Mail, Kivra, BankID, Swish, Handelsbanken, Swedbank, SEB, SL, SJ, Mälartåg, Flights, 1177, Alltid öppet, 112, SVT Nyheter, DN, Aftonbladet, Expressen, Ekot, Weather, Departures, Ferries, Invest, Bank, To-do, Bag, Find, Contacts, Dating, Jobs, Courses, Housing, Bills, Election, Movement, Rights, Wait 1 h. Election and Rights switch to the Society tab; Wait 1 h passes time. (The original audit said 40; there are 39.)

## Planned, not started

Per [MASTER_ROADMAP.md](MASTER_ROADMAP.md): save slots and saved world state (M1); an independent game clock (M2); modules (M3); missions, interior definitions, a playable job, real shopping and a money ledger (M4); NPCs with homes, schedules and memory (M5); buying and furnishing a home, more jobs and buildings (M6); performance measurement and per-tile loading (M7); multiplayer preparation (M8).

## Simulated or estimated content (labelled in the game)

- Bromma aircraft without the relay; other flights on the Arlanda arrivals board.
- Station timetables in game time.
- Exchange rates when frankfurter.dev is unreachable.
- ISK fund returns; the housing queue at 20× speed.
- SJ and Mälartåg fares (estimates).
- Facts, fees and rules checked in October 2026.

## Systems that do not share one consistent state

- The 3D world keeps its own state (`IN`, `CS`, `JR`, `DR`) inside `buildWorld()`; only `S` is saved, so reloading inside a building, the station, a train or a car returns you to the street (Arlanda is the exception).
- Two clocks: `S.hour` in the city, `csClk` in the station.
- Persistent people (`S.people`) and the 3D pedestrians are unrelated.
