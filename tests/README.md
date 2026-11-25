# Stockholm Life tests

Automated checks for the game, preserved from the 2026-10-31 audit and the two fixes after it (pendeltåg camera `df54793`, M14 `742403b`). They test the game as it is; they do not change it. There is no build step: the tests are Python scripts that drive headless Chrome against a local copy of the game.

## What is here

| File | What it checks | Browser | Test hook |
| --- | --- | --- | --- |
| `test_syntax.py` | `node --check` on the inline `<script>` of `index.html`, on every module under `src/` (nested folders too; each is loaded by `index.html` and read with the same path) and on `tools/flights-worker.js` (as an ES module); every local script `index.html` loads exists and is published by the Deploy workflow and verified by `tools/live_check.py`; the Python tools compile | No | No |
| `test_shard.py` | `tests/shard.py`, which splits the test files over the parallel CI browser jobs: every file in exactly one shard for 1 to 8 shards, the same split whatever the order, a file without a time still runs, the balance, and the completeness check each CI job runs before its tests (a file left out, an empty shard, nothing collected) | No | No |
| `test_geography.py` | `src/geography.js` ([docs/MODULES.md](../docs/MODULES.md)), in Node: its interface, the projection (the same as `tools/osm_stations.py`), districts, stations and lines, known routes, every station pair connected both ways, the nearest station, and a hash of every output pinned to the code before it moved. In the browser: the game uses the module's own objects, and a missing module stops startup with a message | 2 of its 8 tests (the rest run in Node) | 1 test |
| `test_format.py` | `src/util/format.js` ([docs/MODULES.md](../docs/MODULES.md)), in Node: its interface, `clamp`, `kr` (negative amounts, the real minus sign, rounding halves), `hhmm` (wrapping at 24 h, minutes rounding up to 60), `fmtDur` (the "60 min" and "1 h 60 min" roundings, kept from the original), and a hash of every output on fixed grids pinned to the code before it moved. In the browser: the game uses the module's own functions, and a missing module stops startup with a message naming `src/util/format.js` | 2 of its 8 tests (the rest run in Node) | 1 test |
| `test_sun.py` | `src/rules/sun.js` ([docs/MODULES.md](../docs/MODULES.md)), in Node: its interface, sunrise, sunset and day length against sunrise-sunset.org (seven dates, checked 2026-11-17, tolerance 10 and 18 minutes), the seasons at Stockholm (no polar day or night at this latitude), the summer-time switch, `isLight` and its limits, the original's behaviour for invalid input, the WMO tables and `WXICON`, a hash of every output pinned to the code before it moved, and the message when `src/util/format.js` is missing. In the browser: the game uses the module's own functions and adds no other name to the page, and a missing module stops startup with a message naming `src/rules/sun.js` | 2 of its 17 tests (the rest run in Node) | 1 test |
| `test_stockholm_time.py` | `src/rules/stockholm-time.js`, in Node: Stockholm time whatever the machine zone, daylight-saving days, life day, weekday, fake clock |
| `test_life_start.py` | `src/rules/life-start.js`, in Node: the real start of a life (`t0`), clock changes included |
| `test_namnsdag.py` | `src/rules/namnsdag.js`, in Node: Swedish name days (366 dates, 627 names) |
| `test_realtime.py` | `src/rules/realtime.js`, in Node: the real-time flag, the derived Stockholm clock, the developer-only fake clock |
| `test_holidays.py` | `src/rules/holidays.js`, in Node: Swedish public holidays from Lag (1989:253) |
| `test_tables.py` | `src/tables.js` ([docs/MODULES.md](../docs/MODULES.md)): `JOBS`, `COUNTRIES`, `OPEN`, `COURSES`, `ITEMS` and `HOMES` in Node (interface, shape, order, hashes pinned to the declarations before each move, `HOMES` district keys resolve in `AREAS`, plain data); in the browser the game's tables are the module's own objects, consumers (`routesFrom`, `EU_GOODS`, `hoursFor`, `shopItemsFor`, `homeD`, `assignAddress`, the housing modal's choices) work and the live tables equal the pinned ones, and a module that does not load stops the game with a message | Partly | No |
| `test_clock.py` | `src/rules/clock.js` ([docs/MODULES.md](../docs/MODULES.md), M2 stage 2), in Node: its interface, `dateOf` equal to the original formula for 1,500 days (day 1 = Saturday 24 October 2026, a leap day, New Year), `START` not changed by a caller, `CLOCK_RATE` = 4 (the station's rate), `reachesMidnight` at the boundaries (23.99, exactly 24:00, long spends); and a source check that `index.html` takes the calendar from the module and defines it nowhere else | No | No |
| `test_city_data.py` | `src/city-data.js` ([docs/MODULES.md](../docs/MODULES.md)): in Node, `parseHours` (common forms, the cases it gives up on, and a hash of its outputs pinned to the code before it moved) and `gunzipFetch` against a stubbed `fetch` (plain and gzip JSON, UTF-8, HTTP error, no `DecompressionStream`, invalid JSON, truncated gzip, network failure). In the browser: the game's names are the module's own, the real data loads through them, and a module that does not load stops the game with a message | Partly | No |
| `test_smoke.py` | Desktop 1366×768: city loads, WebGL canvas, no game file fails to load, character creation shown; "Go" starts a life and writes a save; each dock tab renders; every phone app opens without an uncaught error (at least 39 tiles); every places-bar button responds, Centralen opens its travel card | Yes | No |
| `test_save.py` | Reload restores name, day, hour, money and position; an old `stockholm-life-v3` save migrates (HUD 10:00, 1 200 kr, v4 written) | Yes | No |
| `test_prompt_mouse.py` | Station and train prompts answered with a real mouse (`page.mouse`: press, at least two frames, release): "Sit down?" Yes and No, another seat, getting off, entering the station; unchanged prompts keep their buttons, changed ones update | Yes | Yes |
| `test_prompt_keyboard.py` | The same prompts answered with the real keyboard (`page.keyboard`): E, Enter and Y for Yes, Escape and N for No, each counted so an answer given twice fails; a held key answers once; typing in a field and an open modal do not answer | Yes | Yes |
| `test_save_safety.py` | Save safety with faults injected into `localStorage`: failure and recovery messages; unreadable saves kept; the placeholder never saved; deportation (including refused deletion) and restart; lifecycle saves; nothing saved during journeys and lessons; court cases; several tabs. A hidden tab and the back/forward cache are simulated | Yes | Yes |
| `test_save_place.py` | Carry on where you left off (KNOWN_ISSUES M7, M19): a reload returns to the same place in Stockholm Central, to the train (at the platform, or arriving at the next stop if it was moving) and inside a café; station time is in the save; a place saved by an older version that played on is ignored; a v4 save loads as v5. Export and import of a life: bad files refused (not readable, wrong format, newer version, changed, incomplete); full storage changes nothing; the life before an import is kept; a file exported in one browser carries on in a fresh one | Yes | Yes |
| `test_save_slots.py` | Save slots, part A (M1c): the slot index `stockholm-life-slots-v1` and the active slot. Every fixture loads as slot 1 with its stored bytes unchanged; a missing index is built without touching a life and a browser with no life gets none; a corrupt, truncated or malformed index is copied first (`stockholm-life-slots-corrupt-<ts>`, never pruned) and rebuilt, and when the active slot cannot be told saving pauses and nothing changes; the active slot is the one loaded, saved and kept across reloads, and the v3 fallback is slot 1's; data is written before the index and an interrupted index write is repaired by the next save; a stale tab stops (narrows M20, not atomic); deportation ends only the active slot and lists it as ended; import keeps 3 copies and never prunes evidence. Negative controls on a scratch copy with `SL_INDEX_HTML` | Yes | No |
| `test_save_slot_ui.py` | Save slots, part B (M1c): the Save slots window and its actions. Five slots listed with their status and only fitting actions; opening another slot saves and reads back the current life first and is refused during a journey, an arrest, a driving lesson or a train ride, when storage cannot take the save or the index, or when another tab changed the slots; an ended or unreadable slot cannot be opened; a new life in an empty slot; rename (metadata only, validated, escaped); delete (typed name, verified copy first, never the active slot, evidence kept as `-corrupt-`); start over; per-slot export and import; restoring a kept copy (the current life is copied first, the chosen copy is never touched); the newest 3 copies per category are kept and `-corrupt-` evidence is never pruned; storage that fails at each step and an interrupted action leave every other key byte for byte. Negative controls on a scratch copy with `SL_INDEX_HTML` | Yes | Yes |
| `test_save_fixtures.py` | Saves from earlier builds still load and migrate (quality strategy A7). Fixtures in `tests/fixtures/saves/` ([README](fixtures/saves/README.md)): real saves written by the game at commits `55c196b`, `870fe30` (the live site) and `3eb5711` (street, Stockholm Central, train, café), and one synthetic v3 life, each with source, generator, version and file hash in `manifest.json`. Checks: the files match the manifest and README, no personal data; migration keeps every value (only `v` 4 → 5), adds only `bills`, drops nothing and is idempotent; import refuses a bad hash, version 0 or 6, a bad format; each fixture loads at start as version 5 with the same values (apart from live weather, and station time in a station or train), the place comes back, and save, reload and export, import are stable. 13 tests, 9 with a browser. `fixtures/negative_controls.py` shows the tests detect 8 injected migration and import faults (in a temporary copy of `index.html`, never the repository's); `fixtures/generate_saves.py` makes the fixtures (by hand only) | Yes (9 of 13) | Yes |
| `test_vehicle_lanes.py` | Buses stay inside the street: the bus route lines near a place in Vasastan, with the game's kerb shift (`busKerb`) applied, never end outside the carriageway, and the old uncapped shift does (so the test notices it coming back); and cars on road classes 4 to 9 stay inside the carriageway. Both need the city loaded | 2 of 2 tests | 1 test (an extra `window.__V` for the names) |
| `test_transit_rides.py` | Rides on SL buses and trams from a stop. The bus tests were written before trams were added and pin what a bus journey does (a hash of the lines offered at 371 real bus stops; three complete journeys: ticket, SL card in rush hour, fare dodging, with their money, time, mood, log and arrival). The tram tests: which tram lines each tram stop and station offers (no mixing with buses, stops in order), the wording of the actions ("Take tram 7 towards Waldemarsudde"), that a tram journey runs on its track with no sideways shift while a bus keeps its own, and complete tram journeys from a `tram_stop` and from a station (Tvärbanan), including the cars in the scene and gone afterwards. The journeys step the game's own `busTick`, because a frame in the test browser takes about a second | 7 tests (all with a browser) | 1 test (`window.__V` for the names) |
| `test_boat_rides.py` | Rides on SL's own boats from a pier (pendelbåt 80, Djurgårdsfärjan 82). Which piers offer which line (no Waxholm, cruise, canal or Finland ferries; no buses mixed in), the piers in order, the wording ("Take boat 80 towards Ropsten", the loop lines named by their last pier), that a boat runs on the route line with no shift and only where the city map has water (båt 89 is not offered: its piers lie beyond the map), and complete journeys (Nybroplan to the next pier and to Ropsten, Slussen to Djurgården): fare, SL card, fare dodging, time, log, arrival, the boat model in the scene and gone afterwards, the calls at the piers in between. Steps the game's own `busTick` | 7 tests (all with a browser) | 1 test (`window.__V` for the names) |
| `test_time_rules.py` | M2 preparation ([M2_SPEC.md](../docs/M2_SPEC.md)): pins how game time passes today and what it triggers, on the production functions with `Math.random` fixed and no waiting: the calendar, the needs drain per hour and its thresholds, the clock running past midnight into sleep, the day change at home and in each way a night can pass, rent on the 1st, payday on the 25th (and CSN, and the quirks found), garnishing, the bill stages (also by sleeping), eviction, child benefit, walking and driving advancing the clock, and that time does not pass while standing still | 21 tests (all with a browser) | 1 test (`window.__V` for the names) |
| `test_layout.py` | 390×844 and 520×900 (touch) and 1366×768: no horizontal overflow on the intro or while playing; dock, joystick, Run, zoom and places bar inside the viewport | Yes | No |
| `test_m14.py` | M14 regression at the same three sizes: in the station, boarding (with the "Sit down?" prompt), a three-line prompt (phones), seated. The message strip is at most 60 px tall; on phones it overlaps none of the ride HUD, prompt, joystick, Run, zoom or dock; on desktop it is still centred near the top. The strip never covers any visible control (ride HUD, prompt, top bar, Next up, places bar, zoom, joystick, Run, dock…), even by part of a pixel: two- and three-line messages in the station, boarding (prompt open, also three lines tall) and seated (prompt closed), at 360×640, 375×667, 390×844, 520, 601, 640 and 768 px wide, landscape 640×360, 844×390 and 1024×768, and four desktop sizes; where nothing is in the way the desktop strip keeps its place. Explicit regression: the Home button at 768×1024. Where no place is free (a three-line message at 640×360) the strip may share space only beneath a control, which stays on top and takes the tap. The strip also follows layout changes between the game's frames (the top bar growing, which moves the HUD through `--boardH`; the HUD growing; a resize) with the periodic HUD update held. Layouts are measured once they have stayed the same for three rendered frames, not after a fixed time | Yes | Yes |
| `test_traincam.py` | Pendeltåg camera regression: every tested seat (60) × 24 yaws × 3 pitches and 17 standing spots × 24 yaws keep the camera inside the car and out of posts, poles and cab walls; seated default is "You" with the avatar visible; "Eyes" puts the camera exactly where it was before `df54793`; standing resets pitch; the camera stays below the gangway header; walking along the aisle with W (real key presses) moves you and the camera follows, inside the car with you on screen; getting off restores the city camera; at 390×844 the ride HUD fits in three rows with the short "🧍 You" label | Yes | Yes |
| `test_live_check.py` | `tools/live_check.py` (see "Live check" below): the verdict rules and CDN confirmation window, the expected sources (local Git, simulated GitHub API), exact file comparison by Git blob ID, gzip in transit and gzip files, the Deploy workflow's data rules (and that they still match `deploy.yml`), redirects checked hop by hop, DNS pinning, Chromium's resolver rules, route interception of the page and every same-origin file, failure classification, safe output paths, and that a run changes nothing in the repository. Uses only loopback servers and generated sites in `tmp_path`; no internet | Some | No |
| `game.py`, `conftest.py` | Shared helpers: local server, browser, test hook, page set-up, measurements | | |

Every browser test fails on an uncaught JavaScript error (`pageerror`). Console errors and failed requests to external services (weather, SL, flights, news) are recorded but do not fail a test, because those services can be offline. A failed request for the game's own files does fail `test_smoke.py`.

`test_traincam.py::test_place_label_after_getting_off` is marked **xfail**: it documents KNOWN_ISSUES L10 (the place label can stay on "Pendeltåg 41" after getting off). It reports `XFAIL` while the issue exists and `XPASS` if it no longer shows; neither fails the run.

## Install (once)

Needs Python 3.10+ and Node.js (for the syntax check).

```sh
python3 -m pip install --user -r tests/requirements.txt
```

The tests use the browser in `CHROME` when it is set, otherwise the system Google Chrome at `/usr/bin/google-chrome` when it exists, otherwise Playwright's own Chromium. The first line of every run says which one. GitHub Actions always uses the Chromium build that the pinned Playwright version is made for; to run locally on exactly that browser:

```sh
python3 -m playwright install chromium
CHROME=$(python3 -c 'from playwright.sync_api import sync_playwright as s; p = s().start(); print(p.chromium.executable_path); p.stop()') python3 -m pytest tests
```

Rendering is software WebGL (SwiftShader), so no GPU is needed.

## Run

From the repository root:

```sh
python3 tests/test_syntax.py            # syntax only, about 1 s
python3 -m pytest tests                 # everything
python3 -m pytest tests -m "not hook"   # without the station/train tests
python3 -m pytest tests/test_m14.py     # one file
python3 -m pytest tests -k 390          # only the 390 px cases
python3 -m pytest tests -s              # also print load times and recorded console errors
python3 -m pytest $(python3 tests/shard.py 2 6)   # shard 2 of 6, as one CI job runs it
```

**Local server.** The tests use a server already running on port 8000 (for example `./start.sh`) if it serves this repo's `index.html`, and otherwise start `python3 -m http.server 8000 --bind 127.0.0.1` themselves and stop it afterwards. If port 8000 serves a different `index.html` (another checkout, an edited copy), the run stops with a message rather than testing the wrong code. Another port can be set with `SL_PORT=8123`, but the flights relay only allows port 8000, so live flights will show CORS errors there (they do not fail the tests).

**Output.** Screenshots go to `tests/output/` (ignored by git), named after the test and screen width, e.g. `layout-390.png`.

**Speed.** Each browser test loads the whole city (about 12 MB of data) and the software renderer runs at 1–2 fps, so a full run takes a while. Frame rates measured here say nothing about real hardware.

**In CI** the suite runs in six parallel jobs, `browser shard 1 of 6` to `6 of 6`. `tests/shard.py` splits the files by their time in CI (the table in that file; longest first, each to the shard with the least time so far), so each job takes about 20 minutes instead of about 2 hours for the whole suite in one job. Each job first checks that every file pytest collects from `tests/` is in exactly one shard. The required check `tests-browser` is a last job that passes only when all six passed. A new test file needs no change to run; add its CI time to the table in `tests/shard.py` when it takes more than a minute or two, so the shards stay even.

## The test hook

The station, the train and the cameras live inside the `buildWorld()` closure, and walking to Stockholm Central at 1–2 fps would take far too long. The `hook` tests (`test_m14.py`, `test_traincam.py`) therefore use a **test-only copy** of `index.html`:

1. `game.hooked_html()` reads `index.html` from disk and replaces the closure's last statement, `return API;`, with `window.__T={csEnter, jrStart, jrSit, …, get CS(){…}, get JR(){…}};return API;` (the full list is `HOOK_NAMES` and `HOOK_LIVE` in `game.py`).
2. Playwright's `context.route('**/index.html', …)` serves that copy to the test browser only. Data files come unchanged from the local server.
3. The tests then call the game's own functions through `window.__T` (for example `__T.csEnter(__T.CS_DOORS[0])` to go inside Central, `__T.jrStart(...)` to board).

The file on disk, the local server's copy and the published game are never changed, so normal play cannot see the hook. If `return API;` disappears or appears twice, the tests stop with an explicit message; if a hooked name is renamed, the page throws a `ReferenceError` naming it at boot. Update `HOOK_NAMES` when that happens.

To run the hooked tests on another version of the game, point `SL_INDEX_HTML` at a saved copy. This is how the M14 test was checked against the code before the fix, where it fails with the original 365 px strip:

```sh
git show df54793:index.html > /tmp/before-m14.html
SL_INDEX_HTML=/tmp/before-m14.html python3 -m pytest tests/test_m14.py -k 390   # expected: 1 failed
```

The prompt tests have negative controls too. `test_prompt_mouse.py` run against the `promptSet` from before the fix (`6e9ac76`) must fail: Sit down Yes and No, the buttons staying the same, changed content updating and a new seat (getting off usually fails too; entering the station can pass by luck). The keyboard does not use the buttons, so `test_prompt_keyboard.py` passes on that build; its controls are copies of the game with the keydown handler deliberately broken, one change per control:

| Control | Broken copy | Tests that must fail |
| --- | --- | --- |
| K1 | keys typed in a text field are not ignored | `test_typing_in_a_field_does_not_answer` |
| K2 | keys are not ignored while a dialog is open | `test_open_modal_blocks_the_keys` |
| K3 | Y no longer answers Yes | `test_sit_yes_with_key[y]` |
| K4 | N no longer answers No | `test_sit_no_with_key[n]` |
| K5 | E answers Yes twice | `test_sit_yes_with_key[e]`, `test_get_off_with_key`, `test_enter_station_with_key`, `test_held_key_answers_once` |

Because the hook jumps straight into the station and the train, a hooked test shows that the code works once you are there. It does not show that a player can walk there, buy a ticket or pass the gates.

## Live check (`tools/live_check.py`)

A read-only check that the published site serves exactly one commit and that the game starts there. It never deploys, pushes, fetches or changes Git refs, and reads no credentials. By default it writes no file at all. Only `--json` and `--screenshot` write, each a new file (never overwriting an existing file or following a symbolic link, mode 600). Those paths are refused inside this repository and inside the `--repo` repository unless `--allow-repo-output` is given; `.git` and `tests/output/` there are refused even then.

```sh
python3 tools/live_check.py --expect <full 40-character SHA>                     # files and browser startup, 1 round
python3 tools/live_check.py --expect <sha> --rounds 4 --interval 300 --json /tmp/live.json   # after a deployment
python3 tools/live_check.py --expect <sha> --no-browser                          # files only
python3 tools/live_check.py --expect <sha> --source github                       # expected files from GitHub, no local repo
```

`--expect` is required and must be a full SHA; the tool never compares against a branch. What it checks:

0. **Hosts without `version.txt`** (Cloudflare, `https://stockholmsliv.app/`): `--no-version-file` (implied for that host, `--source git` only). The targets are every file of the commit that `.assetsignore` does not exclude, `index.html` is read at `/` (Cloudflare redirects `/index.html`), there is no `version.txt` target, and the report says the commit is identified by file contents.
1. **Files.** The expected list comes from the commit itself (`index.html`, every file under `data/`, and `version.txt` = the SHA and a newline, as the Deploy workflow writes it), from the local repository (`git ls-tree`, read-only) or with `--source github` from the Git Trees API. Each live file is compared by its Git blob ID over the exact bytes served (gzip in transit removed, gzip files kept).
2. **Rounds and the CDN.** GitHub Pages caches files for 10 minutes (`max-age=600`), so a difference counts as a confirmed mismatch only if it stays the same over at least that window (`--rounds`, `--interval`). A difference seen once, or edges disagreeing, is INCONCLUSIVE, not FAIL. Every round is reported.
3. **Data.** The bytes that match are checked with exactly the Deploy workflow's rules for `b`, `r` and `m` (`test_live_check.py` fails if the two ever differ).
4. **Browser.** Headless Chromium starts the game with every same-origin request intercepted: the tool fetches it, hashes it and gives the page exactly those bytes, so it knows the browser ran the verified files. Startup needs `#loading` gone, a WebGL canvas, no fallback message and the character-creation screen. A JavaScript error when every file matched is a game defect (FAIL); outside services or CDNs failing are only warnings, or INCONCLUSIVE when a required startup script is missing.
5. **Deployment record** (GitHub API, no login): evidence only. GitHub records the commit the workflow was started from, not the commit it published.

Exit codes: 0 PASS, 1 FAIL (a confirmed mismatch, data that fails the Deploy rules, or a game defect), 2 INCONCLUSIVE (could not check; nothing proven wrong), 3 usage or local error.

**Loopback mode.** An `http://` URL switches on the mode the tests use: every connection must go to a loopback address, names are resolved once and pinned (only `localhost` and the test resolver's names), redirects are checked before they are followed, Chromium only resolves pinned names, and every other outside request is refused before it is made. The test-only settings `SL_LIVE_GITHUB_API`, `SL_LIVE_EXTERNAL_STUBS`, `SL_LIVE_TEST_RESOLVER`, `SL_LIVE_TEST_SINK`, `SL_LIVE_FAULT` and `SL_LIVE_TEST_CHROME_ARGS` work only in this mode. To prove the tests use no network:

```sh
unshare -rn sh -c 'ip link set lo up && python3 -m pytest tests/test_live_check.py'
```

**What it cannot see.** Each request reaches one CDN edge; it cannot list the edges, nor prove that no extra files are live. The browser's same-origin requests go through Playwright's HTTP client rather than Chromium's own network stack. Under SwiftShader it shows that the game starts, not how well it runs, and it does not replace the checks on real devices.

## Still manual

These need a real GPU, a real phone or a long run, and are listed in `docs/TEST_PLAN.md` §4:

- Frame rate and feel on desktop and phones; touch joystick; touch-drag camera rotation.
- Pendeltåg camera on real hardware (several seats both ways, a full turn by mouse and touch, Eyes and back, stand up, gangway, phone HUD readability).
- A real pendeltåg journey: departing, a tunnel and the tunnel-exit cinematic, arriving, getting off at a real stop (the automated test uses a shortcut), the place label afterwards.
- Walking into Stockholm Central, tickets, gates.
- The M14 strip on a real iPhone (safe-area insets) and Android phone, and in a 601–640 px window.
- Offline behaviour (TEST_PLAN.md §3.2 item 7) is not automated yet.
- Everything else in TEST_PLAN.md §2 "Not tested": interiors, Arlanda, driving, transit rides, day change, bills, crime, emergencies, elections, audio, the other origins.
