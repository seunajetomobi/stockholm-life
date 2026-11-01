# Technical architecture

How Stockholm Life is built today, its known weaknesses, and the target architecture. Replaces the audit's `ARCHITECTURE.md` (never committed). Measured on `main` at `40d913e`. Sections are marked **Observed** (from the code, test runs and the GitHub API) or **Target** (agreed direction).

## 1. Current architecture (observed)

### Stack

| Item | Value |
| --- | --- |
| Language | Plain JavaScript (ES2020+), HTML and CSS; no build step, no `package.json` |
| Rendering | three.js **r128** from cdnjs and jsdelivr, with the `examples/js` add-ons OrbitControls, GLTFLoader, SkeletonUtils, BufferGeometryUtils, SimplifyModifier |
| Hosting | GitHub Pages, published by the "Deploy to GitHub Pages" workflow (see §4) |
| Backend | One optional Cloudflare Worker (`tools/flights-worker.js`) relaying flights, news feeds and Swedavia wait times |
| External services | Open-Meteo, SL Transport, adsbdb.com, Sveriges Radio, frankfurter.dev, the relay |
| Tests | Python: pytest + Playwright with Chromium (`tests/`) |

### Files

| Path | Size | Role |
| --- | --- | --- |
| `index.html` | 820,778 bytes, 5,316 lines | Everything: CSS, markup and one inline script (about 4,860 lines) |
| `data/b.json`, `r.json`, `m.json`, `t.json` | 7.3, 8.1, 3.2, 2.1 MB | Buildings in 1,101 tiles; street graph; green areas, water, POIs; transit routes |
| `data/x.json`, `o.json`, `e.json` | 0.4 MB | Signals, one-way and lanes, station entrances |
| `data/people.json`, `vehicles.json`, `trees.json` | 14.7 MB | GLB models as base64 inside JSON |
| `tools/osm_lanes.py`, `tools/osm_stations.py` | | Build `o.json` and `e.json` from Overpass exports (inputs not in the repo) |
| `tools/flights-worker.js` | | The relay |
| `.github/workflows/tests.yml`, `deploy.yml` | | CI tests and the manual deployment |
| `tests/` | | Browser and syntax tests (see TEST_PLAN.md) |

The generators for `b`, `r`, `m`, `t` and the model files are not in the repository.

### Code structure inside `index.html`

One IIFE with 608 named functions. Approximate layers in file order:

| Lines | Layer | Contents |
| --- | --- | --- |
| ~457–1250 | Rules and life simulation | Areas, `JOBS` (14), `HOMES` (10), `BG` (3), `ACTS` (57), needs, people and relationships, dating, courses, shops, civic system; `newGame`, `migrate`, `save`/`load`, `spendTime`, work |
| ~1250–1920 | Travel and phone | Travel cards, crime, live SL data, flights, places bar, invest, calls, care, banks, news, mail, chats, to-do, bag (`ITEMS`: 8) |
| ~1920–2360 | Onboarding and day cycle | Origins, Arlanda customs, bills, `sleep` (day change, payday, rent), events, `goals`, `render` |
| 2360–5284 | `buildWorld()` | The whole 3D world as one closure: renderer, tiles, collision, routing, ambient agents, transit, interiors, Arlanda, driving, emergencies, aircraft, input, camera, main loop `tick()`; Stockholm Central and the pendeltåg ride (about lines 4378–5284) including the train camera (`jrCam`, `jrArm`, `jrBlockers`, `jrOcclude`) |
| 5285–5316 | Boot | `loadCity`, `start` |

### State and data flow

- `S` is one plain object holding the whole life, saved as JSON under one localStorage key (`stockholm-life-v4`); `migrate()` upgrades older saves. About 46 `save()` calls are spread through action handlers.
- The rules layer reads and writes `S` directly from everywhere; `render()` rebuilds panels with `innerHTML` (54 assignments).
- The 3D world keeps its own state (`IN` interiors, `CS` station, `JR` train ride, `DR` driving) and reports back through `window.__slCommit`, `window.__slDrive` and the returned `W` API. This world state is **not saved**.
- **Time** advances with distance walked (`__slCommit`), driving and actions (`spendTime`), not on its own; standing still stops time. The station runs a separate clock (`csClk`), merged back with `csFlush`.
- Five core functions are reassigned later in the file (`newGame`, `sleep`, `spendTime`, `addBill`, `log`), so their behaviour depends on script order. Some names are also reused for unrelated local helpers (`person`, `spot`, `walkTo`).
- 36 empty `catch(e){}` blocks; about 225 unseeded `Math.random()` calls.

### Rendering and world loading

- All city JSON (about 12 MB compressed, 37 MB raw) is fetched and parsed on the main thread at start and kept in memory (194 MB JS heap measured after boot).
- Geometry is built per 500 m tile around the player, with culling and disposal; repeated objects use instancing and merged geometry.
- Renderer: antialiasing, logarithmic depth buffer, soft shadows on "Rich", pixel ratio up to 2; Fast/Rich presets (`QS`) with automatic switch to Fast on slow GPUs.
- The simulation step is capped at 50 ms per frame, so below 20 fps the city runs slower than real time.

