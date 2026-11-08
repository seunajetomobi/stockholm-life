"""Carry on where you left off (M1b, KNOWN_ISSUES M7 and M19): the save holds the place you are in, with a stamp of the life it was
saved with, and a reload puts you back there; a place an older version did not update is ignored. A life can be exported to a file
and imported in another browser; an import changes nothing unless every check passes.
Run on an older index.html with SL_INDEX_HTML=<file> for the negative control."""
import json
import time
import pytest
import game

pytestmark = [pytest.mark.browser, pytest.mark.hook]

SAVED = f"() => JSON.parse(localStorage.getItem('{game.SAVE_KEY}'))"
TS = "window.__TS"


def life(browser, init_script=None):
    ctx, page, err = game.new_page(browser, 1366, 768, hook=True, init_script=init_script)
    game.boot(page)
    if game.intro_shown(page):
        game.start_life(page)
    game.clear_overlays(page)
    return ctx, page, err


def reload(page):
    page.reload(wait_until='load')
    page.wait_for_function("() => !document.getElementById('loading')", timeout=180000)
    time.sleep(2)


def save(page):
    """Save now and return what is in storage."""
    page.evaluate(f"() => {TS}.save()")
    return page.evaluate(SAVED)


def test_station_place_and_time_restored(browser):
    ctx, page, err = life(browser)
    try:
        game.enter_station(page)
        # one call, so no frame adds station time between setting it and saving
        before, s, pend = page.evaluate(f"() => {{ const h = {TS}.S.hour; __T.CS.pend = 30; {TS}.save(); return [h, ({SAVED})(), __T.CS.pend] }}")
        assert s['place']['kind'] == 'station', s.get('place')
        assert s['place']['stamp'] == page.evaluate(f"() => {TS}.placeStamp({TS}.S)")
        assert s['hour'] == pytest.approx(before + 0.5), 'station time held in CS.pend must be in the save (M19)'
        assert pend == 0, 'the flushed station time must not be counted twice'
        pos = page.evaluate("() => __T.av.position.toArray()")
        reload(page)
        assert game.wait_for(page, "() => __T.CS.mode === 'station'", 60), 'the reload did not return to Stockholm Central'
        time.sleep(1)
        after = page.evaluate("() => __T.av.position.toArray()")
        assert all(abs(a - b) < 0.05 for a, b in zip(after, pos)), (pos, after)
        assert err.uncaught == []
    finally:
        ctx.close()


def test_train_at_the_platform_restored(browser):
    ctx, page, err = life(browser)
    try:
        game.enter_station(page)
        game.board_train(page)
        page.evaluate("() => { __T.JR.depAt = Infinity }")
        ref = page.evaluate("() => __T.JR.d0.ref")
        s = save(page)
        assert s['place']['kind'] == 'train' and s['place']['si'] == 0 and s['place']['phase'] == 'dwell', s['place']
        reload(page)
        assert game.wait_for(page, "() => __T.CS.mode === 'ride' && !!__T.JR && __T.JR.si === 0", 90), 'not back on the train'
        assert page.evaluate("() => __T.JR.d0.ref") == ref
        assert err.uncaught == []
    finally:
        ctx.close()


def test_moving_train_restored_at_the_next_stop(browser):
    ctx, page, err = life(browser)
    try:
        game.enter_station(page)
        game.board_train(page)
        page.evaluate("() => __T.jrSkipStop()")
        assert game.wait_for(page, "() => __T.JR.phase === 'run'", 60), 'the train did not leave'
        s = save(page)
        assert s['place']['kind'] == 'train' and s['place']['phase'] == 'run' and s['place']['si'] == 0, s['place']
        reload(page)
        assert game.wait_for(page, "() => __T.CS.mode === 'ride' && !!__T.JR && __T.JR.si === 1 && __T.JR.phase === 'dwell'", 90), \
            page.evaluate("() => __T.JR && [__T.CS.mode, __T.JR.si, __T.JR.phase]")
        assert err.uncaught == []
    finally:
        ctx.close()


def test_interior_restored(browser):
    ctx, page, err = life(browser)
    try:
        name = page.evaluate(f"""() => {{ const W = {TS}.W; for (let i = 0; i < 50000; i++) {{ const p = W.poi(i); if (!p) break;
            if (p.type === 'cafe' && p.name) {{ W.enterPlace(p); return p.name }} }} return null }}""")
        assert name, 'no café in the city data'
        assert game.wait_for(page, f"() => {TS}.W.inside()", 30), 'did not go inside'
        s = save(page)
        assert s['place']['kind'] == 'interior' and s['place']['ik'] == 'cafe' and s['place']['name'] == name, s['place']
        reload(page)
        assert game.wait_for(page, f"() => {TS}.W.inside() && document.getElementById('inTitle').textContent === {json.dumps(name)}", 60), \
            'the reload did not return inside the café'
        assert err.uncaught == []
    finally:
        ctx.close()


def test_place_from_an_older_version_is_ignored(browser):
    """An older version keeps `place` but not its stamp up to date: a life that moved on starts on the street, as before."""
    ctx, page, err = life(browser)
    try:
        game.enter_station(page)
        s = save(page)
        s['money'] += 1
        s['v'] = 4
        page.evaluate(f"s => localStorage.setItem('{game.SAVE_KEY}', JSON.stringify(s))", s)
        reload(page)
        time.sleep(5)
        assert page.evaluate("() => __T.CS.mode") is None, 'a stale place was restored'
        assert page.evaluate(f"() => {TS}.S.v") == 5
        assert err.uncaught == []
    finally:
        ctx.close()


