# Components plan

How every part of Stockholm Life becomes a component: the target files, the order of the moves, the conflicts with open work, the hazards and the first three slices. It extends [MODULES.md](MODULES.md) (which stays as history; §6 is superseded by the sequence here) and follows [TECHNICAL_ARCHITECTURE.md](TECHNICAL_ARCHITECTURE.md) §3.

**Status: approved by the owner on 2026-11-27 (decisions D1 to D9, all as recommended). Nothing in this plan is implemented yet;** the state of each slice is in [`.agent/QUEUE.md`](../.agent/QUEUE.md).

Written by the architect agent on 2026-11-26 from a read-only review of `main` `6e6e9a3`; nothing was run. **All line numbers refer to `main` `6e6e9a3`** (`main` has since moved, to `a0cb0ea` after PR #62) and shift with every merge; search by name when you move code. The lead verified the three `pickR` bugs (§4, item 5); the other measurements are the architect's and were not re-run.

## Measured on main 6e6e9a3
- index.html: 6,345 lines, 975,686 bytes. CSS 31–651 (621 lines, 83 kB); markup 653–709; game script 729–6342 (5,614 lines).
- `buildWorld`: 2787–5922 (3,136 lines, 476 kB).
- The 12 existing modules hold 1,189 lines.

## Recommendation (option A, approved as D1)
- Keep the approach MODULES.md already approved: classic scripts on `window.StockholmLife` now, native ES modules in one late pull request, **no build step**.
- This takes about 49 move-only pull requests, or about 30 if moves are bundled per area (D6).
- Two changes to the existing plan:
  1. **Add guard rails first:** a scope checker and a move checker, strict mode, and folding the reassigned functions. The scope check already found three live bugs (§4.5).
  2. **Move Stockholm Central and the train ride early.** They are 834 lines (13 % of the file) and narrow: 41 imported names, 25 exported, and one shared variable written (`walk`). Nothing open touches lines 4963–5796.

Rejected options:
- **B, big ES-module pull requests now:** they would have to untangle 5 reassigned functions, 28 shared variables and a closure of 786 names in diffs too large to review.
- **C, a bundler:** it breaks the test hook, `live_check`'s blob-ID check and Cloudflare's no-build serving, and it adds npm.

## 1. Target, about 80 files
**What a component is:** one file with one job, registered on `window.StockholmLife` (later, one ES module). Evaluating it does nothing; any setup goes in `init()`, called at the old line. There are four kinds:
- **Pure:** data, rules, formatting, fetchers. Tested in Node.
- **Game:** gets `S` from `src/state/state.js`. `S` has 1,842 reads and only 4 writes, so the moved bodies stay verbatim.
- **World:** `install(ctx)`, called inside `buildWorld()` in the original order.
- **Style:** CSS files, linked in the original cascade order.

The static markup (653–709) stays in index.html: it is the first paint, it carries the SEO, and test_name.py reads it.

| Component | ~Lines | Owns (main's lines) |
| --- | --- | --- |
| index.html, the shell | 170 | head and SEO 1–30, markup 653–709, the script list |
| src/styles/ base, title, panels, phone, responsive | 620 | 31–651, cut at its own comments (59, 125, 325, 445, 568) |
| src/main.js | 60 | start() 6317–6341, loadCity and matchServices 5927–5936, timers |
| src/state/ state, save, timesync | 315 | S, busy, `$`, today… (1262–1287, 1318–1327); migrate 1342; saves, slots, place, export and import 1351–1558; syncServerTime, syncClock, realDate 1268–1279 |
| src/data/ looks, prices, backgrounds, acts, text | 330 | LOOKS…HAIRS (870–881, 1329); TAX, SL_PRICE, TICKET, QUEUE_*, RIKSNORM (748, 870); NODOCS, BG (784–792, 2304); ACTS (803–868); TXT, TIPS (5946–6029); CHANGELOG |
| src/rules/ needs, acts, people, work, home, money, justice, civic, day, goals, customs, origins, travel | 850 | needs 881–889 and 1598–1600; acts 751–777 and 1602–1649; people 902–953 and 1798–1816; work 954–984 and 2677–2702; home 893–901, 992–1000 and 2703–2719; money 781–783, 2018–2031 and 2551–2594; justice 1729–1797; civic 1067–1161; day 2595–2676; goals 985–991 and 2720–2743; customs 2397–2497; origins 2289–2313 and 2366–2396; travel 1162–1173, 1651–1728 and 1976–2035 |
| src/live/ weather, sl, flights, news, fx | 150 | fetch and parse parts of 1288–1317, 1852–1915, 1916–1975 and 2142–2144; the csExchange rates |
| src/ui/ shell, icons, panels, place-menus, save-slots, intro | 480 | 1174–1195, modal 2744, icons 1817–1851, render 2747–2782, 1196–1260, 2498–2521, 2036–2041, 1001–1066, 2522–2550, 1560–1597, intro 2314–2365 |
| src/ui/phone/ | 420 | PHONE_APPS 1184–1193; 2153–2205; 2206–2240; 2241–2260; 2261–2274; 2275–2288; 2042–2152; 915–946; 970–979 |
| src/ui/title/ | 400 | 5937–6316 |
| src/world/world.js | 300 | renderer, scene and quality 2787–2816; shared state 4719–4725; resize, fps and tick 5797–5895; placeState and restorePlace 5896–5915; the W API, 61 entries (5916–5921) |
| src/world/ env, streets, tiles, furniture, landmarks, entrances, ads | 770 | 2817–2871, 4726–4734, 4815–4873; 2872–2931; 2932–3105; 3106–3135, 3199–3241, 3444–3482; 3606–3631, 3975–4023, 4131–4135, 4735–4738; 4024–4124, 4600–4631; 3355–3388 |
| src/world/ traffic, transit, emergency, air, avatar, input, driving, demos | 930 | 3242–3354 and 4632–4718; 3136–3198, 3389–3443, 3563–3598 and 4568–4599; 3483–3562; 3830–3974; 4874–4962; 3599–3659 and 4739–4814; 4481–4534; 4535–4567 |
| src/world/places/ interiors, arlanda/*, central/* | 1,350 | 4136–4157; 3660–3829 and 4158–4480; 4963–5796 |


## 2. Sequence
Each pull request only moves code and must pass the full CI suite. The move check, `tools/modcheck.js`, proves that the moved file's tokens equal the original region's, apart from a declared list of renames, and that the region is gone from index.html.

| PR | What | After | Effort, risk | Extra proof |
| --- | --- | --- | --- | --- |
| G1 | Guard rails: modcheck scope, move and strict; tests/sources.py | D3 | S–M, low | its own unit tests |
| G2 | `'use strict'` for the game script | G1 | S, low–med | the same swallowed errors on main and on the branch |
| G3 | Fold `log`, `spendTime`, `addBill` and `sleep` wrappers | G1 | S, med | test_life_hooks.py, test_time_rules.py |
| B1 | Fix the three `pickR` calls (a bug fix) | – | XS, low | regression tests that fail on main |
| G4 | Test hook across several files | #62, #66 and #67 merged | S, med | every hooked test gives the same verdict |
| G5 | Fold the `newGame` wrapper (2396) | r2 merged, G1 | XS, med | save fixtures, new-life tests |
| U1 | CSS to src/styles/ | ui-v2 and #63 merged | S, low | the joined files byte-equal 31–651; layout, m14 and loading-flash tests |
| D1–D3 | Data tables | G1 (`TXT` after #62) | S, low | move check; hashes pinned before the move |
| L1–L3 | Live fetchers; flights after #67 | G1 | S, low | Node tests with fetch stubbed |
| S1 | state.js; `busy` becomes `STATE.busy` (37 places) | G3, G5, D5 | M, med | move check with the rename; save fixtures |
| S2 | save.js | S1 | M, high | 13 save-fixture tests; negative_controls 8 of 8 |
| R1–R13 | Rules modules | S1 | S, low–med | move check; test_time_rules |
| UI1–UI8 | UI modules | S1 and their blockers | S–M, low–med | smoke, layout, m14, title_page, menu_extras |
| W0 | World context and forwarders | G4, #66 | M, med | move check; scene fingerprint |
| W1 | Stockholm Central and the ride | W0 | L, med | prompt, traincam, m14 and save_place tests; frame times |
| W2 | Arlanda | W0 | L, med–high | arrival_hall and landing tests |
| W3–W9 | Air, avatar, driving, demos, emergency, transit, traffic, city, environment, input | W0 | M; high for traffic and city | scene fingerprint; frame times; lane, transit and boat tests |
| W10 | src/world/world.js | W1–W9 | M, med | suite |
| E1 | Native ES modules with modulepreload | all the above, G2 | M, med | first-load measurement |
| E2 | src/main.js; index.html becomes the shell | E1 | S, low | suite |

**Running in parallel.** After G1, the data, live and Central work can be written at the same time. Each lane uses its own comment anchor in the `<script src>` list (716–727). Merges stay serial, because the strict up-to-date rule re-runs CI after every merge.

**How the test hook survives:**
- A function that moves out of `buildWorld` leaves a one-line forwarder there.
- Constants are aliased after install.
- Variables that a component reassigns become getters.
- G4 turns `hooked_html()` into a table of markers, each found exactly once.

**Measurements:**
- **Scene fingerprint:** a seeded `Math.random`, then `renderer.info` and the mesh count must be equal before and after.
- **Frame time:** the M15 laptop, Rich and Fast, 60 s each in the street, Centralhallen and the train; median and p95.
- **First load:** cold and warm, 10 runs each, unthrottled and on Fast 4G; median and p95. Proposed budget: +100 ms cold and +50 ms warm (the owner sets it).


## 3. Conflicts and order
State of the open work on 2026-11-26. PR #62 has since merged; the others were open then and must be rechecked before each slice.

| PR or branch | Touches | Wait for it |
| --- | --- | --- |
| #62 | setTab/uiInit 1179, modal 2744, title 5943–6298; tests/game.py | G4, UI shell, title, TXT |
| #63 | CSS 435, 591 | U1 |
| #64 | tools and tests only | only a top-level styles/ (D8) |
| #65 | the Worker only | none |
| #66 | buildWorld setup 2803–2821, resize, tick, API; tests/game.py new_context | G4, W0, environment, W10 |
| #67 | routeOf 1921, render 2768, facades 2964; hooks | G4, flights, panels, tiles |
| feat/ui-v2 | head; +186 lines of CSS; 1186; icons 1830; 2021–2029; render | U1, icons, panels, places bar |
| feat/r2 | 1071, 1224, 1265, after 1330, tick 5872, start 6314–6324 | G5, S1, civic, main loop, main.js |

- **Safe to start now:** G1 (if it leaves tests/game.py alone), G2, G3, B1, D1, the SL, weather and news fetchers, customs, and writing W1 (merge it after G4 and W0).
- **Rule:** one region is "in move" at a time, recorded in QUEUE.md.

## 4. Hazards
1. **Reassigned functions.** `lifeMailHooks()` (2276–2288, run at 2521) wraps `log` 1350, `addBill` 2552, `spendTime` 1600 and `sleep` 2596. `newGame` is wrapped at 2396. Fold them into a base function plus a static wrapper (the wrappers drop return values and still run after an early return).
2. **Shared mutable variables.**
   - `busy` is written in 7 sections and in `buildWorld`.
   - `S` is replaced at 1332, 6323 and 6326; `W` and `CITY` at 6329–6330; `DESK` from the world (4393).
   - 23 of `buildWorld`'s `let`s are written from other sections. Central reads 8 changing world variables, and `JR` is read 23 times outside Central.
   - Tables patched after they are defined: `BG`, `ACTS` (1696–1699, including a getter-only `cost`) and `EVENTS.push` (2665).
3. **Load order.** Function declarations are hoisted; a destructured `const` is not. Code that runs at load includes `syncServerTime` (1271), the patches, 2396, 2521, `applyHints` (5941), the key listeners (5943), listeners at 6194 and 6316, and `start()` (6341).
4. **Strict mode is safe by analysis.** The script parses as strict, writes no undeclared names, uses `this` only in `new Agent`, and uses no `arguments`, `eval` or `with`. The remaining risk is an error newly swallowed by one of the 58 empty catch blocks (out of 144); G2 measures that.
5. **Three live bugs.** `pickR` is declared only inside `buildWorld` (2806) but is called outside it at:
   - 2084: answering a call from family or a friend;
   - 2008: `friendHome()` for a friend with no home yet;
   - 2003: the family video call from abroad.

   Each throws a ReferenceError. They date from commits 7e269f0 and bab51ba. `pickA` (879) has the same body. Verified by the lead on 2026-11-26. **A fix is in progress on branch `fix/pickr-scope`** (slice B1).
6. **Save safety.** Keep `stockholm-life-v4`, `SV`, the slot keys and `migrate`. After S2, `negative_controls.py` must point at save.js. Comparisons through `SL_INDEX_HTML` will then need a whole worktree.
7. **Tests that read index.html text:** loading_flash, menu_extras, name and clock. G1's tests/sources.py handles them.
8. **Many requests.** Cloudflare's default `max-age=0, must-revalidate` means every visit revalidates about 80 files, but a visitor never gets a mix of versions. E1 needs `modulepreload`. Moving the CSS out costs about one round trip (estimate).
9. **Publishing.** Cloudflare serves the repository minus `.assetsignore`. `live_check.published()` and deploy.yml know index.html, data/ and src/, so `src/styles/` needs no change.
10. **After ES modules.** Keep a small classic loader that reports which import failed (6 tests check that message). 12 test files use `require()`; put that behind one helper.
11. **three.js.** World components take `THREE` from `ctx`.

## 5. Decisions
All nine approved by the owner on 2026-11-27, as recommended (asked "approve D1-D9 as recommended"; answered "merge and approve all").

| # | Decision | Status |
| --- | --- | --- |
| D1 | Option A and the target above; markup stays in index.html | Approved by the owner, 2026-11-27 |
| D2 | No build step (revisit only if the first-load budget fails after E1) | Approved by the owner, 2026-11-27 |
| D3 | Parser for the guard rails: vendor pinned acorn, acorn-walk and eslint-scope in tools/vendor/, not published | Approved by the owner, 2026-11-27 |
| D4 | Strict mode for the game script now | Approved by the owner, 2026-11-27 |
| D5 | A minimal state owner before the full M1 design (moves MODULES.md step 7's gate) | Approved by the owner, 2026-11-27 |
| D6 | Move-only PRs bundled per area, up to about 600 lines (about 30 PRs) | Approved by the owner, 2026-11-27 |
| D7 | Merge order as in §3, one region in move at a time | Approved by the owner, 2026-11-27 |
| D8 | CSS in src/styles/ | Approved by the owner, 2026-11-27 |
| D9 | Machine-checked renames in world moves (`walk` to `ctx.walk`, `JR` to `CENTRAL.JR`) | Approved by the owner, 2026-11-27 |

## 6. The first three slices
### Slice 1 (m3-guardrails): tools and tests only; tests/game.py untouched
- **`tools/modcheck.js`:**
  - `scope <files>`: fails on any undeclared name that is not in `tools/modcheck-globals.txt` (53 browser globals plus `THREE`, `module`, `require` and `globalThis`). Known exceptions are listed by line with a KNOWN_ISSUES id: `pickR` at 2003, 2008 and 2084, until B1.
  - `move --base --from --to [--rename]`: compares acorn token streams, ignoring comments and whitespace, and checks the region is gone.
  - `strict <file>`.
- **`tests/test_modcheck.py`:** the scope gate on the real files, and the move check on fixtures. A changed literal, an unrenamed name, swapped statements or a dropped line must fail; reformatting and comments must pass.
- **`tests/sources.py`:** index.html plus the files it loads; loading_flash and menu_extras switch to it.
- **Docs:** MODULES.md §2.3–2.4 and tests/README.md.
- **Done when:** the tests pass locally and in CI, an injected undeclared call makes `scope` fail, and the full suite is green. 1–2 days.

### Slice 2 (m3-strict-script)
- **The change:** `'use strict';` as the first statement at 729.
- **`tests/test_strict.py`:** the directive is there, and `this` is undefined.
- **Proof:**
  1. `modcheck instrument` reports every catch block through `sendBeacon`.
  2. Run the full suite on main and on the branch, with the request logs kept.
  3. The swallowed-error lists must be equal, and there must be no new page or console errors.
- Under a day, plus two full local runs.

### Slice 3 (m3-fold-life-hooks)
- **The change:**
  1. Rename `log`, `spendTime`, `addBill` and `sleep` to `*Core`.
  2. Replace `lifeMailHooks()` with four declarations whose bodies are the old wrappers verbatim.
  3. Delete the call at 2521.
  4. Leave `newGame` until G5.
- **`tests/test_life_hooks.py`**, written first and passing on main:
  - the HR mail on `log('Hired as …!')`;
  - the SL bill and its invoice mail;
  - `incomingChats` on `spendTime`, with real time off and on;
  - the to-do roll after `sleep`;
  - a source check that none of the four names is reassigned.
- **Proof:** modcheck move with the renames; test_time_rules; a negative control in which the `log` wrapper drops `sendMail` must fail.
- Under a day.

## Stale documents
- PROJECT_STATUS and QUEUE: refreshed on branch docs/status-2026-11-25, `b7f22a5` (at the time of the review).
- MODULES.md said `W` has 51 entries; it has 61. Corrected on 2026-11-27.
