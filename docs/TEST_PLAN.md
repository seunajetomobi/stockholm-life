# Test plan

Current as of 2026-11-01, `main` at `3d04635`. How the game is tested today, what is not covered, and what each roadmap milestone must add. First written in the audit of 2026-10-31. How to install and run the tests: [`tests/README.md`](../tests/README.md).

## 1. The automated suite (observed)

Python, pytest and Playwright driving headless Chromium with software WebGL (SwiftShader) against `python3 -m http.server 8000`. No `package.json`, bundler, linter or type-checker.

| File | Tests | What it checks |
| --- | --- | --- |
| `test_syntax.py` | 3 | `node --check` on the inline script and on `tools/flights-worker.js`; the Python tools compile |
| `test_smoke.py` | 9 | City loads, WebGL canvas, game files load, character creation; starting a life writes a save; 5 dock tabs render; all 39 phone apps open without errors; every places-bar button responds |
| `test_save.py` | 3 | Reload restores the life; a corrupted save starts fresh; a v3 save migrates |
| `test_layout.py` | 3 | 390×844, 520×900, 1366×768: no horizontal overflow, controls inside the screen |
| `test_m14.py` | 7 | Station/train message strip. At 390, 520 and 1366 px: at most 60 px tall, clear of the HUD, prompt and controls on phones, centred on desktop. From PR #4: the strip stays on screen and covers no visible control (ride HUD, prompt, top bar, "Next up", places bar, zoom, joystick, Run, dock), even by part of a pixel; the only overlap allowed is the no-room fallback, with the strip beneath the control, at 360×640, 375×667, 390×844, 520, 601, 640 and 768 px wide, 640×360, 844×390, 1024×768 and four desktop sizes; in the station, boarding (prompt open, also three lines tall) and seated; with two- and three-line messages. An explicit 768×1024 Home-button regression test; the no-room fallback at 640×360 with a three-line message (the strip beneath Run, which stays visible on top and takes taps; the strip has `pointer-events: none`); desktop keeps its place where nothing is in the way |
| `test_traincam.py` | 7 | Pendeltåg camera: inside the car and clear of blockers at 60 seats × 24 yaws × 3 pitches and 17 standing spots; "You" and "Eyes" views; standing up; gangway; walking with W while the camera follows; getting off; the 390 px ride HUD; one `xfail` for L10 |

**Test hook.** The station and train are reached through a test-only copy of `index.html`: Playwright serves it to the test browser with `window.__T` added at the end of `buildWorld`. The real `index.html` and the published site never contain it. Details in `tests/README.md`.

**In CI.** `.github/workflows/tests.yml` runs on every pull request to `main`. Jobs `tests-syntax` and `tests-browser` are **required checks** (GitHub Actions, integration 15368). The browser job installs the Chromium build pinned by Playwright 1.58.0 (145.0.7632.6) and fails if any other browser would be used. The Deploy workflow runs the same tests on the exact commit it publishes (browser tests can be skipped only for an urgent rollback or a commit from before the tests existed).

**Latest results.** 32 tests. PR #4 CI on `081682f` (run `41269872906`): 31 passed, 1 xpassed (L10) in about 14 minutes; the same locally. The four new M14 tests failed on the earlier PR #4 commit `adc765d` (negative control) and pass on `081682f`.

**Live verification.** After every deployment the workflow polls `version.txt` for the deployed commit. Deeper live checks (file hashes against the commit, deployment identity from the API, browser startup, repeated over 17 minutes) were run with a script kept outside the repository (`live_check.py`); adding it to `tools/` is part of M0.

## 2. History: what the audit ran (2026-10-31, `870fe30`)

`node --check` on the inline script and the relay; `py_compile` on the tools; a headless smoke run (0 page errors; city loaded in 10–13 s; 39 phone apps opened; reload, corrupted save and v3 migration behaved as above; no overflow at 390×844); live probes of GitHub Pages and the relay (the relay lacks `/waittime`, KNOWN_ISSUES M1; 11.9 MB downloaded). Walking with W for 3 s at 1.7 fps moved 0.28 m, consistent with the 50 ms step cap. These checks are now part of the suite above.

## 3. Known gaps

