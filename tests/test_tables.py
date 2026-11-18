"""src/tables.js, M3 step 5 (docs/MODULES.md): the data tables JOBS and COUNTRIES, moved out of index.html unchanged.

Unit tests run the module in Node; the content is pinned by a hash of its JSON taken from the declarations in
index.html before the move (3c76cf7 plus PR #28, 874ce40), so any change to a value, key or order is visible.
Browser tests check that the game's names are the module's own objects, that consumers (the start screen's
routes) work with them, and that a missing module stops the game with a message.
Run alone with: python3 -m pytest tests/test_tables.py"""
import hashlib, json, shutil, subprocess
import pytest
import game

MODULE = game.ROOT / 'src' / 'tables.js'
NAMES = ['JOBS', 'COUNTRIES']
# sha256 of JSON.stringify({JOBS,COUNTRIES}) of the original declarations (3488 characters). A deliberate change to a
# job rate or a country changes this value; check the new data (and its date, AGENTS.md rule 8), then update it.
GOLDEN = '9c450af42d50a2ce29c38152e8739b9ea058cb834f006b5c39f53f047a0c86fc'
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
    assert node('[Array.isArray(G.COUNTRIES),typeof G.JOBS]') == [True, 'object']


def test_same_content_as_before_the_move():
    out = node('G')
    assert len(json.dumps(out, ensure_ascii=False, separators=(',', ':'))) == 3488
    assert hashlib.sha256(json.dumps(out, ensure_ascii=False, separators=(',', ':')).encode('utf-8')).hexdigest() == GOLDEN


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
    expose = 'window.__G={JOBS,COUNTRIES,routesFrom,workPlace,EU_GOODS};return API;'
    body = game.hooked_html().replace('return API;', expose)
    ctx = browser.new_context(viewport={'width': 1366, 'height': 768})
    ctx.route('**/index.html', lambda route: route.fulfill(status=200, content_type='text/html; charset=utf-8', body=body))
    page = ctx.new_page()
    err = game.Errors(page)
    try:
        game.boot(page)
        assert page.evaluate("() => !!window.__G && !!document.querySelector('canvas')"), 'the city did not start'
        assert page.evaluate("() => ['JOBS','COUNTRIES'].filter(k => window.__G[k] !== window.StockholmLife.tables[k])") == []
        assert page.evaluate("() => Object.keys(window.__G.JOBS).length === 14 && window.__G.COUNTRIES.length === 51")
        # consumers read the tables: the flight routes of a country and the EU goods rule
        assert page.evaluate("() => Array.isArray(window.__G.routesFrom('Nigeria')) && window.__G.EU_GOODS('Sweden') === true && window.__G.EU_GOODS('Nigeria') === false")
        assert err.uncaught == []
        assert err.local_failures() == []
    finally:
        ctx.close()


@pytest.mark.browser
def test_missing_module_stops_with_a_message(browser):
    ctx = browser.new_context(viewport={'width': 1366, 'height': 768})
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
