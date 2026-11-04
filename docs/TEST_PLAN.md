# Test plan

Current as of 2026-11-04, `main` at `492a8e5`, with the save tests as on branch `feat/m1-save-safety` (not merged). How the game is tested today, what is not covered, and what each roadmap milestone must add. First written in the audit of 2026-10-31. How to install and run the tests: [`tests/README.md`](../tests/README.md).

## 1. The automated suite (observed)

Python, pytest and Playwright driving headless Chromium with software WebGL (SwiftShader) against `python3 -m http.server 8000`. No `package.json`, bundler, linter or type-checker.

| File | Tests | What it checks |
| --- | --- | --- |
| `test_syntax.py` | 3 | `node --check` on the inline script and on `tools/flights-worker.js`; the Python tools compile |
| `test_smoke.py` | 9 | City loads, WebGL canvas, game files load, character creation; starting a life writes a save; 5 dock tabs render; all 39 phone apps open without errors; every places-bar button responds |
| `test_save.py` | 2 | Reload restores the life; a v3 save migrates |
| `test_save_safety.py` | 47 | M1a: failed saves are reported once and recovery is reported; unreadable saves are kept before anything replaces them; the placeholder and ended lives are never written; deportation and restart; closing and hiding the tab (hidden tab and back/forward cache simulated); no save while busy or in a driving lesson; court cases survive until sentenced, once; a stale tab that can see a newer save stops instead of overwriting it. Uses fault injection on `localStorage` |
| `test_layout.py` | 3 | 390×844, 520×900, 1366×768: no horizontal overflow, controls inside the screen |
| `test_m14.py` | 8 | Station/train message strip. At 390, 520 and 1366 px: at most 60 px tall, clear of the HUD, prompt and controls on phones, centred on desktop. From PR #4: the strip stays on screen and covers no visible control (ride HUD, prompt, top bar, "Next up", places bar, zoom, joystick, Run, dock), even by part of a pixel; the only overlap allowed is the no-room fallback, with the strip beneath the control, at 360×640, 375×667, 390×844, 520, 601, 640 and 768 px wide, 640×360, 844×390, 1024×768 and four desktop sizes; in the station, boarding (prompt open, also three lines tall) and seated; with two- and three-line messages. An explicit 768×1024 Home-button regression test; the no-room fallback at 640×360 with a three-line message (the strip beneath Run, which stays visible on top and takes taps; the strip has `pointer-events: none`); desktop keeps its place where nothing is in the way. From PR #6: the strip follows layout changes between the game's frames (the top bar growing, which moves the ride HUD through `--boardH`; the HUD growing; a resize) at 360×640 with the periodic HUD update held (KNOWN_ISSUES M17); layouts are measured once they have stayed the same for three rendered frames, not after a fixed time |
| `test_live_check.py` | 139 (22 with a browser) | `tools/live_check.py`: verdict rules and the CDN confirmation window; expected files from local Git and a simulated GitHub API (with tree truncation, rate limits, refused commits); exact comparison by Git blob ID including gzip; the Deploy workflow's data rules and a check that they still match `deploy.yml`; redirects checked hop by hop; DNS pinning; Chromium's resolver rules; route interception of the page and every same-origin file; game defect vs CDN inconsistency vs missing dependency vs no WebGL vs timeout vs interception failure vs a game error during an outside-service outage; the warning on a PASS from a single round; safe output paths; a run leaves the repository unchanged. Loopback servers and generated sites only; runs offline |
| `test_traincam.py` | 7 | Pendeltåg camera: inside the car and clear of blockers at 60 seats × 24 yaws × 3 pitches and 17 standing spots; "You" and "Eyes" views; standing up; gangway; walking with W while the camera follows; getting off; the 390 px ride HUD; one `xfail` for L10 |

**Test hook.** The station and train are reached through a test-only copy of `index.html`: Playwright serves it to the test browser with `window.__T` added at the end of `buildWorld`. The real `index.html` and the published site never contain it. Details in `tests/README.md`.

**In CI.** `.github/workflows/tests.yml` runs on every pull request to `main`. Jobs `tests-syntax` and `tests-browser` are **required checks** (GitHub Actions, integration 15368). The browser job installs the Chromium build pinned by Playwright 1.58.0 (145.0.7632.6) and fails if any other browser would be used. The Deploy workflow runs the same tests on the exact commit it publishes (browser tests can be skipped only for an urgent rollback or a commit from before the tests existed).

