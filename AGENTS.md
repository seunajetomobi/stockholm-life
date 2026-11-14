# Stockholm Life — shared instructions for AI coding agents

Stockholm Life is a browser game: `index.html` holds CSS, HTML and the game script (three.js r128 from CDN); code moved out of it lives in `src/` as classic scripts loaded before the game script ([`docs/MODULES.md`](docs/MODULES.md)).
Run with `./start.sh` and open http://localhost:8000. There is no build step and no package.json. How to run the tests: [`tests/README.md`](tests/README.md).

These instructions apply to every agent working in this repository. Agent-specific notes live in that agent's own file (for Claude Code, `CLAUDE.md`, which imports this file).

## Roles

| Who | Role |
| --- | --- |
| The user | Project owner. Final authority over merging, deployment, destructive or irreversible operations, architecture and product decisions |
| ChatGPT | Independent project coordinator and reviewer: prepares tasks, reviews diffs, test results and reports, and keeps the queue and status honest. It works through the user and the repository; it has no direct connection to the agents |
| Claude Code | Implementation agent: inspects, implements, tests, commits, pushes feature branches, opens pull requests and reports |
| Codex | Optional. May implement or review when the user chooses; no workflow depends on it |

A report of success is not proof. Reviewers check the actual code, Git history, CI runs and behaviour.

## Where things are

| What | Where |
| --- | --- |
| Current status (main and live commits, open pull requests, milestone, verification results) | [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md), the single authoritative status |
| Current task and upcoming tasks | [`.agent/QUEUE.md`](.agent/QUEUE.md), the single queue; there is no separate current-task file |
| Task specifications, when a queue entry needs more than a few lines | `.agent/tasks/<task-id>.md` |
| Reports worth keeping | `.agent/reports/<date>-<task-id>.md` |
| Technical decisions | [`docs/TECHNICAL_ARCHITECTURE.md`](docs/TECHNICAL_ARCHITECTURE.md) §5 |
| Vision, roadmap, features, issues, tests | [`docs/PRODUCT_VISION.md`](docs/PRODUCT_VISION.md), [`docs/MASTER_ROADMAP.md`](docs/MASTER_ROADMAP.md), [`docs/FEATURE_INVENTORY.md`](docs/FEATURE_INVENTORY.md), [`docs/KNOWN_ISSUES.md`](docs/KNOWN_ISSUES.md), [`docs/TEST_PLAN.md`](docs/TEST_PLAN.md) |

Folders under `.agent/` exist only when they hold a file. `.agent/archive/` is for maintained material that is no longer current; private or historical material that should not be public stays outside the repository.

**The repository is public.** Never commit credentials, tokens, private configuration, local machine paths or details, personal information, or unreviewed internal handoffs and assessments.

## Working rules

1. **Inspect first.** Check the Git state (`git status`, branch, recent commits, worktrees) and the real GitHub state (pull requests, checks, `main`, the live `version.txt`) before working. Never assume a pull request was merged or deployed; verify it.
2. **Preserve the user's work.** Never reset, clean, stash, discard, overwrite or delete uncommitted or untracked work, local branches, worktrees or backups. Do not switch or pull in the user's checkout; build changes in a separate worktree from the latest `origin/main`.
3. **One feature branch per task**, small and reviewable; no unrelated changes. Follow the existing architecture and the code around you; do not rewrite without a documented, approved reason.
4. **Push only the named branch with an explicit refspec** (`git push -u origin <branch>:refs/heads/<branch>`). Never force-push or rewrite pushed history.
5. **Test every meaningful change:** syntax checks and the full browser suite (`tests/README.md`), plus a regression test that fails without the fix where possible. Prefer condition-based waits to fixed sleeps.
6. **Review your own diff** before committing: accidental deletions, unrelated changes, secrets and private information.
7. **Report honestly.** Report the actual results, including failures, flaky runs and steps skipped. Do not mark a milestone or feature complete without evidence. Keep `docs/PROJECT_STATUS.md` and `.agent/QUEUE.md` accurate when a task changes them.
8. **Facts in the game** (fees, prices, rules) come from real sources and carry the date they were checked.

## Approval boundaries

The user must explicitly approve each of these. Approval covers only the action, pull request or commit it names; it does not carry over to the next one.

