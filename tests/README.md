# Stockholm Life tests

Automated checks for the game, preserved from the 2026-10-31 audit and the two fixes after it (pendeltåg camera `df54793`, M14 `742403b`). They test the game as it is; they do not change it. There is no build step: the tests are Python scripts that drive headless Chrome against a local copy of the game.

## What is here

| File | What it checks | Browser | Test hook |
| --- | --- | --- | --- |
| `test_syntax.py` | `node --check` on the inline `<script>` of `index.html` and on `tools/flights-worker.js` (as an ES module); the Python tools compile | No | No |
| `test_smoke.py` | Desktop 1366×768: city loads, WebGL canvas, no game file fails to load, character creation shown; "Go" starts a life and writes a save; each dock tab renders; every phone app opens without an uncaught error (at least 39 tiles); every places-bar button responds, Centralen opens its travel card | Yes | No |
| `test_save.py` | Reload restores name, day, hour, money and position; a corrupted save starts a fresh life without errors; an old `stockholm-life-v3` save migrates (HUD 10:00, 1 200 kr, v4 written) | Yes | No |
| `test_layout.py` | 390×844 and 520×900 (touch) and 1366×768: no horizontal overflow on the intro or while playing; dock, joystick, Run, zoom and places bar inside the viewport | Yes | No |
| `test_m14.py` | M14 regression at the same three sizes: in the station, boarding (with the "Sit down?" prompt), a three-line prompt (phones), seated. The message strip is at most 60 px tall; on phones it overlaps none of the ride HUD, prompt, joystick, Run, zoom or dock; on desktop it is still centred near the top. The strip never covers any visible control (ride HUD, prompt, top bar, Next up, places bar, zoom, joystick, Run, dock…), even by part of a pixel: two- and three-line messages in the station, boarding (prompt open, also three lines tall) and seated (prompt closed), at 360×640, 375×667, 390×844, 520, 601, 640 and 768 px wide, landscape 640×360, 844×390 and 1024×768, and four desktop sizes; where nothing is in the way the desktop strip keeps its place. Explicit regression: the Home button at 768×1024. Where no place is free (a three-line message at 640×360) the strip may share space only beneath a control, which stays on top and takes the tap | Yes | Yes |
| `test_traincam.py` | Pendeltåg camera regression: every tested seat (60) × 24 yaws × 3 pitches and 17 standing spots × 24 yaws keep the camera inside the car and out of posts, poles and cab walls; seated default is "You" with the avatar visible; "Eyes" puts the camera exactly where it was before `df54793`; standing resets pitch; the camera stays below the gangway header; walking along the aisle with W (real key presses) moves you and the camera follows, inside the car with you on screen; getting off restores the city camera; at 390×844 the ride HUD fits in three rows with the short "🧍 You" label | Yes | Yes |
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
```

**Local server.** The tests use a server already running on port 8000 (for example `./start.sh`) if it serves this repo's `index.html`, and otherwise start `python3 -m http.server 8000 --bind 127.0.0.1` themselves and stop it afterwards. If port 8000 serves a different `index.html` (another checkout, an edited copy), the run stops with a message rather than testing the wrong code. Another port can be set with `SL_PORT=8123`, but the flights relay only allows port 8000, so live flights will show CORS errors there (they do not fail the tests).

**Output.** Screenshots go to `tests/output/` (ignored by git), named after the test and screen width, e.g. `layout-390.png`.

**Speed.** Each browser test loads the whole city (about 12 MB of data) and the software renderer runs at 1–2 fps, so a full run takes a while. Frame rates measured here say nothing about real hardware.

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
