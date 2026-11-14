# Modules

How Stockholm Life is divided into modules: what exists now, how a module is written, loaded and tested, how the game starts, and the order in which the rest of `index.html` moves out. It follows [TECHNICAL_ARCHITECTURE.md](TECHNICAL_ARCHITECTURE.md) §3 (evolve, don't rewrite; keep three.js r128 and no-build static hosting) and the M3 rule "move before you change" ([MASTER_ROADMAP.md](MASTER_ROADMAP.md)). Sections are marked **Observed** (from the code) or **Target** (proposed direction, each step approved separately).

Written with the first move (`refactor/modules-first-extraction`, from `main` `3eb5711`), 2026-11-14.

## 1. What exists (observed)

```
index.html        markup, CSS, and the game script (one inline classic <script>, a single IIFE)
src/
  geography.js    the map projection, districts, stations, lines and route finding
  util/
    format.js     number, money and time formatting: clamp, kr, hhmm, fmtDur
data/             city data, unchanged
tests/            test_geography.py and test_format.py test the modules; test_syntax.py checks every file under src/
```

| Module | Owns | Public interface (an object on `window.StockholmLife`, named after the module) | Depends on |
| --- | --- | --- | --- |
| `src/geography.js` | The projection (1 unit = 50 m, origin T-Centralen, x east, z south); the fallback water outlines; the ten districts; the 45 T-bana and tram stations; the six lines; route finding with transfer penalties; the nearest station to a point | `O_LAT`, `O_LON`, `P`, `PP`, `WATER_FALLBACK`, `AREAS`, `HUB_R`, `ST`, `STP`, `LINES`, `transitRoute`, `nearestStation` | Nothing: no DOM, no game state, no three.js, no network |
| `src/util/format.js` | `clamp`; `kr` (kronor with a space between thousands and a real minus sign); `hhmm` (a clock time from hours, wrapping at 24); `fmtDur` (a duration from minutes). The original bodies, moved unchanged | `window.StockholmLife.format`: `clamp`, `kr`, `hhmm`, `fmtDur` | Nothing: no DOM, no game state, no three.js, no network |

The game script reads each module once, at the place where the code used to be, under the names it always used (`D` stays an alias of `AREAS`; `clamp`, `kr`, `hhmm` and `fmtDur` are read at their old lines). No function, variable or save key changed name. The game script's other `hhmm` is a local variable inside a function and stays local. `dateOf`, `today`, `esc0`, `esc2` and the local `escH` stayed where they were: they are not pure or not identical, and merging them would change behaviour.

## 2. How a module works

### 2.1 Loading: classic scripts on one namespace (observed)

A module is a **classic script** in `src/`, loaded by its own `<script src>` tag after the three.js tags and before the game script:

```html
<script src="src/geography.js"></script>
<script src="src/util/format.js"></script>
<script>
(function(){
const {O_LAT, …, nearestStation}=useModule('geography');
// …later, where the code used to be:
const {clamp,kr,hhmm,fmtDur}=useModule('format','util/format.js');
```

`useModule(name, file)` takes the module's name on `window.StockholmLife` and, when the file is not `src/<name>.js`, its path under `src/`. A module in a subfolder passes it, so that a missing file is reported under its real path.

Each module wraps its code in a function with `'use strict'`. It registers one object on `window.StockholmLife`, or on `module.exports` when Node loads it for tests:

```js
(function(root){
'use strict';
// … the code …
const geography={O_LAT,O_LON,P, …};
if(typeof module==='object'&&module&&module.exports)module.exports=geography;
else (root.StockholmLife=root.StockholmLife||{}).geography=geography;
})(globalThis);
```

**Why classic scripts and not native ES modules yet.** TECHNICAL_ARCHITECTURE.md §3.1 names native ES modules as the end state, and that stays the end state. Today the game script is a classic, sloppy-mode script, and it uses the moved code as soon as it runs:

- A `<script type="module">` is deferred, so the game script could not read it synchronously.
- Turning the game script itself into a module would change all of its 5,000 lines at once. It would become strict mode, and it would run deferred. That is not a move-only change.

A classic script runs in order and keeps the game script exactly as it was. Converting later is mechanical: replace the last three lines of each module with `export`, and the game script's `useModule()` with `import`. That happens once, in its own pull request, after a strict-mode audit of the game script (§6, step 9). The inline script already parses as strict-mode syntax; whether it behaves the same at runtime under strict mode is not yet known.

### 2.2 Rules for a module (target, followed by `geography.js`)

1. **One responsibility, one object.** A module registers exactly one name on `window.StockholmLife` and nothing else on `window`.
2. **No hidden dependencies.** A module uses only:
   - its own code;
   - modules loaded before it, read through `window.StockholmLife` when it starts;
   - what it is given as arguments.

   It never reads the game script's variables (`S`, `W`, `CITY`). Those are not visible to it anyway, because they live inside the game script's function.
3. **State stays with its owner.** Data modules are read-only in practice. Nothing in the game writes to `AREAS`, `ST`, `STP` or `LINES` (checked when `geography.js` moved). The life state `S` is owned by the game script until the state module exists (§4.2).
4. **The same names.** Moved code keeps its names, comments and behaviour. A move and a change never share a pull request.
5. **Fail loudly at startup.** The game script reads every module through `useModule(name, file)`. If a module did not load (a missing file, a network failure, a syntax error), `useModule` writes *"The game could not load src/<file>…"* (the real path, e.g. `src/util/format.js`) on the loading screen and stops the script, instead of leaving a blank page.

### 2.3 Adding a module

1. Choose a section from the sequence in §6, and check that its names are not reassigned outside it. Use an AST pass: a plain text search is misleading, because many names are shadowed by local variables (`P` and `D` are reused as local arrays in `buildWorld`).
2. Copy the code verbatim into `src/<name>.js` inside the wrapper of §2.1, and list its public names in the registered object.
3. In `index.html`, replace the section with `const {…}=useModule('<name>');` (or `useModule('<name>','<folder>/<name>.js')` for a module in a subfolder, with the same path in the script tag), and add `<script src="src/<name>.js"></script>` after the modules it depends on and before the game script.
4. Write `tests/test_<name>.py` (§2.4).
5. Run `python3 tests/test_syntax.py` and the full suite (`tests/README.md`).
6. Document it here, in §1.

### 2.4 Testing a module

- **Unit tests in Node**, no browser, in seconds. The test runs `node -e` with `require('src/<name>.js')` and checks known values and properties. `tests/test_geography.py` is the pattern.
- **Characterisation, for a move.** The test hashes every output on a fixed set of inputs, and the hash is computed once against the code *before* the move. `GOLDEN` in `tests/test_geography.py` covers 1,305 projections, the data tables, 2,401 routes (every pair among the 45 stations and four names that are not stations) and 13,225 nearest-station lookups.
- **In the game.** A browser test exposes the game script's names (through the test hook, `tests/game.py`). It checks that they are the module's own objects, not copies, and that the city starts. A second test blocks the module's file and checks the startup message.
- **Syntax and publishing**, in `tests/test_syntax.py`:
  - every `.js` file under `src/`, in nested folders too, passes `node --check`;
  - every module `index.html` loads exists, and every `.js` file under `src/` is loaded (an unlisted file fails);
  - each loaded module is read with `useModule`, and the path in that call equals the path in its script tag;
  - every local script `index.html` loads is among the files the Deploy workflow publishes and `tools/live_check.py` verifies.

## 3. Publishing (observed: a blocker for merging)

The Deploy workflow (`.github/workflows/deploy.yml`, step "Collect the game files only") publishes `index.html`, `data/` and `version.txt`, nothing else. `tools/live_check.py` (`published()`, `expected_from_git()`, `expected_from_github()`) verifies the same set. Published as it is, `src/geography.js` would be missing from the site and the game would stop at startup with the message of §2.2.

`tests/test_syntax.py::test_local_scripts_are_published` fails until both are updated. The Deploy workflow runs the test workflow before it publishes, so this test also blocks a deployment, not only a merge. The change needs the owner's approval (AGENTS.md: deployment workflows), and it must be merged before or together with the first module:

- `deploy.yml`: `cp -R index.html data src _site/`, and list `_site/src` in the step's output.
- `tools/live_check.py`: `published()` also accepts `src/`; `git ls-tree` also lists `src`; the GitHub tree walk also descends into `src`.
- `tests/test_live_check.py`: the file count also lists `src`, plus cases for a `src/` file.

**Caching.** GitHub Pages caches every file for 10 minutes. For up to 10 minutes after a deployment, a visitor can therefore get a new `index.html` with an old module, or the other way round. A pure move is unaffected, because the old and new code are the same. Once a module's interface changes, `index.html` should load it with a version query (`src/<name>.js?v=<n>`), which needs no build step.

## 4. Initialisation, state and lifecycle

### 4.1 Start-up sequence (observed)

1. **HTML parse.** The CSS and the markup are read, and the loading screen is visible.
2. **three.js r128 and its add-ons**, classic scripts from cdnjs and jsdelivr.
3. **The `src/` modules**, in order. Today: `geography.js`, then `util/format.js`.
4. **The game script, top level.** The constants and tables are defined, plus about 600 functions. Five core functions are wrapped by later reassignments, so their behaviour depends on file order: `log` and `addBill`, `spendTime` and `sleep` in the phone section, and `newGame` in the origins section. No geography name is used at this stage outside a function.
5. **`start()`**, called directly, or through `window.claude.hot` when that is present:
   1. `uiInit()`;
   2. `load()` or a hot snapshot, then `migrate()`; for a new player, a default `S`;
   3. `lifeInit(S)`, `updateLoc()`, `render()`;
   4. the `pagehide` and `visibilitychange` save listeners;
   5. `loadCity()`, which fetches `data/*.json`, then `matchServices()`;
   6. `buildWorld()`, which creates the renderer, the scene, the input listeners and the `tick()` loop, and returns `W`;
   7. the loading screen is removed;
   8. the player is placed and any saved place restored (`W.restorePlace`) or the Arlanda arrival started;
   9. `intro()` for a new life;
   10. the live-data timers start: weather every 10 minutes, flights every 10 s (when a relay is set), and a chance of an incoming call every 150 s.

### 4.2 State (observed, then target)

**Observed.**

- `S` is the single authoritative life state. It is saved as JSON under `stockholm-life-v4`, at version 5. It is owned by the game script, and written directly from everywhere.
- The world keeps its own runtime state: `IN` (interiors), `CS` (station), `JR` (train), `DR` (driving), `AP` (Arlanda). The world reports into `S` through `window.__slCommit` and `window.__slDrive` and the `W` API (51 entries). The place you are in is saved through `W.placeState()` and `W.restorePlace()`.

**Target.**

- `S` keeps one owner, a future `src/state.js` (M1). It brings mutation helpers that emit events, so that the panels and the world subscribe instead of everyone calling `render()`.
- Modules never hold life state. They receive what they need as arguments, or read it through the state module's interface.
- The save format, the storage key and the migrations do not change because code moves.

### 4.3 Communication (target)

| Kind | Mechanism |
| --- | --- |
| Data and pure rules | Direct calls to a module's functions (as with `transitRoute`) |
| World ⇄ rules | The existing `W` facade, which stays; parts of `buildWorld` move behind it while it keeps its 51 entries |
| State changes | One small event emitter in the state module (`on`, `off`, `emit`), with named events such as `day`, `money` and `place`. It replaces the five reassigned functions with explicit hooks (`onNewGame`, `onDayChange`, …). Added with M1, not before |
| Live data | Each client (weather, SL, flights, news, exchange rates) behind a function returning a promise, which degrades to "unavailable" as it does today |

No framework, no build step and no dependency beyond three.js.

### 4.4 Resources, errors, assets and the frame loop

- **three.js resources.** `buildWorld` owns the renderer, the scene, the cameras and the controls. When world code moves out, a module receives a context `{THREE, scene, camera, renderer, city}` from `buildWorld`; it is not a global. A module that creates geometry, materials or textures disposes of them through the existing disposal paths (`disposeGroup`, tile clearing).
- **Errors.** A missing module stops startup with a message (§2.2). Live-data failures stay non-fatal. Moved code keeps its existing `try/catch` behaviour; its empty `catch` blocks are changed only in separate pull requests.
- **Assets.**
  - City data: `loadCity()` → `gunzipFetch('data/*.json')`, three files essential and the rest optional.
  - Models: `loadModels()`, GLB as base64 inside JSON.
  - Modules: static scripts, loaded before the game script.

  This order stays. Parsing tile data in a worker belongs to M7.
- **Update and render.**
  - `tick()` in `buildWorld` is the only `requestAnimationFrame` loop.
  - The simulation step is capped at 50 ms per frame.
  - The station and the train run inside it (`csTick`, `jrTick`/`jrRender`).
  - A world module exposes a `tick(dt)` function that `tick()` calls in a fixed order. Separating the simulation from rendering is M2/M7, not part of moving code.

## 5. Module inventory (planned, from the code)

The table maps the areas of the game to the code that implements them today; the names are those in `index.html`. "Pure" means no DOM, no `S` and no three.js, so a module can be tested in Node. The proposed modules are each a separate, approved pull request, in the order of §6. Several areas are not separate in the code. They share `S` and call each other, and they move only after the state module exists.

| Area | Code today | Depends on | State | Testable alone | Risks and cycles | Proposed modules |
| --- | --- | --- | --- | --- | --- | --- |
| A. Core lifecycle, config | `start`, `loadCity`, `matchServices`, `uiInit`, the hot-reload hooks, quality presets `QS`, `FLIGHT_RELAY_DEFAULT` | Everything | Creates `S`, `W`, `CITY` | No: the composition root | Order of start-up | Stays in `index.html` until last; then `src/main.js` |
| B. State and persistence | `S`, `newGame`/`_newGame`, `migrate`, `SAVE_KEY`, `SV`, `save`, `load`, `saveParse`, `saveLoad`, `saveKeep`, `endLife`, `placeStamp`/`placeSave`/`placeValid`, `exportLife`, `importCheck`, `importApply`, `saveHash`; `lifeInit`, `civInit`, `crimeInit`, `inboxInit`, `invInit` | localStorage, DOM (`saveMsg`), `W.placeState`, `busy` | Owns `S` | Partly: parse, migrate and import checks with storage and `W` passed in | Highest: save compatibility. Cycle: save → `W.placeState` → world → `S` | `src/state.js`, `src/save.js` (M1) |
| C. Renderer, camera, scenes, lighting | In `buildWorld`: `renderer`, `scene`, `camera`, `controls`, `QS`/`setQuality`, `hemi`/`sun`/`moon`/`sky`/`clouds`, `lightAt`/`refresh`, `resize`, `goodCamera`, `icam`, `jrCam` | THREE, `S.hour`, `S.wx` | Own runtime state | No | Every world function closes over these | `src/world/render.js`, after the context exists |
| D. World and environment | Tiles (`buildTile`, `buildingGeo`, `roadGeo`, `greenGeo`, `updateTiles`, `cullTiles`, `disposeGroup`); water and land (`waterPolys`, `inWater`); collision (`colByTile`, `colliding`, `hitPoly`, `slideMove`, `freeSpot`, `unstick`); street graph (`G`, `route`, `nearestNode`, `walkable`); furniture and signals (`buildFurniture`, `updateSignals`); `decorFor`; labels, POIs, entrances; `CITY`, `gunzipFetch`, `parseHours` | THREE, `CITY`, geography | Read-only city data plus tile caches | Geometry builders: yes, in Node with three.js and no WebGL; `parseHours`: pure | Large shared closure | `src/city-data.js`, `src/world/tiles.js`, `src/world/collision.js`, `src/world/streets.js` |
| E. Buildings, interiors, places | `buildRoom`, `enterInterior`, `exitInterior`, `IN`, `interiorTick`, `kindFor`, `spot`; Arlanda (`arlandaScene`, `AP`, `apTick`, `airportGuide`, customs `packSuitcase`, `customsCheck`, `custFinish`); Stockholm Central (`CS`, `csBuild`, `csTick`, …); opening hours (`SVC`, `svcPlace`, `OPEN`, `isOpen`); `poiActions`, `showPoi`; places bar `renderPlaces`, `goHome`, `goWork` | World context, rules, UI | Runtime state saved through `placeState` | Customs rules and opening hours: yes (data plus functions); scenes: no | Restoring a place after a reload (M1b) | `src/rules/customs.js`, `src/rules/hours.js`, then `src/places/central/*`, `src/places/arlanda/*` |
| F. Player and NPCs | Avatar `av`, `placeAvatar`, walking in `tick`, `ensureAgents`, `pedAvoid`, `modelPed`; people records `newPerson`, `relUpdate`, `maybeMeet`, `peopleDaily`, `openPerson`; station NPCs `csPeople`, `csNpcTick` | World, `S.people` | `S.people`, runtime agents | People rules: yes, if `S` is passed in | `newPerson` uses unseeded `Math.random` | `src/rules/people.js`; agents later (M5) |
| G. Appearance and animation | `LOOKS`, `SKIN`/`TOPS`/`BOTTOMS`/`HAIRS`, `randomOutfit`, `applyStyle`, `applyOutfit`, `setLook`, `tintModel`; models `MODELS`, `loadModels`, `parseModel`, `avMixer`, `avActs`, `setAvState`; `cAnim`, `sitPose`, `syncLuggage` | THREE, SkeletonUtils, `data/people.json` | `S.look` | Data tables: yes | Model loading is asynchronous | `src/data/looks.js`; `src/world/models.js` |
| H. Interactions and dialogue | `modal`/`closeModal`, `menuFor`, `runItem`, `choiceModal`, `DESK`, `agencyDesk`, `actionsMenu`, `homeMenu`, `promptFor`/`promptSet`/`promptAnswer`, `dateConversation`, `TOPICS`, `meetStranger`, `OPENERS`, chats (`CHAT_IN`, `CHAT_REPLY`, `BOT`, `openChat`), `hoverInfo` | UI, rules, `S` | Writes `S` | Text tables: yes | Rules and UI call each other | `src/data/dialogue.js`; `src/ui/modal.js` |
| I. Transport and vehicles | Rules: `openTravel`, `goWalk`, `walkTo`, `buySL`, `slTicket`, `TRIPS`, `takeTrip`, `taxiQuote`, `carActs`, `licenceActs`. Live: `slSites`, `slDepartures`, `fetchFlights`, `routeOf`, `waitTimes`. World: `TRANSIT`, `updateTransit`, `ride`, `busRide`, `carStep`, driving `DR`, `startDrive`, `driveTick`, lessons `COACH`, `coachTick`, `LIMIT`, `emergency`, `updateAir`, `updateLiveAir`, `planeMesh`. Pendeltåg: `PTT`, `ptDep`, `jrStart`, `jrTick` | Geography, world, live data, `S` | `S.tix`, `S.slUntil`, runtime vehicles | Ticket prices and timetables (`PTT`, `ptDep`): yes; the live clients, with `fetch` stubbed | `carStep` is large and tested only in the browser | `src/live/sl.js`, `src/live/flights.js`, `src/rules/tickets.js`, `src/world/traffic.js` |
| J. Housing and everyday life | `HOMES`, `openHousing`, `assignAddress`, `addrText`, `atHome`, `homelessActs`; needs (`NEED_KEYS`, `needsTick`, `feelings`); `ACTS`, `doAct`, `spendTime`, `sleep`, `lifeDaily`; shopping `ITEMS`, `shopMenu`, `groceryMenu`, `useItem`, `openBag` | `S`, UI | Writes `S` | Data tables: yes; `needsTick`, if `S` is passed in | `spendTime` and `sleep` are reassigned later (§4.1) | `src/data/homes.js`, `src/data/acts.js`, `src/rules/needs.js` |
| K. Employment and education | `JOBS`, `openJobs`, `workAct`, `gigAct`, `jobPay`, `afterShift`, `JOBPLACE`, `workPlace`, `goWork`; `COURSES`, `LEVELS`, `openCourses`, `courseAct`, `CSN4W`, SFI | `S`, opening hours, UI | Writes `S.job`, `S.pay`, `S.svenska` | `JOBS`, `COURSES`, `jobPay`: yes | Work in progress elsewhere may change this area; check open branches first | `src/data/jobs.js`, `src/rules/work.js` |
| L. Economy | `kr`, `TAX`, bills (`addBill`, `BILLSTAGE`, `billTotal`, `processBills`, `garnish`, `openBills`), banks (`BANKS`, `openBankApp`, `openBankID`, `openSwish`, `openBank`), funds (`FUNDS`, `invInit`, `invTick`, `openInvest`), `RIKSNORM`, `BARNBIDRAG`, exchange rates (`csExchange`, `FXR`), `SL_PRICE`, `TICKET`, `MUSEUM_PRICES`. There is no business system; businesses appear only in text | `S`, UI, live exchange rates | Writes `S.money`, `S.bills` | Bill stages and tax: yes, if `S` is passed in | `addBill` is reassigned later | `src/data/prices.js` (facts with their dates), `src/rules/bills.js` |
| M. Government and public services | `NODOCS`, `requestDocs`, `papers`, `skvWhere`/`skvSvc`, `agencyOf`, `takeQueue`, `QUEUE_SPEED`, `QUEUE_FEE`, `queueYears`; civic (`civInit`, `holdElection`, `castVote`, `campaign`, `holdDemo`, `joinMarch`, `fileJO`); justice (`CRIMES`, `crimeAttempt`, `sentence`, `deported`, `SENTENCING`); care (`open112`, `careOpen`, `careNeed`, `call1177`, `AKUT`, `hospitalStay`); `openKivra`; `BG` documents | `S`, UI, `endLife` | Writes `S.docs`, `S.civ`, `S.crime` | Election maths (`pollShares`, `seatsFor`) and sentencing: yes | `deported` → `endLife` (saving) | `src/rules/civic.js`, `src/rules/justice.js`, `src/data/agencies.js` |
| N. Animals and horses | None: no system exists. Dogs and cats appear only in text ("walking a dog") and as goods in the customs rules | — | — | — | — | None until there is a feature (rule 2.2: no empty modules) |
| O. UI and smartphone | `TAB`, `setTab`, `render`, `renderNeeds`, `nextSteps`, `renderGuide`, `renderCivic`, `renderAbout`, `renderTodo`, `renderPlaces`, `renderSOS`, `toast`, `PHONE_APPS`, `notify`, `badges`, `openMailbox`, `openChats`, `openTodo`, `openCalls`, `callScreen`, `incomingCall`, `openNews`, `intro`, `$`, `esc0`/`esc2`/`escH` | DOM, `S`, rules | Reads `S` | Helpers (`kr`, `hhmm`, `fmtDur`, `esc*`): yes | Panels are rebuilt with `innerHTML`; rules call `render()` | `src/util/format.js` first; `src/ui/*` after the state events exist |
| P. Weather, audio, environment | Weather `LIVEWX`, `WMO`, `fetchLiveWeather`, `applyLiveWeather`, `rollWeather`, `TEMP`, `winter`, `dressAdvice`, `wearTip`, `openWeather`; sun (`sunInfo`, `daylight`, `sunrise`, `sunset`, `isLight`, `RAD`, `LAT`); world `lightAt`, `refresh`, `snowyNow`, `season`, `aurora`; audio `AUD`, `audInit`, `audSet`, `tone`, `sfx`, `say`, `audToggle` (station only) | Open-Meteo, `S.wx`, THREE | `S.weather`, `S.temp`, `S.wx` | Sun maths and WMO codes: yes; the weather client, with `fetch` stubbed | `applyLiveWeather` writes `S` | `src/rules/sun.js`, `src/live/weather.js`, `src/world/audio.js` |
| Q. Progression and activities | `goals`, `check`, `WANTS`, `rollWants`, `checkWants`, `ASPIRATIONS`, `aspirationDone`, `EVENTS`, `pickEvent`, `showEvent`, `nextSteps`, the to-do list (`todoRoll`, `TODO_RULES`, `suggestFor`, `planAdvice`), the Arlanda guide (`AP_STEP`), `csGuideMenu`, `museumVisit`, `socialAct`. There is no mission system yet (M4) | `S`, UI | Writes `S.wants`, `S.flags` | Tables: yes | `EVENTS` is extended after its definition (`EVENTS.push`) | `src/data/events.js`; missions with M4 |
| Cross-cutting: time | `spendTime`, `sleep`, `dateOf`, `today`, `hhmm`, `csClk`/`csFlush`; time advances with distance walked (`__slCommit`) | `S` | `S.day`, `S.hour` | `dateOf`, `today`: yes | M2 changes the model | `src/state/clock.js` (M2) |

## 6. Extraction sequence (target)

Foundations first; one module per pull request; each pull request is a move only, with the full suite green and no change to the save. The first three steps need nothing beyond this document.

| Step | Module | Why here | Gate |
| --- | --- | --- | --- |
| 0 | Publishing `src/` (§3) | Without it no module can go live | Owner approval of the workflow change |
| 1 | `src/geography.js` | **Done** (the first move). Pure, used throughout the game script and the world, never written outside its section | Step 0 |
| 2 | `src/util/format.js`: `clamp`, `kr`, `hhmm`, `fmtDur` | **Done** (the second move). Pure helpers used everywhere; makes the later rules modules testable. `esc0`/`esc2`/`escH` (they differ in how they treat `null`) and `pickA` (not checked) did not move | Step 1 |
| 3 | `src/rules/sun.js`: `sunInfo`, `daylight`, `sunrise`, `sunset`, `isLight`, WMO tables | Pure maths, tested against published sun times | — |
| 4 | `src/city-data.js`: `gunzipFetch`, `parseHours` | Small, loads assets, testable with stubbed `fetch` | — |
| 5 | Data tables: `JOBS`, `HOMES`, `ACTS`, `COURSES`, `ITEMS`, `COUNTRIES`, prices (with their dates) | Data only; check each for functions that close over `S` first | After step 2 |
| 6 | Live-data clients: weather, SL, flights, news, exchange rates | Each degrades on its own; `fetch` can be stubbed | After step 2 |
| 7 | `src/state.js` and `src/save.js` (M1) | Owner of `S`, events, explicit hooks instead of the five reassigned functions | M1 spec approved |
| 8 | Rules modules (needs, work, bills, civic, justice, customs, people) | Need `S` passed in or the state module | After step 7 |
| 9 | Strict-mode audit of the game script, then native ES modules (`type="module"`, `import`/`export`) | The documented end state (TECHNICAL_ARCHITECTURE.md §3.1) | Audit and owner approval |
| 10 | World parts behind the `W` facade: context, tiles, collision, traffic, transit, interiors, Stockholm Central, the pendeltåg ride | Largest and most interconnected; needs the context of §4.4 | After step 9; M4 to M7 |
| 11 | `src/main.js`; `index.html` reduced to markup plus loading | Last | After step 10 |

Until step 7, a module never touches `S`: steps 2 to 6 move only code that does not read or write it, or that receives it as an argument.
