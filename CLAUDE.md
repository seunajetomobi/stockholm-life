# Notes for Claude Code

Stockholm Life is a single-file browser game: `index.html` holds CSS, HTML and all JavaScript (three.js r128 from CDN).
Run with `./start.sh` and open http://localhost:8000. There is no build step and no package.json.

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

- 1 world unit = 50 m. Origin = T-Centralen (59.3313 N, 18.0603 E). x = east, z = south. `P(lat, lon)` converts.
- Tiles are 10 units (500 m), keyed "i,j". Integer coordinates in the JSON files are units × 100.
- `data/e.json` (T-bana entrances and rail/tram stations with their SL lines and colours) is built by `tools/osm_stations.py` from two Overpass exports.
- `data/o.json` (one-way directions + lane counts per street edge, from OpenStreetMap tags) is built by `tools/osm_lanes.py` from an Overpass export; vehicles use it in `mayEnter`, `nextEdge`, `lanesOf` and `agentEdge`.
- Road classes 0–14: motorway, motorway_link, trunk, trunk_link, primary, primary_link, secondary, tertiary, unclassified, residential, living_street, pedestrian, service, cycleway, footway. Edge flags: 1 bridge, 2 tunnel, 4 no walking.

## Known issues to work on

- About 0.5% of auto-walk time still passes through building footprints (narrow passages in Gamla stan).
- Performance drops at high detail on weak GPUs; the "Fast" quality setting reduces tiles and trees.
- Facts in the game (fees, prices, rules) were checked in October 2026 and may change.
- Stockholm City is drawn 26 m below the street (35–44 m in reality) with one island platform; its track numbers (spår 1 south, spår 2 north) are the game's choice, not verified. The station interior is a simplified model of the real layout, not a survey.
