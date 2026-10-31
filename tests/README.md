# Stockholm Life tests

Automated checks for the game, preserved from the 2026-10-31 audit. They test the game as it is; they do not change it. There is no build step: the tests are Python scripts that drive headless Chrome against a local copy of the game.

## What is here

| File | What it checks | Browser | Test hook |
| --- | --- | --- | --- |
| `test_syntax.py` | `node --check` on the inline `<script>` of `index.html` and on `tools/flights-worker.js` (as an ES module); the Python tools compile | No | No |
| `test_smoke.py` | Desktop 1366×768: city loads, WebGL canvas, no game file fails to load, character creation shown; "Go" starts a life and writes a save; each dock tab renders; every phone app opens without an uncaught error (at least 39 tiles); every places-bar button responds, Centralen opens its travel card | Yes | No |
| `test_save.py` | Reload restores name, day, hour, money and position; a corrupted save starts a fresh life without errors; an old `stockholm-life-v3` save migrates (HUD 10:00, 1 200 kr, v4 written) | Yes | No |
| `test_layout.py` | 390×844 and 520×900 (touch) and 1366×768: no horizontal overflow on the intro or while playing; dock, joystick, Run, zoom and places bar inside the viewport | Yes | No |
| `game.py`, `conftest.py` | Shared helpers: local server, browser, test hook, page set-up, measurements | | |

Every browser test fails on an uncaught JavaScript error (`pageerror`). Console errors and failed requests to external services (weather, SL, flights, news) are recorded but do not fail a test, because those services can be offline. A failed request for the game's own files does fail `test_smoke.py`.

The station and train regression tests (`test_m14.py`, `test_traincam.py`) are added together with the camera and M14 changes they check.

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
python3 -m pytest tests/test_save.py    # one file
python3 -m pytest tests -k 390          # only the 390 px cases
python3 -m pytest tests -s              # also print load times and recorded console errors
```

**Local server.** The tests use a server already running on port 8000 (for example `./start.sh`) if it serves this repo's `index.html`, and otherwise start `python3 -m http.server 8000 --bind 127.0.0.1` themselves and stop it afterwards. If port 8000 serves a different `index.html` (another checkout, an edited copy), the run stops with a message rather than testing the wrong code. Another port can be set with `SL_PORT=8123`, but the flights relay only allows port 8000, so live flights will show CORS errors there (they do not fail the tests).

**Output.** Screenshots go to `tests/output/` (ignored by git), named after the test and screen width, e.g. `layout-390.png`.

**Speed.** Each browser test loads the whole city (about 12 MB of data) and the software renderer runs at 1–2 fps, so a full run takes a while. Frame rates measured here say nothing about real hardware.

## The test hook

The station, the train and the cameras live inside the `buildWorld()` closure, and walking to Stockholm Central at 1–2 fps would take far too long. The `hook` tests (`test_m14.py`, `test_traincam.py`, added with the camera and M14 changes) therefore use a **test-only copy** of `index.html`:

1. `game.hooked_html()` reads `index.html` from disk and replaces the closure's last statement, `return API;`, with `window.__T={csEnter, jrStart, jrSit, …, get CS(){…}, get JR(){…}};return API;` (the full list is `HOOK_NAMES` and `HOOK_LIVE` in `game.py`).
2. Playwright's `context.route('**/index.html', …)` serves that copy to the test browser only. Data files come unchanged from the local server.
3. The tests then call the game's own functions through `window.__T` (for example `__T.csEnter(__T.CS_DOORS[0])` to go inside Central, `__T.jrStart(...)` to board).

The file on disk, the local server's copy and the published game are never changed, so normal play cannot see the hook. If `return API;` disappears or appears twice, the tests stop with an explicit message; if a hooked name is renamed, the page throws a `ReferenceError` naming it at boot. Update `HOOK_NAMES` when that happens.

To run the hooked tests on another version of the game, point `SL_INDEX_HTML` at a saved copy (for example `git show <rev>:index.html > /tmp/old.html`).

Because the hook jumps straight into the station and the train, a hooked test shows that the code works once you are there. It does not show that a player can walk there, buy a ticket or pass the gates.

## Still manual

These need a real GPU, a real phone or a long run, and are listed in `docs/TEST_PLAN.md` §4:

- Frame rate and feel on desktop and phones; touch joystick; touch-drag camera rotation.
- Pendeltåg camera on real hardware (several seats both ways, a full turn by mouse and touch, Eyes and back, stand up, gangway, phone HUD readability).
- A real pendeltåg journey: departing, a tunnel and the tunnel-exit cinematic, arriving, getting off at a real stop (the automated test uses a shortcut), the place label afterwards.
- Walking into Stockholm Central, tickets, gates.
- The M14 strip on a real iPhone (safe-area insets) and Android phone, and in a 601–640 px window.
- Offline behaviour (TEST_PLAN.md §3.2 item 7) is not automated yet.
- Everything else in TEST_PLAN.md §2 "Not tested": interiors, Arlanda, driving, transit rides, day change, bills, crime, emergencies, elections, audio, the other origins.
