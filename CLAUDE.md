# Notes for Claude Code

Stockholm Life is a single-file browser game: `index.html` holds CSS, HTML and all JavaScript (three.js r128 from CDN).
Run with `./start.sh` and open http://localhost:8000. There is no build step and no package.json.

## Map of index.html (search for these names)

- Game state: global `S` (needs, money, docs, people, bills, flags…). `newGame()`, `save()` (localStorage `stockholm-life-v4`), `render()` (panels).
- Rules: `ACTS`, `BG` (backgrounds), `JOBS`, `HOMES`, `sleep()` (day change), `spendTime()`, `addBill()` + `processBills()` (reminder → inkasso → Kronofogden).
- Phone apps: `PHONE_APPS`, `openChats`, `openMailbox`, `openTodo`, `openBag`, `notify`.
- Origins and start screen: `intro()`, `COUNTRIES`, `routesFrom()`, `applyOrigin()`, `airportSpot()`.
- Crime and accidents: `crimeAttempt`, `doCrime`, `sentence`, `accidentHappened`, `hospitalStay`.
- 3D world: `buildWorld()` returns the `W` API. Inside: tiles (`buildTile`, `buildingGeo`, `roadGeo`), collision (`colByTile`, `colliding`, `onCarriageway`, `slideMove`, `freeSpot`, `unstick`), routing (`route`), agents (`ensureAgents`, `carStep`: lights, lanes, give way, högerregeln, never drive into the vehicle ahead), transit (`TRANSIT`, `updateTransit`, `ride`, `busRide`), interiors (`enterInterior`, `buildRoom`), driving (`DR`), Arlanda cutscene (`playLanding`), emergency vehicles (`emergency`), hover info (`hoverInfo`), the main loop `tick()`.

## Coordinates and data

- 1 world unit = 50 m. Origin = T-Centralen (59.3313 N, 18.0603 E). x = east, z = south. `P(lat, lon)` converts.
- Tiles are 10 units (500 m), keyed "i,j". Integer coordinates in the JSON files are units × 100.
- `data/o.json` (one-way directions + lane counts per street edge, from OpenStreetMap tags) is built by `tools/osm_lanes.py` from an Overpass export; vehicles use it in `mayEnter`, `nextEdge`, `lanesOf` and `agentEdge`.
- Road classes 0–14: motorway, motorway_link, trunk, trunk_link, primary, primary_link, secondary, tertiary, unclassified, residential, living_street, pedestrian, service, cycleway, footway. Edge flags: 1 bridge, 2 tunnel, 4 no walking.

## Known issues to work on

- About 0.5% of auto-walk time still passes through building footprints (narrow passages in Gamla stan).
- Performance drops at high detail on weak GPUs; the "Fast" quality setting reduces tiles and trees.
- Facts in the game (fees, prices, rules) were checked in October 2026 and may change.