## 2. Strengths and weaknesses (observed)

**Strengths:** real, consistent geography (1 unit = 50 m, origin T-Centralen); a large set of working, interconnected Swedish-life rules; graceful fallback for every live feed; small saves that migrate; tile streaming and quality presets; no build step.

**Weaknesses, in order of impact on the roadmap:**

1. **Persistence:** one slot, silent failures, unsaved world state (M1).
2. **Time tied to movement:** blocks schedules and opening-hours gameplay (M2).
3. **Monolith:** one 820 kB file with a 2,924-line closure; no module boundaries (M3).
4. **Global mutable state** without owner, events or validation (M1, M3).
5. **Monkey-patched core functions** and silent error handling (M3).
6. **Simulation driven by the render loop** (M2, M7).
7. **Start-up cost and phone GPU cost**, never measured on real devices (M7).
8. **Data pipeline not reproducible** for the main data files; models stored as base64 (M7).
9. **Old dependency:** three.js r128 with `examples/js` add-ons, loaded without Subresource Integrity.

## 3. Target architecture

Principle: **evolve, don't rewrite.** Keep three.js and static hosting; move code before changing it; every move guarded by the test suite.

### 3.1 Modules without a build step (M3)

```
index.html            markup + <script type="module" src="src/main.js">
styles/game.css
src/
  main.js             boot
  state/  state.js (S, mutation helpers, events), save.js (envelope, slots, migrations), clock.js
  rules/  needs, jobs, housing, bills, people, civic, crime, docs
  ui/     panels (render), modal, phone/*, intro, hud
  live/   weather, sl, flights, news, fx
  world/  world.js (facade returning W), tiles, collision, routing, agents, transit, interiors/*, driving, air, camera, input
  places/ central/*, arlanda/*
  data/   JOBS, HOMES, BG, ACTS, ITEMS, COUNTRIES, ...
```

### 3.2 State, time and saving (M1, M2)

- One owner for `S`, with mutation helpers (`addMoney`, `advanceTime`, `setDoc`) emitting events; UI and world subscribe instead of calling `render()` everywhere.
- Explicit hooks instead of reassigned functions (`onNewGame`, `onDayChange`).
- Save envelope `{v, savedAt, S, world: {place, interior, vehicle, station, train}}`, ordered migrations, slots, export/import, `pagehide` saving, visible errors.
- A game clock owned by `clock.js`; the world reads it instead of driving it.

### 3.3 World (M4–M7)

- `buildWorld()` stays the facade returning `W`; its parts move into modules sharing a context (scene, camera, city data, state accessor).
- A **Place** abstraction (`city`, `interior:<id>`, `station`, `train`, `airport`) with `enter`, `exit`, `tick` and `serialize`, so every scene saves and restores the same way.
- Interior definitions as data (rooms, doors, spots, NPC slots); the station's metre-based builder (`csBuild`) is the model.
- NPC registry simulated as records, embodied near the player (M5).
- Fixed-timestep simulation separate from rendering; per-tile data parsed in a worker (M7).

### 3.4 Multiplayer readiness (M8)

State changes as recordable actions, seeded randomness and the explicit clock make a deterministic, replayable core possible later. No networking is planned.

## 4. Release and quality infrastructure (observed)

| Element | Configuration |
| --- | --- |
| Pull-request tests | `.github/workflows/tests.yml` on `pull_request` to `main`: jobs `tests-syntax` and `tests-browser` (Playwright's pinned Chromium 145.0.7632.6, version-checked) |
| Branch protection | Ruleset "Protect main": pull request required, required checks `tests-syntax` and `tests-browser` from GitHub Actions (integration 15368), branches up to date, no force pushes or deletion, no bypass |
| Deployment | `.github/workflows/deploy.yml`, manual (`workflow_dispatch`) from `main`: resolves the requested ref to one commit already on `main`, runs the tests on it, checks the game files, publishes `index.html`, `data/` and a generated `version.txt`, then polls `version.txt` for up to 11 minutes |
| Approval | Environment `github-pages`: reviewer approval required, deployments from `main` only, no administrator bypass |
| Pages source | GitHub Actions (since 2026-10-31); pushes to `main` do not publish |
| Actions security | GitHub-owned actions only, full-SHA pinning required, approval for all external contributors' workflows, read-only default token |
| Rollback | Run the Deploy workflow with an earlier commit from `main` |

## 5. Decisions

| Date | Decision |
| --- | --- |
| 2026-10-31 | Keep three.js r128 and no-build static hosting for now |
| 2026-10-31 | Publish via GitHub Actions with a manual, approval-gated deployment of an exact commit |
| 2026-10-31 | Evolve the existing code; no rewrite |
| 2026-11-01 | Foundations (M1 save/state, M2 time) before new gameplay |
