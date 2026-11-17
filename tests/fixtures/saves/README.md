# Save fixtures

Saves from earlier builds of the game, used by [`tests/test_save_fixtures.py`](../../test_save_fixtures.py) (quality strategy A7: saves from every earlier version load correctly in every build). **No game code is involved**: these files only hold data and the tests read them.

Every life is synthetic: a character named "Fixture Anna" made through the character-creation form (the v3 life is named "Old"). No real player data is stored here, and none may be added: never copy a save from a real browser.

## What is in the folder

| File | Authenticity | Source commit | Commit date | Save version (storage key) | Place | Keys | SHA-256 of the file |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `v3-legacy.json` | synthetic | `(none: written by hand)` | – | 3 (no field) (`stockholm-life-v3`) | – | 17 | `b9620854b1e0f97d13c29dcce2df5bf839901d40ab44f6f998ed0c679394b048` |
| `v4-55c196b.json` | authentic | `55c196b9a474344fd3bed10477183205f8efb05a` | 2026-10-25 | 4 (`stockholm-life-v4`) | none | 61 | `d93019b9a397d0a3bf4a5e683dc7ba6eb889ada3a72c97555752efe1241c05f1` |
| `v4-870fe30.json` | authentic | `870fe309543c6eb375e6e150423002a09763a3db` | 2026-10-26 | 4 (`stockholm-life-v4`) | none | 64 | `69ce16c7ad0d2e5f9238ce4aea50fd7cd2d1706da171ffb41af56ad072f1e551` |
| `v5-3eb5711-street.json` | authentic | `3eb5711bdb55ad6aa02276eec8d73193092be5b3` | 2026-11-08 | 5 (`stockholm-life-v4`) | street | 65 | `027a56b169b25ff87355c761db8353c28e64ce7641630aa72ea279e064337f24` |
| `v5-3eb5711-station.json` | authentic | `3eb5711bdb55ad6aa02276eec8d73193092be5b3` | 2026-11-08 | 5 (`stockholm-life-v4`) | station | 67 | `783de66b9f97bc2931fbe91e59382ae955e7d30e2b655e2cd43b0430864e8c70` |
| `v5-3eb5711-train.json` | authentic | `3eb5711bdb55ad6aa02276eec8d73193092be5b3` | 2026-11-08 | 5 (`stockholm-life-v4`) | train | 67 | `f2aac6d042ecff582be6e6caaac6d60ea691a6241df685bb7090be487bf9f780` |
| `v5-3eb5711-interior.json` | authentic | `3eb5711bdb55ad6aa02276eec8d73193092be5b3` | 2026-11-08 | 5 (`stockholm-life-v4`) | interior | 65 | `f2fc159e2dfa63ca20c751ffe5daa1a7373a773bd6b57144050317a63006e3ff` |

- **authentic**: the real game at the source commit wrote the file; the save data is the game's own output, stored unedited. Not everything was done through the UI: the life was created and the five actions played through the game's buttons, but the place was entered through the test hook (`__T.csEnter` for Stockholm Central, `__T.jrStart` for the train, `W.enterPlace` for the café), and the save was triggered by the hook's `__TS.save()` for the v5 files and by a `pagehide` event for the v4 files. The generator (`tests/fixtures/generate_saves.py`) runs that commit's `index.html` in headless Chrome, creates the life, plays five real actions (requests public documents three times, adds a to-do, joins a civic list) and, for the v5 files, enters the place. What the game wrote to localStorage is stored as it was: nothing is edited, added or removed.
- **synthetic**: `v3-legacy.json` is written by hand from the shape `migrate()` expects (it is the life of `tests/test_save.py`). **No build in the git history ever wrote the v3 key** (the first commit already reads it as the legacy key), so a genuine v3 save cannot be made. It proves that the code can load a life of that shape, not that a real v3 save looks like this.
- `55c196b` is the first commit (2026-10-25). `870fe30` is the build that was live when these files were made (the Deploy workflow's last deployment, 2026-10-31); a deployment of `main` migrates players' v4 saves from this shape. `3eb5711` is the last commit before the modules moved out of `index.html` (the game's logic is the same as on `main`). The v5 files cover each place a life can be saved in: street, Stockholm Central, a train and a café.
- The `wx` field holds the live weather from Open-Meteo at the time of generation (public data, not personal).
- `manifest.json` records every field above for each file, plus the byte count, the actions played and `generator_commit`: the commit the generator ran on, which is the base of the branch that adds these files (`b3305d3`). The generator itself is added together with the fixtures, so `generator_commit` does not contain it. `test_manifest_matches_the_files` fails if a file is changed, added or removed without the manifest, or if this table does not list every hash and source commit in the manifest.

## Rules

1. **Never edit a fixture by hand.** A hand-edited "historical" save proves nothing, and the place stamp depends on the life's own fields. Regenerate instead.
2. **The game uses unseeded random numbers**, so running the generator again gives different files. The committed files and their hashes are the evidence. To add a fixture: add a line to `SPECS` in the generator, run `SL_PORT=8123 python3 tests/fixtures/generate_saves.py --only <id>`, then add the row to the table above.
3. **A change to the shape of `S` needs a fixture and a migration step in the same pull request** (docs/TEST_PLAN.md, section 5). Generate the fixture from the build *before* the change, so that the test proves the old save still loads.
4. The generator needs the full git history (`git show` of old commits), Playwright and Chrome. The tests do not: they only read the committed files.

## What the tests check

For each fixture the current build can import (a v3 life has no `flags.started`, so it goes through `load()` only):

- **Migration** (the game's own `importCheck`, which runs `migrate`): every key and value is kept; the only change is `v` 4 → 5 for a v4 life; the only key added is `bills`; nothing is dropped; migrating twice gives the same life.
- **Import refusals**: a changed life (hash mismatch), version 6, version 0, a version that is not a number, a wrong format, text that is not JSON, no life and an incomplete life are all refused; a good file is accepted at its own version and at 5.
- **Loading at start**: no character creation, version 5, no uncaught error, no failed local request, and the same values. Two things may differ, and only these: the live weather (`temp`, `weather`, `wx`) is replaced with the current reading, and in a station or a train the clock keeps running, so `hour`, the needs that drain with it (`hunger`, `hygiene`, `fun`), the place stamp (`place`) and the `log` line of the entry change (KNOWN_ISSUES M19); street, interior and every v4 life are compared strictly. The place is restored (street, station, train or interior).
- **Saving and reloading** is stable (same exceptions), and **exporting then importing** a life gives the same life, in storage and after a reload.

## Negative controls

`tests/fixtures/negative_controls.py` shows that the tests notice a broken migration. It makes a copy of `index.html` with one deliberate fault in a temporary folder, runs the tests on that copy (`SL_INDEX_HTML`, the switch the other hooked tests use) and reports whether a test failed. The faults: migrate overwrites the documents, `lifeInit` empties the people, `migrate` forgets the version, `migrate` changes the life each time it runs, `inboxInit` replaces the to-do list, import skips the migration, import ignores the hash, import accepts a newer version. The first run is the unmutated game and must pass. `index.html` in the repository is never modified.

```
SL_PORT=8124 python3 tests/fixtures/negative_controls.py
```

## Known limits

- The v3 fixture is synthetic (above). A real v3 save has never been tested.
- Five actions do not reach every field of `S`. Fields that only appear later in a life (a job, a partner, a licence, a criminal record) are not in these fixtures; the preservation check covers whatever each fixture holds.
- The tests run on the current build only. They show that old saves load in it, not that the new saves load in an old build (the existing test `test_place_from_an_older_version_is_ignored` covers a v5 place read by older rules).