**Latest results.** Branch `feat/m1-save-safety`, based on `492a8e5`, run locally on 2026-11-04 with system Chrome, before a final correction to two comments (CI results are on the pull request): 218 tests (79 for the game, 139 for `tools/live_check.py`), 217 passed, 1 xpassed (L10) in 58 minutes. Negative control on `492a8e5`: 40 of the 47 new tests fail. Seven pass there because they record behaviour that was already right or a known limit. Earlier, 172 tests (33 for the game, 139 for `tools/live_check.py`). PR #8 CI on `7931618` (run `41387669915`): 171 passed, 1 xfailed (L10) in about 30 minutes; locally the same in 31 minutes, and `test_live_check.py` alone passed offline (139). Of three local full runs, one had an intermittent failure in `test_m14.py::test_strip_avoids_controls_phone_tablet` that passed alone and in the other two (details not captured). Earlier, on `4ff1aa4`: 159 tests, 158 passed, 1 xfailed; before that, 33 tests. PR #6 CI on `77bf136` (run `41285465844`): 32 passed, 1 xfailed (L10) in about 28 minutes; locally twice, 32 passed and 1 xpassed or xfailed. The new layout-change test fails on `main` `3d04635` (negative control) and passes with the fix. Earlier: PR #4 CI on `081682f` (run `41269872906`), 31 passed and 1 xpassed; its four new M14 tests failed on the earlier PR #4 commit `adc765d`.

**Live verification.** After every deployment the workflow polls `version.txt` for the deployed commit. `tools/live_check.py` (how to use it: `tests/README.md`, "Live check") checks more, read-only: every published file against the commit by Git blob ID, repeated over the 10-minute CDN cache window before a difference counts as confirmed; the data files with the Deploy workflow's rules; the game starting in headless Chromium with every same-origin file verified as served; the deployment record as evidence. Its own tests are `test_live_check.py` (loopback servers only, no internet). It is run by hand: before a deployment against the live commit, and after it against the deployed one. It is not part of a workflow.

## 2. History: what the audit ran (2026-10-31, `870fe30`)

`node --check` on the inline script and the relay; `py_compile` on the tools; a headless smoke run (0 page errors; city loaded in 10–13 s; 39 phone apps opened; reload, corrupted save and v3 migration behaved as above; no overflow at 390×844); live probes of GitHub Pages and the relay (the relay lacks `/waittime`, KNOWN_ISSUES M1; 11.9 MB downloaded). Walking with W for 3 s at 1.7 fps moved 0.28 m, consistent with the 50 ms step cap. These checks are now part of the suite above.

## 3. Known gaps

### 3.1 Not covered by automated tests

- Rules: day change, rent, salary and tax, bills escalation, jobs and promotion, housing queue, courses, crime, health (no unit tests at all).
- The other origins (newcomer via Arlanda, elsewhere in Sweden); Arlanda arrivals and customs.
- Entering interiors; walking into Stockholm Central, tickets and gates; a full pendeltåg ride between stations, tunnels, the tunnel-exit cinematic and getting off at a real stop.
- Driving, lessons and the driving test; transit rides; emergencies; elections; audio.
- Offline behaviour of the live features.
- Frame rate, feel and touch input on real devices. One frame-rate comparison ran once, outside this suite, on one laptop (§6).

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
| M0 | Real-device checks in §4 recorded; `tools/live_check.py --expect <deployed SHA> --rounds 4 --interval 300` passes after deploying `main` |
| M1 Save and state | `node --test` unit tests for the save envelope and every migration (v3 → v4 → v5); browser tests that save and reload in each place type; full and blocked storage shows an error; a corrupted save is kept |
| M2 Game-time model | Unit tests for the clock, need drain, day change (rent on the 1st, salary on the 25th, bills); a browser test that time passes while standing still; station and city clocks agree |
| M3 Modules | The full suite green after every move; unit tests for each moved rules module |
| M4 First week | Unit tests for the mission step machine, shift scoring and the money ledger; browser tests driving the week through the test hook with time skips, checking mission and save state each day |
| M5 NPCs | NPC position at fixed game times; relationship changes from encounters |
| M6 | Tests per new job, building or mission, following the M4 pattern |
| M7 Performance | Per release on real devices, Fast and Rich, at Odenplan and Sergels torg: ≥ 30 fps Rich and ≥ 45 fps Fast on an Intel UHD 620 laptop; ≥ 30 fps Fast on a mid-range Android phone and an iPhone with no reload from memory pressure in 10 minutes; time to playable < 15 s on 50 Mbit/s; JS heap < 500 MB. A debug overlay (`?debug=1`) shows fps, draw calls, triangles, heap and loaded tiles |
| M8 | Replay and determinism tests from a seed and an event log |

