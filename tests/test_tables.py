"""src/tables.js, M3 step 5 (docs/MODULES.md): the data tables JOBS, COUNTRIES, OPEN, COURSES, ITEMS and HOMES, moved out of index.html unchanged.

Unit tests run the module in Node; the content is pinned by a hash of its JSON taken from the declarations in
index.html before each move (JOBS and COUNTRIES at 874ce40; OPEN, COURSES and ITEMS at 79ee5f5; HOMES at dca25e6), so any change to a value, key or order is visible.
Browser tests check that the game's names are the module's own objects, that consumers (the start screen's
routes) work with them, and that a missing module stops the game with a message.
Run alone with: python3 -m pytest tests/test_tables.py"""
import hashlib, json, shutil, subprocess
import pytest
import game

MODULE = game.ROOT / 'src' / 'tables.js'
NAMES = ['JOBS', 'COUNTRIES', 'OPEN', 'COURSES', 'ITEMS', 'HOMES']
# sha256 of JSON.stringify({JOBS,COUNTRIES}) of the original declarations (3488 characters). A deliberate change to a
# job rate or a country changes this value; check the new data (and its date, AGENTS.md rule 8), then update it.
GOLDEN = '9c450af42d50a2ce29c38152e8739b9ea058cb834f006b5c39f53f047a0c86fc'
# sha256 of the compact JSON of each of OPEN, COURSES and ITEMS at 79ee5f5, before they moved.
GOLDEN3 = {
    'OPEN': 'a17c3ba07a8cbf8801455dd5fc87cdb627d76905c475de57fbd033e53d81a49c',
    'COURSES': '067fbf8b3e94596d00facacaa0cacb284e931f8c2da80f991e5055a8d29f5331',
    'ITEMS': '546c4492887519611fa470ee2470b3289671923c73f7150a0c9f77f649470151',
}
# sha256 of JSON.stringify(HOMES) (UTF-8, 1098 characters, 12 entries) at dca25e6: the ten homes of the literal in index.html
# plus the 'none' and 'jour' entries that line 736 then added at startup. Computed by evaluating the original source, not this module.
GOLDEN_HOMES = 'a65ced23c380efaec0c5de95dc9190a87421e336cdf65e13e4f2a4dc9c91f0e9'
HOME_KEYS = ['rinkebyRoom', 'korridor', 'parents', 'soderRoom', 'kistaRoom', 'sbgRoom', 'fhRinkeby', 'fhSbg', 'fhKungs', 'fhSoder', 'none', 'jour']
SIZES = {'OPEN': (12, 598), 'COURSES': (8, 1129), 'ITEMS': (16, 2079)}   # keys, characters of compact JSON
JOB_KEYS = ['foodora', 'barista', 'guide', 'usk', 'dev', 'consult', 'cleaner', 'kitchen', 'cook', 'warehouse', 'barnsk', 'uskcert', 'itsup', 'taxidrv']


