"""Save compatibility fixtures (quality strategy A7, task save-fixtures): saves written by earlier builds still load and migrate.

The fixtures in tests/fixtures/saves/ are real saves: written by the game at named commits (55c196b, 870fe30 = the live site, 3eb5711; life and actions through its UI, place entry and the save trigger through test hooks),
with the provenance and a hash of each file in manifest.json (see tests/fixtures/saves/README.md). The one
exception is v3-legacy, written by hand and labelled synthetic: no build in the history ever wrote the v3 key.

What is checked, for every fixture the current build can import (a v3 life has no `flags.started`, so it goes through load() only):
  - migration keeps every key and value (only `v` 4 -> 5 changes), adds only `bills`, drops nothing, and is idempotent;
  - the file checks of an import: a bad hash, an unsupported or missing version and a bad format are refused;
  - loading the save at start: no intro, version 5, no uncaught error, the same values apart from the live weather and, in a station
    or a train, the station time (the hour, the needs that drain with it, the place stamp) and the log line of the entry (M19), and the
    place comes back;
  - saving writes every field of the fixture (nothing dropped), and saving and reloading is stable, and exporting then importing a life gives the same life.
Run on another index.html with SL_INDEX_HTML=<file> for a negative control (tests/fixtures/saves/README.md lists the mutations)."""
import hashlib, json, re, time
from pathlib import Path
import pytest
import game

FX = Path(__file__).resolve().parent / 'fixtures' / 'saves'
MANIFEST = json.loads((FX / 'manifest.json').read_text(encoding='utf-8'))['fixtures']
IDS = [e['id'] for e in MANIFEST]
TS = 'window.__TS'
CURRENT = 5
# what the game rewrites at start from live data, and what restoring a place changes; nothing else may differ
LIVE = ['temp', 'weather', 'wx']                   # the weather reading from Open-Meteo is applied at start (applyLiveWeather)
# in a station or a train the clock keeps running (M19): the hour moves on, the needs drain with it (needsTick), the saved place stamp holds
# the hour, and restoring the place logs the entry. Every other fixture is compared strictly.
STATION_TIME = ['hour', 'log', 'hunger', 'hygiene', 'fun', 'place']
RESTORE = {'station': STATION_TIME, 'train': STATION_TIME}
ONCE = "try {{ if (!sessionStorage.getItem('t')) {{ localStorage.setItem({k}, {v}); sessionStorage.setItem('t', 1) }} }} catch (e) {{}}"
# diff(a, b, skip): the paths of a whose value is missing or different in b, ignoring the top-level keys in skip
DIFF = """const diff = (a, b, skip) => { const out = [], same = (x, y) => JSON.stringify(x) === JSON.stringify(y);
  const walk = (x, y, p) => { if (x && typeof x === 'object' && y && typeof y === 'object' && Array.isArray(x) === Array.isArray(y)) {
      for (const k of Object.keys(x)) { if (p === '' && skip.includes(k)) continue; if (!(k in y)) out.push(p + k + ' MISSING'); else walk(x[k], y[k], p + k + '.') } }
    else if (!same(x, y)) out.push(p.slice(0, -1) + ': ' + String(JSON.stringify(x)).slice(0, 40) + ' -> ' + String(JSON.stringify(y)).slice(0, 40)) };
  walk(a, b, ''); return out };"""


def fixture(fid):
    e = next(e for e in MANIFEST if e['id'] == fid)
    raw = (FX / e['file']).read_text(encoding='utf-8')
    return e, raw, json.loads(raw)


def importable(fid):
    """A life the file import accepts (it must have started and have a position); a v3 life does not, and goes through load()."""
    g = fixture(fid)[2]
    return bool(g.get('flags', {}).get('started') and g.get('pos'))


IMPORTABLE = [i for i in IDS if importable(i)]


# ---------- the fixture files themselves (no browser) ----------
def test_manifest_matches_the_files():
    listed = {e['file'] for e in MANIFEST}
    on_disk = {p.name for p in FX.glob('*.json')} - {'manifest.json'}
    assert listed == on_disk, f'manifest and folder differ: {sorted(listed ^ on_disk)}'
    for e in MANIFEST:
        raw = (FX / e['file']).read_text(encoding='utf-8')
        assert hashlib.sha256(raw.encode('utf-8')).hexdigest() == e['sha256'], f"{e['file']} was changed after it was recorded"
        assert len(raw.encode('utf-8')) == e['bytes'] and len(json.loads(raw)) == e['keys'], e['file']
        assert json.loads(raw).get('v') == e['save_version'], e['file']
        common = ('id', 'file', 'storage_key', 'save_version', 'sha256', 'bytes', 'keys', 'name', 'place', 'authenticity', 'generator')
        if e['authenticity'] == 'synthetic':
            assert all(k in e for k in common + ('source',)), e['id']
            assert e['id'].startswith('v3-') and e['storage_key'] == 'stockholm-life-v3', e['id']
        else:
            assert all(k in e for k in common + ('source_commit', 'source_date', 'generator_commit', 'actions')), e['id']
            assert e['authenticity'].startswith('authentic'), e['id']
            assert re.fullmatch(r'[0-9a-f]{40}', e['source_commit']) and re.fullmatch(r'\d{4}-\d\d-\d\d', e['source_date']), e['id']
            assert re.fullmatch(r'[0-9a-f]{40}', e['generator_commit']), e['id']
            assert e['source_commit'].startswith(e['id'].split('-')[1]), f"{e['id']} is not named after its source commit"