- Merging any pull request (merge commit pinned to the approved head SHA with `--match-head-commit`; if the head changes, ask again).
- Deploying the game, or changing deployment workflows, environments, branch protection, rulesets, Actions or repository settings.
- Destructive or irreversible operations: deleting files, branches, worktrees or backups; force-pushing; rewriting history.
- Cleaning up or synchronising the user's local checkout, branches or worktrees.
- Major architectural changes and important product decisions.
- Publishing anything outside the repository, or making private material public.

If a task needs to cross one of these boundaries, stop and ask.

## Report format

Every task ends with a report (in the pull request description, or to the user when there is no pull request) containing:

- Task ID, agent, date
- Starting commit and final commit (exact SHAs)
- Branch and pull request, with merge and deployment status
- Files changed
- Implementation summary
- Tests run and their actual results (local and CI, with run IDs)
- Known problems and limitations
- Outstanding work
- Recommended next action and any decisions needed from the user

# Code map

## Map of index.html (search for these names)

- Game state: global `S` (needs, money, docs, people, bills, flags…). `newGame()`, `save()` (localStorage `stockholm-life-v4`), `render()` (panels).
- Rules: `ACTS`, `BG` (backgrounds), `JOBS`, `HOMES`, `sleep()` (day change), `spendTime()`, `addBill()` + `processBills()` (reminder → inkasso → Kronofogden).
- Phone apps: `PHONE_APPS`, `openChats`, `openMailbox`, `openTodo`, `openBag`, `notify`.
- Origins and start screen: `intro()`, `COUNTRIES`, `routesFrom()`, `applyOrigin()`, `airportSpot()`.
- Arlanda arrival: `buildRoom('arlanda')`, guide card `airportGuide`/`airportNext`, belt 4 with your suitcase `apTick`/`apTake` (state `AP`), signs `apSign`, arrivals screen `apArrivals`. Customs from Tullverket's rules: `packSuitcase()` (`S.suitcase`, from `depCountry()`), `customsCheck()`, `customsChannel('green'|'red'|'blue')`, the declaration form and `custFinish()` (tax by card, fines as bills), `custRules()`.
- Live data (needs internet; all degrade gracefully offline):
  - Weather: `LIVEWX`, `fetchLiveWeather()` (Open-Meteo, every 10 min), `applyLiveWeather()`, `dressAdvice()`, `wearTip()`, `openWeather()`. Sky, clouds, rain/snow density, wind and fog in `lightAt()`/`refresh()` read `S.wx`.
  - SL departures: `slSites()` (all stop areas, cached a week in localStorage), `slDepartures()`, `openDepartures()`, `departuresNear()`, `openDeparturesApp()`, `openFerries()`, `slLineCol()`.
  - Flights: `FLIGHT_RELAY_DEFAULT` / `?flights=<url>`, `fetchFlights()`, `LIVEFL`, `openFlights()`, `flightDetail()`; routes from adsbdb.com via `routeOf()`. The relay is `tools/flights-worker.js` (Cloudflare Worker).
  - Arlanda security queues: `waitTimes()`, `openSecurity()` and the Security line in `flightDetail()`, from Swedavia's WaitTime API through the relay's `/waittime` (the relay needs the Worker secret `SWEDAVIA_KEY`; without it the game says queue times are unavailable).