## 6. Seated-train frame-rate comparison (2026-11-03)

An M15 comparison, **not an M7 performance test**: M7's targets (§5) apply to other scenes and to more devices, and M7 asks for ≥ 45 fps on Fast where this comparison used M15's 30 fps minimum. It ran once, outside the automated suite, on one laptop. It says nothing about other devices.

**Status: the comparison is complete; M15 overall is not** (KNOWN_ISSUES M15, M18). The authoritative report is `three-arm-2026-11-03/combined-22-sessions/RESULTS.md`. That report, the raw data and the test scripts are private, held by the project owner outside this repository, so public readers cannot check them.

**Design.** A = `870fe30`, first-person seated camera. B = `3ac8b53`, Eyes view. C = `3ac8b53`, You view, the default. Rich and Fast, three valid runs each. Each session was a fresh browser on line J43, in the same seat, with three 20-second scenes: at the platform, in the tunnel, and above ground. Headed Chrome 156 on Intel UHD 620 integrated graphics, page 2048×974, on mains power. Rich and Fast were held by a preset, so the game's automatic switch to Fast could not occur.

**Sessions.** All 18 required results exist: three valid sessions for each of the 6 arm and setting combinations. 22 sessions ran. Four were disturbed; they are preserved and excluded from every comparison, and each was replaced by one approved repeat:

| Invalid session | Arm, setting | Why | Replaced by |
| --- | --- | --- | --- |
| s02 | B, Rich | Tunnel and above ground ran at 1 fps; the page shape changed | r02 |
| s03 | C, Rich | The camera moved before the tunnel scene | r03 |
| s04 | C, Fast | Stood up, changed seat, "Next stop" used | r04 |
| s07 | B, Rich | The character stood up during the above-ground scene | r07 |

### Measured

Typical fps per run, with the lowest 1-second window across the three runs in brackets.

| Setting | Scene | A | B | C |
| --- | --- | --- | --- | --- |
| Rich | Platform | 12, 13, 13 (12) | 13, 16, 13 (12) | 13, 13, 13 (12) |
| Rich | Tunnel | 11, 13, 13 (10) | 12, 15.5, 12 (11) | 12.5, 12, 13 (11) |
| Rich | Above ground | 11, 19, 19 (9) | 18.5, 23, 19 (14) | 16, 15, 16 (12) |
| Fast | Platform | 23, 24, 25 (17) | 23, 24, 24 (21) | 22, 22, 22 (17) |
| Fast | Tunnel | 23, 23.5, 24 (21) | 22, 24, 24 (16) | 22, 21, 21.5 (19) |
| Fast | Above ground | 31, 34, 33 (24) | 31, 33, 33 (27) | 28, 28, 28 (23) |

Each arm's lowest 1-second window is below 30 fps in every scene (9–27 fps). In one single run, s16 (B, Fast, above ground), the lowest window stayed at 31. Typical fps is above 30 only on Fast above ground in arms A and B.

Median draw calls and triangles, from a separate 3-second sample:

| Setting | Scene | A | B | C |
| --- | --- | --- | --- | --- |
| Rich | Platform | 1352 / 2.03 M | 1377 / 1.99 M | 1410 / 2.13 M |
| Rich | Tunnel | 246 / 0.23 M | 227 / 0.21 M | 284 / 0.23 M |
| Rich | Above ground | 901 / 2.05 M | 935 / 2.03 M | 1567 / 2.06 M |
| Fast | Platform | 879 / 1.01 M | 873 / 1.00 M | 973 / 1.07 M |
| Fast | Tunnel | 139 / 0.14 M | 137 / 0.13 M | 183 / 0.14 M |
| Fast | Above ground | 518 / 0.94 M | 529 / 0.94 M | 1059 / 0.97 M |