def test_readme_lists_every_fixture():
    """The provenance table in the README must name every hash and source commit of the manifest."""
    readme = (FX / 'README.md').read_text(encoding='utf-8')
    for e in MANIFEST:
        assert e['file'] in readme and e['sha256'] in readme, f"README does not list {e['file']} with its hash"
        assert e.get('source_commit', '(none: written by hand)') in readme, f"README does not list the source commit of {e['id']}"


def test_fixtures_cover_every_save_version_and_place():
    assert {e['save_version'] for e in MANIFEST} == {None, 4, 5}, 'a save version has no fixture'
    builds = {e['source_commit'][:7] for e in MANIFEST if e['authenticity'] != 'synthetic'}
    assert {'55c196b', '870fe30', '3eb5711'} <= builds, builds
    assert {e['place'] for e in MANIFEST if e['save_version'] == 5} == {'street', 'station', 'train', 'interior'}


def test_fixtures_hold_no_personal_data():
    """Synthetic lives named "Fixture Anna" (v3-legacy: "Old"). No e-mail address, web address, file path or phone number."""
    for e in MANIFEST:
        raw = (FX / e['file']).read_text(encoding='utf-8')
        assert e['name'] in ('Fixture Anna', 'Old') and json.loads(raw)['name'] == e['name'], e['id']
        assert not re.search(r'https?://|[\w.+-]+@[\w-]+\.[a-z]{2,}|/home/|/Users/|[A-Za-z]:\\\\|\+\d[\d -]{8,}', raw), e['id']


# ---------- migration and import, on the current build (one page, every fixture) ----------
@pytest.fixture(scope='module')
def lab(browser):
    """A running game with the test hook, used to call the game's own importCheck on every fixture."""
    ctx, page, err = game.new_page(browser, 1366, 768, hook=True)
    game.boot(page)
    yield page
    ctx.close()
    assert err.uncaught == []


MIGRATE = DIFF + """async ([fixtures]) => { const T = window.__TS, out = {};
  const env = async (g, v) => JSON.stringify({format: T.SAVE_FILE, v, game: g, sha256: await T.saveHash(g)});
  for (const [id, g, v] of fixtures) { const r1 = await T.importCheck(await env(g, v));
    if (r1.err) { out[id] = {err: r1.err}; continue }
    const r2 = await T.importCheck(await env(r1.game, 5));
    out[id] = {v: r1.game.v, changed: diff(g, r1.game, []), added: Object.keys(r1.game).filter(k => !(k in g)), dropped: Object.keys(g).filter(k => !(k in r1.game)),
               again: r2.err || diff(r1.game, r2.game, []).concat(diff(r2.game, r1.game, [])) } }
  return out }"""


@pytest.mark.browser
@pytest.mark.hook
def test_migration_keeps_the_life_and_is_idempotent(lab):
    r = lab.evaluate(MIGRATE, [[[i, fixture(i)[2], fixture(i)[0]['save_version'] or 4] for i in IMPORTABLE]])
    for fid in IMPORTABLE:
        want_changed = ['v: 4 -> 5'] if fixture(fid)[0]['save_version'] == 4 else []
        got = r[fid]
        assert 'err' not in got, f'{fid} was refused: {got}'
        assert got['v'] == CURRENT, f"{fid}: version {got['v']}"
        assert got['changed'] == want_changed, f"{fid}: migration changed {got['changed']}"
        assert got['dropped'] == [], f"{fid}: migration dropped {got['dropped']}"
        assert got['added'] == ['bills'], f"{fid}: migration added {got['added']}"   # the one field a saved life may lack
        assert got['again'] == [], f"{fid}: migrating again changed {got['again']}"


INVALID = """async ([fid, g, v]) => { const T = window.__TS, out = {};
  const env = async (game, ver, extra) => JSON.stringify({format: T.SAVE_FILE, v: ver, game, sha256: await T.saveHash(game), ...extra});
  const err = async text => (await T.importCheck(text)).err || '';
  out.valid = !!(await T.importCheck(await env(g, v))).game;
  out.validCurrent = !!(await T.importCheck(await env(g, 5))).game;
  out.tampered = await err(JSON.stringify({...JSON.parse(await env(g, v)), game: {...g, money: g.money + 1}}));
  out.newer = await err(await env(g, 6)); out.zero = await err(await env(g, 0)); out.text = await err(await env(g, '5'));
  out.format = await err(JSON.stringify({...JSON.parse(await env(g, v)), format: 'other'}));
  out.notJson = await err('{not json'); out.noLife = await err(JSON.stringify({format: T.SAVE_FILE, v: 5, game: [], sha256: 'x'}));
  const noPos = {...g}; delete noPos.pos; out.incomplete = await err(await env(noPos, v));
  return out }"""