### 3.1 Not covered by automated tests

- Rules: day change, rent, salary and tax, bills escalation, jobs and promotion, housing queue, courses, crime, health (no unit tests at all).
- The other origins (newcomer via Arlanda, elsewhere in Sweden); Arlanda arrivals and customs.
- Entering interiors; walking into Stockholm Central, tickets and gates; a full pendeltåg ride between stations, tunnels, the tunnel-exit cinematic and getting off at a real stop.
- Driving, lessons and the driving test; transit rides; emergencies; elections; audio.
- Offline behaviour of the live features.
- Frame rate, feel and touch input on real devices.

### 3.2 Weak spots in existing tests

- The camera sweep would also pass if the camera stopped moving at a valid position: it checks bounds and avatar visibility, not that the camera orbits or keeps your head on screen. Partly covered by the walking and "Eyes" tests.
- The gangway test only checks the camera's height and side limits.
- The "Eyes" test repeats the old camera formula, so a deliberate change to the eyes view needs the test updated.
- The L10 test is an `xfail` that may pass, so it neither catches L10 getting worse nor confirms a fix.
- The camera tests have no negative control: they cannot run against the code before the camera change.
- The M14 layout tests compare rectangles and stacking order in headless Chromium with an emulated touch screen; they do not judge readability, real safe-area insets or whether the strip covers the character's head. Overlaps between two controls (KNOWN_ISSUES L14) are not tested.

## 4. Manual checks (per release, on real devices)

- Walk with keyboard and joystick for 2 minutes in Gamla stan: never inside a building; camera never stuck behind walls.
- Tap-to-walk across Norrmalm; time and energy change as shown on the travel card.
- Enter and leave each interior kind; actions inside cost the stated time and money.
- Arrive from abroad: belt 4, suitcase, customs (green, red, blue), leave by train, bus and taxi.
- Stockholm Central: buy a ticket, pass the gates, ride the pendeltåg one stop, get off; the place label then names the street (L10).
- **Pendeltåg camera, on a desktop with a real GPU and on a real phone (outstanding, M15):** window, middle and aisle seats both ways; a full turn by mouse and by touch; "Eyes" and back; stand up and walk to the gangway; a tunnel portal with cinematics on and off; arrive and get off; the HUD readable on the phone; acceptable frame rate.
- **Message strip on a real iPhone (safe-area insets), an Android phone and a tablet, portrait and landscape (outstanding, M15):** a short bar that covers no control (beneath them only where no free place exists, controls still tappable), readable with a prompt open, not covering the character's head; also a 601–640 px window.
- Driving lesson and driving test.
- A full in-game week: rent, salary, bills, events, sleep.
- Save inside each place, reload, check where you are.
- Every phone app on a real phone, in portrait.

## 5. Tests each milestone must add

| Milestone | Required tests |
| --- | --- |
| M0 | Real-device checks in §4 recorded; live verification after deploying `main` |
| M1 Save and state | `node --test` unit tests for the save envelope and every migration (v3 → v4 → v5); browser tests that save and reload in each place type; full and blocked storage shows an error; a corrupted save is kept |
| M2 Game-time model | Unit tests for the clock, need drain, day change (rent on the 1st, salary on the 25th, bills); a browser test that time passes while standing still; station and city clocks agree |
| M3 Modules | The full suite green after every move; unit tests for each moved rules module |
| M4 First week | Unit tests for the mission step machine, shift scoring and the money ledger; browser tests driving the week through the test hook with time skips, checking mission and save state each day |
| M5 NPCs | NPC position at fixed game times; relationship changes from encounters |
| M6 | Tests per new job, building or mission, following the M4 pattern |
| M7 Performance | Per release on real devices, Fast and Rich, at Odenplan and Sergels torg: ≥ 30 fps Rich and ≥ 45 fps Fast on an Intel UHD 620 laptop; ≥ 30 fps Fast on a mid-range Android phone and an iPhone with no reload from memory pressure in 10 minutes; time to playable < 15 s on 50 Mbit/s; JS heap < 500 MB. A debug overlay (`?debug=1`) shows fps, draw calls, triangles, heap and loaded tiles |
| M8 | Replay and determinism tests from a seed and an event log |