V4 = {'v': 4, 'name': 'Four', 'bg': 'newcomer', 'day': 3, 'hour': 10, 'money': 1200, 'energy': 70, 'mood': 50, 'social': 10, 'svenska': 5,
      'skill': 40, 'queue': 0, 'home': 'rinkebyRoom', 'loc': 'tc', 'job': None, 'flags': {'started': 1}, 'log': [], 'applied': {}}
ONCE = "try {{ if (!sessionStorage.getItem('t')) {{ localStorage.setItem({k}, {v}); sessionStorage.setItem('t', 1) }} }} catch (e) {{}}"


def test_v4_save_loads_as_v5_on_the_street(browser):
    ctx, page, err = life(browser, ONCE.format(k=json.dumps(game.SAVE_KEY), v=json.dumps(json.dumps(V4))))
    try:
        assert not game.intro_shown(page), 'the v4 life was not loaded'
        assert page.evaluate(f"() => [{TS}.S.name, {TS}.S.v, __T.CS.mode]") == ['Four', 5, None]
        assert err.uncaught == []
    finally:
        ctx.close()


CHECKS = f"""async () => {{ const T = {TS}, game = JSON.parse(JSON.stringify(T.S)), env = async g => ({{format: T.SAVE_FILE, v: 5, game: g, sha256: await T.saveHash(g)}});
  const ok = await env(game), out = {{}};
  out.valid = !!(await T.importCheck(JSON.stringify(ok))).game;
  out.tampered = (await T.importCheck(JSON.stringify({{...ok, game: {{...game, money: game.money + 1}}}}))).err || '';
  out.notJson = (await T.importCheck('{{not json')).err || '';
  out.format = (await T.importCheck(JSON.stringify({{...ok, format: 'other'}}))).err || '';
  out.newer = (await T.importCheck(JSON.stringify({{...ok, v: 6}}))).err || '';
  const noPos = {{...game}}; delete noPos.pos; out.incomplete = (await T.importCheck(JSON.stringify(await env(noPos)))).err || '';
  return out }}"""


def test_import_refuses_bad_files(browser):
    ctx, page, err = life(browser)
    try:
        r = page.evaluate(CHECKS)
        assert r['valid'], r
        assert 'check does not match' in r['tampered'], r
        assert 'not readable' in r['notJson'], r
        assert 'not a Stockholmsliv' in r['format'], r
        assert 'newer version' in r['newer'], r
        assert 'incomplete' in r['incomplete'], r
        assert err.uncaught == []
    finally:
        ctx.close()


def test_import_backs_up_and_full_storage_changes_nothing(browser):
    ctx, page, err = life(browser)
    try:
        page.evaluate(f"() => {TS}.save()")
        before = page.evaluate(f"() => localStorage.getItem('{game.SAVE_KEY}')")
        full = page.evaluate(f"""() => {{ const T = {TS}, g = JSON.parse(JSON.stringify(T.S)), set = Storage.prototype.setItem;
            g.name = 'Imported'; Storage.prototype.setItem = function () {{ throw new DOMException('full', 'QuotaExceededError') }};
            try {{ return T.importApply(g) }} finally {{ Storage.prototype.setItem = set }} }}""")
        assert 'Storage is full' in (full or ''), full
        assert page.evaluate(f"() => localStorage.getItem('{game.SAVE_KEY}')") == before, 'a refused import changed the save'
        assert page.evaluate("() => Object.keys(localStorage).filter(k => k.includes('-before-import-')).length") == 0
        ok = page.evaluate(f"() => {{ const T = {TS}, g = JSON.parse(JSON.stringify(T.S)); g.name = 'Imported'; return T.importApply(g) }}")
        assert ok is None, ok
        kept = page.evaluate("() => Object.keys(localStorage).filter(k => k.includes('-before-import-')).map(k => localStorage.getItem(k))")
        assert kept == [before], 'the life before the import was not kept'
        reload(page)
        assert page.evaluate(f"() => {TS}.S.name") == 'Imported'
        assert err.uncaught == []
    finally:
        ctx.close()


def test_export_then_import_in_a_fresh_browser(browser, tmp_path):
    """The file a player saves is accepted by a browser that has never seen the life, and the life carries on there."""
    ctx, page, err = life(browser)
    try:
        page.evaluate(f"() => {{ {TS}.S.money += 123; {TS}.save() }}")
        want = page.evaluate(f"() => [{TS}.S.name, {TS}.S.day, {TS}.S.money]")
        page.evaluate("() => document.querySelector('#dock button[data-tab=phone]').click()")
        time.sleep(0.5)
        page.evaluate("() => [...document.querySelectorAll('#apps > *')].find(e => e.innerText.includes('Save file')).click()")
        with page.expect_download() as dl:
            page.click('#modalRoot #exp')
        path = tmp_path / dl.value.suggested_filename
        dl.value.save_as(path)
        assert path.name.startswith('stockholmsliv-') and path.suffix == '.json', path.name
    finally:
        ctx.close()
    ctx, page, err = game.new_page(browser, 1366, 768, hook=True)
    try:
        game.boot(page)
        assert game.intro_shown(page)
        page.click('#modalRoot #impLife')
        page.set_input_files('#modalRoot #impf', str(path))
        page.wait_for_selector('#modalRoot #yes', timeout=10000)
        with page.expect_navigation(timeout=60000):
            page.click('#modalRoot #yes')
        page.wait_for_function("() => !document.getElementById('loading')", timeout=180000)
        time.sleep(2)
        assert not game.intro_shown(page), 'the imported life was not loaded'
        assert page.evaluate(f"() => [{TS}.S.name, {TS}.S.day, {TS}.S.money]") == want
        assert err.uncaught == []
    finally:
        ctx.close()