@pytest.mark.browser
@pytest.mark.hook
def test_import_refuses_what_it_should_and_accepts_every_fixture(lab):
    for fid in IMPORTABLE:
        e, _, g = fixture(fid)
        r = lab.evaluate(INVALID, [fid, g, e['save_version']])
        assert r['valid'] and r['validCurrent'], f'{fid}: a good file was refused: {r}'
        assert 'check does not match' in r['tampered'], f'{fid}: a changed life was accepted: {r}'
        assert 'newer version' in r['newer'], f'{fid}: version 6 was accepted: {r}'
        assert 'no valid version' in r['zero'] and 'no valid version' in r['text'], f'{fid}: a bad version was accepted: {r}'
        assert 'not a Stockholmsliv' in r['format'] and 'not readable' in r['notJson'], f'{fid}: {r}'
        assert 'no life' in r['noLife'] and 'incomplete' in r['incomplete'], f'{fid}: {r}'


# ---------- loading the save at start, saving and reloading, exporting and importing (one fresh browser per fixture) ----------
def reload(page):
    page.reload(wait_until='load')
    page.wait_for_function("() => !document.getElementById('loading')", timeout=180000)
    time.sleep(3)


def stored(page):
    return page.evaluate(f"() => {{ {TS}.save(); return JSON.parse(localStorage.getItem('{game.SAVE_KEY}')) }}")


def wait_for_place(page, place):
    js = {'station': "() => __T.CS.mode === 'station'", 'train': "() => __T.CS.mode === 'ride' && !!__T.JR",
          'interior': f"() => {TS}.W.inside()"}.get(place)
    if js:
        assert game.wait_for(page, js, 120), f'the {place} was not restored'
    else:
        assert page.evaluate(f"() => __T.CS.mode === null && !{TS}.W.inside()"), 'a street life did not start on the street'


@pytest.mark.browser
@pytest.mark.hook
@pytest.mark.parametrize('fid', IDS)
def test_fixture_loads_saves_reloads_and_round_trips(browser, fid):
    e, raw, fx = fixture(fid)
    skip = LIVE + RESTORE.get(e['place'], [])
    ctx, page, err = game.new_page(browser, 1366, 768, hook=True, init_script=ONCE.format(k=json.dumps(e['storage_key']), v=json.dumps(raw)))
    try:
        game.boot(page)
        game.clear_overlays(page)
        # 1. it loads, as the current version, and the life is the same life
        assert not game.intro_shown(page), f'{fid}: the saved life was not loaded'
        assert page.evaluate(f"() => {TS}.S.v") == CURRENT
        wait_for_place(page, e['place'])
        s = page.evaluate(f"() => JSON.parse(JSON.stringify({TS}.S))")
        gone = page.evaluate(DIFF + "([a, b, skip]) => diff(a, b, skip)", [fx, s, skip + ['v']])
        assert gone == [], f'{fid}: loading changed the life: {gone}'
        # 2. saving, reloading and saving again changes nothing (a station or train keeps its clock and log, by design)
        first = stored(page)
        lost = page.evaluate(DIFF + "([a, b, skip]) => diff(a, b, skip)", [fx, first, skip + ['v']])
        assert lost == [], f'{fid}: saving dropped or changed a field of the fixture: {lost}'
        reload(page)
        wait_for_place(page, e['place'])
        second = stored(page)
        unstable = page.evaluate(DIFF + "([a, b, skip]) => diff(a, b, skip)", [first, second, skip])
        assert unstable == [], f'{fid}: save, reload, save is not stable: {unstable}'
        # 3. exporting and importing: a saved life is accepted unchanged, and the imported life is the life after a reload
        r = page.evaluate(DIFF + """async ([g]) => { const T = window.__TS;
            const r = await T.importCheck(JSON.stringify({format: T.SAVE_FILE, v: 5, game: g, sha256: await T.saveHash(g)}));
            return r.err ? {err: r.err} : {again: diff(g, r.game, []).concat(diff(r.game, g, [])), applied: T.importApply(r.game)} }""", [second])
        assert 'err' not in r and r['again'] == [], f'{fid}: export then import changed the life: {r}'
        assert r['applied'] is None, f"{fid}: import was refused: {r['applied']}"
        reload(page)
        wait_for_place(page, e['place'])
        third = stored(page)
        changed = page.evaluate(DIFF + "([a, b, skip]) => diff(a, b, skip)", [second, third, skip])
        assert changed == [], f'{fid}: the imported life is not the exported one: {changed}'
        assert err.uncaught == [], err.uncaught
        assert err.local_failures() == []
    finally:
        ctx.close()