- Phone and care: `PHONE_APPS` (icons `txt:` render brand letters), `openCalls`/`callPerson`/`incomingCall`, `open112`, `careOpen`/`careNeed`/`call1177`, `openKivra`, `openBankID`, `openSwish`, `openBankApp`, `openSLApp`, `openRailApp`, `openAlltidOppet`, `openNews` (Ekot direct; SVT/DN/Aftonbladet/Expressen through the relay's `/news`), `renderSOS()` (112 button and care chip).
- Driving practice: `startLesson('lesson'|'test')`, `coachTick` (limits in `LIMIT` by road class, wrong way, keep right, red light, pedestrians), `finishLesson`.
- Safe crossing: `crossSafe`, walk pause in `tick()` (`walk.blocked`), pedestrians in `pedAvoid`. Demonstrations: `demoTick`, `DEMO_PLACES`. Sponsors: `SPONSORS` (billboard ads). Identity: `applyStyle` (headwear, beard, glasses), `syncLuggage`. Arlanda guide: `airportGuide`/`airportNext`.
- Your places bar: `renderPlaces()`, `goHome`, `goWork`/`workPlace`, `goFamily`, `goFriends`/`friendHome`, `openInvest`/`invTick` (ISK funds). `openTravel(k, dest)` travels to a district or any point.
- Crime and accidents: `crimeAttempt`, `doCrime`, `sentence`, `accidentHappened`, `hospitalStay`.
- Stockholm Central and the pendeltåg ride (inside `buildWorld`, search "Stockholm Central Station, Stockholm City"): state `CS` (`mode` null/'station'/'ride'), station clock `csClk()` (game minutes, 4× real time, flushed into `S.hour` by `csFlush`). Station scene built in metres by `csBuild()` from Jernhusen's floor plans (Centralhallen main level, Nedre hallen): floors `R(id,name,x0,x1,z0,z1,y,h)` grouped by level id ('hall', 'lower', 'slhall', 'plat'), walls from `walls()` with door `gap()`s, storefronts `shop()`, blockers (`csWhere`, `csHit`); Stockholm City platform offset by `PX`/`PZ` under Vasagatan; doors in `CS_DOORS` (Huvudentré, Vasagatan norra, Centralplan into Nedre hallen, Cityterminalen); `csEsc`, `csElev`, gates (`csGateIn`/`csGatePass`, no passage without `csTicket()`), `x60Ext` trains placed from the timetable (`PTT`, `ptDep`, `ptAt`, `ptDoor`; long-distance board `MLT`/`mlDeps`). One prompt at a time: `promptFor`/`promptSet` (also outside at the Vasagatan doors, `csOutside`). Menus: `csTicketMachine` (tickets in `S.tix`), `csBuses` (SL stop letters round Stockholm C), `csUpper` (Övre hallen, not built), `csExchange` (`S.fx`, live ECB rates from frankfurter.dev or labelled simulated), `csInfo`, `csGuideMenu`/`CSG`. Ride: `jrStart` → `jrTick`/`jrRender` (X60 interior scene `jrScene` drawn over the city through the windows; tunnel shell `tunSec` and underground stations `ugStation` from the route's real tunnel spans), stops `jrArrive`/`jrDepart`, skips `jrSkipNext`/`jrSkipStop`, tunnel-exit cinematic `jrCineStart`/`jrCineEnd`, getting off `jrAlight`. Facade over the OSM building: `csFacade`. Places bar button "Centralen" → `goCentral()`.
- 3D world: `buildWorld()` returns the `W` API. Inside: tiles (`buildTile`, `buildingGeo`, `roadGeo`), collision (`colByTile`, `colliding`, `onCarriageway`, `slideMove`, `freeSpot`, `unstick`), routing (`route`), agents (`ensureAgents`, `carStep`: lights, lanes, give way, högerregeln, never drive into the vehicle ahead), transit (`TRANSIT`, `updateTransit`, `ride`, `busRide`), interiors (`enterInterior`, `buildRoom`), driving (`DR`), Arlanda cutscene (`playLanding`), emergency vehicles (`emergency`, city 112 calls in `cityCalls`/`spawnIncident`), helicopters (`updateAir`: ambulance, police with searchlight, sea rescue), live aircraft (`updateLiveAir`, `planeMesh`, `LIVERY`), tunnel portals (`buildPortals`, `tunDepth`), station signs (`updateEntrances`), pedestrian personal space (`pedAvoid`), camera (`goodCamera`, third-person pull-in in `tick`), hover info (`hoverInfo`), the main loop `tick()`.

## Coordinates and data

- 1 world unit = 50 m. Origin = T-Centralen (59.3313 N, 18.0603 E). x = east, z = south. `P(lat, lon)` converts. Districts (`AREAS`, alias `D`), stations (`ST`, `STP`), lines (`LINES`), `transitRoute` and `nearestStation` are in `src/geography.js`.
- Tiles are 10 units (500 m), keyed "i,j". Integer coordinates in the JSON files are units × 100.
- `data/e.json` (T-bana entrances and rail/tram stations with their SL lines and colours) is built by `tools/osm_stations.py` from two Overpass exports.
- `data/o.json` (one-way directions + lane counts per street edge, from OpenStreetMap tags) is built by `tools/osm_lanes.py` from an Overpass export; vehicles use it in `mayEnter`, `nextEdge`, `lanesOf` and `agentEdge`.
- Road classes 0–14: motorway, motorway_link, trunk, trunk_link, primary, primary_link, secondary, tertiary, unclassified, residential, living_street, pedestrian, service, cycleway, footway. Edge flags: 1 bridge, 2 tunnel, 4 no walking.

Known issues, with their evidence and suggested fixes, are in [`docs/KNOWN_ISSUES.md`](docs/KNOWN_ISSUES.md).