Comparisons use the agreed thresholds. Real difference: median difference over 2 fps, with every run of one arm on the same side of every run of the other. No meaningful difference: median difference of 1 fps or less, with overlapping runs. Anything else is inconclusive. Figures are the second arm's median minus the first's.

| Setting | Scene | A vs B (same camera) | B vs C (camera) | A vs C (player experience) |
| --- | --- | --- | --- | --- |
| Fast | Platform | No meaningful difference (0) | Inconclusive (−2) | Inconclusive (−2) |
| Fast | Tunnel | No meaningful difference (+0.5) | Inconclusive (−2.5) | Inconclusive (−2) |
| Fast | Above ground | No meaningful difference (0) | **Real difference** (−5) | **Real difference** (−5) |
| Rich | Platform | No meaningful difference (0) | No meaningful difference (0) | No meaningful difference (0) |
| Rich | Tunnel | No meaningful difference (−1) | No meaningful difference (+0.5) | No meaningful difference (−0.5) |
| Rich | Above ground | No meaningful difference (0) | **Real difference** (−3) | Inconclusive (−3) |

### Inconclusive

- **Fast, platform and tunnel, B vs C and A vs C.** The differences are about 2 fps. Three of the four are exactly 2, which is not over the threshold; B vs C in the tunnel is −2.5, but its runs overlap at 22.
- **Rich, above ground, A vs C (−3).** s01's reading of 11 falls below all of C's runs (15–16), while A's other two runs (19) are above them.

### Interpretation (not measurement)

- With the same camera, no meaningful slowdown was detected between `870fe30` and `3ac8b53` on this laptop, in the tested scenes, on either setting. This does not show the same on other devices.
- Above ground, the You camera is slower than Eyes: about 5 fps on Fast and 3 fps on Rich. Its draw calls are about 1.7–2× Eyes' with about the same triangles. That is consistent with additional rendering cost but does not prove the cause.
- Choosing a camera does not bring the seated train up to the 30 fps minimum, since the first-person arms also dip below it.

### Readings kept in

Both passed every check, so they stay in the results above.

- **s01 (A, Rich):** the slowest run. Above ground: lowest window 9, typical 11, 45 frames over 100 ms, against 19 in A's other two runs. Without it, as a check only, Rich above ground A vs C becomes a real difference (−3).
- **r02 (B, Rich):** the fastest Rich run. Typical 16 on the platform, 15.5 in the tunnel and 23 above ground, against 13, 12 and about 19 in B's other two runs. It was the first session after the laptop had been idle, and it recorded higher clock speeds and temperatures than the next sessions. GPU clock was not recorded, so the cause is not established. Without it, no verdict changes.
- **Without both:** Rich tunnel A vs B also becomes inconclusive (−1).

### Limitations

- **Repeats:** they ran about 5½ hours after the other 18, so they are not interleaved with the other arms. Their order was fixed (B Rich, B Rich, C Rich, C Fast), not rotated with A.
- **Weather differed slightly between the two runs:** the game uses live weather. Repeats: 2.9 °C, 6–13 % cloud. First run: 3.5–3.8 °C, 5–7 % cloud. Clear with no precipitation in both. The game clock started at 08:00 in all sessions.
- **Disturbances:** the four invalid sessions look like real clicks, keys or window changes; who or what caused them is not known.
- **Checks:** they read the state at each scene's start and end, plus once-a-second state changes, so a brief disturbance that undid itself could go unseen.
- **Script:** the first attempt was stopped for a script bug and is not counted. The running script took C's camera reference from disturbed s03, so all sessions were rechecked afterwards against the validated preflight references.
- **Setup:** simulated input and a test-only hook, not a person playing. The train was held at the platform and moved above ground by shortcut, the same in every arm. Passengers are random.
- **Scenes:** in the tunnel the frame rate jumps for about the last 5 of 20 seconds, once the city stops being drawn; figures from before the jump give the same verdicts. The tunnel's draw sample covers only the deep part.
- **Scale:** one machine with a low-end GPU and three runs per cell. Refresh-rate steps can blur small differences.

### Proposed future work (not approved or started)

- Investigate the You camera's above-ground cost.
- Repeat the comparison on a stronger GPU.
- Run the frame-cap-off test, which was deliberately not run.
- Check r02's reading again with GPU clock recorded.