def node(expr):
    exe = shutil.which('node')
    if not exe:
        pytest.skip('node is not installed')
    r = subprocess.run([exe, '-e', f'const G=require(process.argv[1]);process.stdout.write(JSON.stringify({expr}))', str(MODULE)],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_interface():
    assert node('Object.keys(G)') == NAMES
    assert node('[Array.isArray(G.COUNTRIES),typeof G.JOBS,typeof G.OPEN,typeof G.COURSES,typeof G.ITEMS,typeof G.HOMES]') == [True, 'object', 'object', 'object', 'object', 'object']


def test_same_content_as_before_the_move():
    out = node('{JOBS:G.JOBS,COUNTRIES:G.COUNTRIES}')
    assert len(json.dumps(out, ensure_ascii=False, separators=(',', ':'))) == 3488
    assert hashlib.sha256(json.dumps(out, ensure_ascii=False, separators=(',', ':')).encode('utf-8')).hexdigest() == GOLDEN


def test_open_courses_items_same_content_as_before_the_move():
    for name, (keys, size) in SIZES.items():
        data = node(f'G.{name}')
        text = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
        assert (len(data), len(text)) == (keys, size), name
        assert hashlib.sha256(text.encode('utf-8')).hexdigest() == GOLDEN3[name], name


def test_homes_same_content_as_before_the_move():
    text = json.dumps(node('G.HOMES'), ensure_ascii=False, separators=(',', ':'))
    assert len(text) == 1098
    assert list(node('G.HOMES')) == HOME_KEYS
    assert hashlib.sha256(text.encode('utf-8')).hexdigest() == GOLDEN_HOMES


def test_homes_shape():
    homes, areas = node('[G.HOMES,require(process.argv[1].replace("tables.js","geography.js")).AREAS]')
    for k, h in homes.items():
        assert list(h)[:4] == ['name', 'd', 'rent', 'type'], k
        assert isinstance(h['name'], str) and isinstance(h['rent'], int) and h['type'] in ('andrahand', 'student', 'parents', 'forstahand', 'none', 'jour'), k
        assert h['d'] is None or h['d'] in areas, k            # every district reference resolves
    assert homes['none'] == {'name': 'No home', 'd': None, 'rent': 0, 'type': 'none'}
    assert homes['jour']['type'] == 'jour' and homes['jour']['rent'] == 0
    assert {k: h['queue'] for k, h in homes.items() if h['type'] == 'forstahand'} == {'fhRinkeby': 5, 'fhSbg': 7, 'fhKungs': 9, 'fhSoder': 12}
    assert [k for k, h in homes.items() if 'queue' in h] == ['fhRinkeby', 'fhSbg', 'fhKungs', 'fhSoder']


def test_open_courses_items_shape():
    op, co, it = node('[G.OPEN,G.COURSES,G.ITEMS]')
    assert list(op) == ['service', 'bank', 'sys', 'vc', 'sfi', 'lib', 'sal', 'skansen', 'vasa', 'apotek', 'galleria', 'migr']   # keys the places and services look up
    assert all('label' in v for v in op.values())
    assert op['skansen'] == {'all': [10, 16], 'label': 'Daily 10–16'}
    assert list(co)[:2] == ['sva', 'usk'] and len(co) == 8
    assert all({'where', 'n', 'h', 'gain'} <= set(v) for v in co.values())
    assert len(it) == 16
    assert all({'n', 'c', 'use', 'at'} <= set(v) for v in it.values())
    assert it['kaffe']['c'] == 38 and 'cafe' in it['kaffe']['at']


def test_tables_are_plain_data():
    # no functions, so a JSON round trip equals the object; nothing in them refers to the game state
    assert node('JSON.stringify(G)===JSON.stringify(JSON.parse(JSON.stringify(G)))') is True
    assert node('Object.values(G).every(t=>Object.values(t).every(v=>typeof v!=="function"))') is True


def test_jobs_shape():
    jobs = node('G.JOBS')
    assert list(jobs) == JOB_KEYS                       # the order is the order of the job list on screen
    for k, j in jobs.items():
        assert {'name', 'where', 'rate', 'req'} <= set(j), k
        assert isinstance(j['rate'], (int, float)) and j['rate'] > 0, k
    assert jobs['foodora'] == {'name': 'Food courier (gig)', 'where': 'any', 'rate': 135, 'req': {}, 'gig': 1}
    assert jobs['dev']['rate'] == 340 and jobs['taxidrv']['lic'] == 1


def test_countries_shape():
    rows = node('G.COUNTRIES')
    assert len(rows) == 51 and rows[0][0] == 'Sweden' and rows[1][0] == 'Nigeria'   # routesFrom falls back to COUNTRIES[1]
    assert all(len(r) == 7 for r in rows)
    names = [r[0] for r in rows]
    assert len(set(names)) == len(names)
    assert {r[2] for r in rows} <= {'se', 'eu', 'noneu', 'nordic'}


# ---------- in the game ----------
@pytest.mark.browser
@pytest.mark.hook
def test_game_uses_the_module(browser):
    """The game script's JOBS and COUNTRIES are the module's own objects, and their consumers work."""
    expose = 'window.__G={JOBS,COUNTRIES,OPEN,COURSES,ITEMS,HOMES,routesFrom,workPlace,EU_GOODS,hoursFor,shopItemsFor,homeD,assignAddress,openHousing,S,D};return API;'
    body = game.hooked_html().replace('return API;', expose)
    ctx = game.new_context(browser, viewport={'width': 1366, 'height': 768})
    ctx.route('**/index.html', lambda route: route.fulfill(status=200, content_type='text/html; charset=utf-8', body=body))
    page = ctx.new_page()
    err = game.Errors(page)
    try:
        game.boot(page)
        assert page.evaluate("() => !!window.__G && !!document.querySelector('canvas')"), 'the city did not start'
        assert page.evaluate("() => ['JOBS','COUNTRIES','OPEN','COURSES','ITEMS','HOMES'].filter(k => window.__G[k] !== window.StockholmLife.tables[k])") == []
        assert page.evaluate("() => Object.keys(window.__G.JOBS).length === 14 && window.__G.COUNTRIES.length === 51")
        # consumers read the tables: the flight routes of a country and the EU goods rule
        assert page.evaluate("() => Array.isArray(window.__G.routesFrom('Nigeria')) && window.__G.EU_GOODS('Sweden') === true && window.__G.EU_GOODS('Nigeria') === false")
        assert page.evaluate("() => Object.keys(window.__G.OPEN).length === 12 && Object.keys(window.__G.COURSES).length === 8 && Object.keys(window.__G.ITEMS).length === 16")
        # consumers: the default opening hours, and the shop list read ITEMS
        assert page.evaluate("() => JSON.stringify(window.__G.hoursFor('skansen')) === '[10,16]' && JSON.stringify(window.__G.hoursFor('nonesuch')) === '[0,24]'")
        assert page.evaluate("() => window.__G.shopItemsFor({type: 'cafe'}).some(([k]) => k === 'kaffe')")
        # nothing changed the tables while the game ran (the same hashes as in Node, over the live objects)
        live = page.evaluate("() => JSON.stringify({OPEN: window.__G.OPEN, COURSES: window.__G.COURSES, ITEMS: window.__G.ITEMS})")
        node_side = node('{OPEN:G.OPEN,COURSES:G.COURSES,ITEMS:G.ITEMS}')
        assert json.loads(live) == node_side
        # HOMES: the live object equals the pre-move hash (so nothing added 'none' or 'jour' at startup, or changed a rent)
        live_h = page.evaluate("() => JSON.stringify(window.__G.HOMES)")
        assert hashlib.sha256(live_h.encode('utf-8')).hexdigest() == GOLDEN_HOMES
        # consumers: homeD for no home, the emergency flat and a normal home; addresses; the housing modal's choices
        assert page.evaluate("() => { const G = window.__G, S = G.S, old = S.home; const r = []; for (const k of ['none', 'jour', 'soderRoom']) { S.home = k; r.push(G.homeD()); } S.home = old; return JSON.stringify(r); }") == '[null,"rinkeby","sodermalm"]'
        assert page.evaluate("() => { const G = window.__G, S = G.S; S.home = 'soderRoom'; G.assignAddress(); const a = S.addr; S.home = 'none'; G.assignAddress(); return !!a && typeof a.x === 'number' && typeof a.z === 'number' && S.addr === null; }")
        choices = page.evaluate("() => { const G = window.__G, S = G.S; S.docs.queue = 1; S.home = 'rinkebyRoom'; G.openHousing(); const a = [...document.querySelectorAll('#modalRoot .choice')].map(b => b.dataset.k); S.home = 'none'; G.openHousing(); const b = [...document.querySelectorAll('#modalRoot .choice')].map(b => b.dataset.k); return [a, b]; }")
        assert choices[0] == ['soderRoom', 'kistaRoom', 'sbgRoom', 'fhRinkeby', 'fhSbg', 'fhKungs', 'fhSoder']
        assert choices[1] == ['rinkebyRoom', 'soderRoom', 'kistaRoom', 'sbgRoom', 'fhRinkeby', 'fhSbg', 'fhKungs', 'fhSoder']   # no 'none', 'jour', 'korridor' or 'parents'
        assert err.uncaught == []
        assert err.local_failures() == []
    finally:
        ctx.close()


@pytest.mark.browser
def test_missing_module_stops_with_a_message(browser):
    ctx = game.new_context(browser, viewport={'width': 1366, 'height': 768})
    ctx.route('**/src/tables.js', lambda route: route.fulfill(status=404, content_type='text/plain', body='not found'))
    page = ctx.new_page()
    err = game.Errors(page)
    try:
        page.goto(game.BASE + '/index.html', wait_until='load', timeout=120000)
        assert game.wait_for(page, "() => (document.getElementById('loadtxt')||{}).textContent.includes('could not load src/tables.js')", 30), \
            page.evaluate("() => (document.getElementById('loadtxt')||{}).textContent")
        assert any('src/tables.js did not load' in e for e in err.uncaught), err.uncaught
        assert page.evaluate("() => !document.querySelector('canvas') && !document.querySelector('#modalRoot #go')"), 'the game started anyway'
    finally:
        ctx.close()
