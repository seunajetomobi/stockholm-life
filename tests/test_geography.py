"""src/geography.js, the first module moved out of index.html (docs/MODULES.md): the map projection, the districts,
the T-bana and tram stations, the lines and route finding.

The unit tests run the module in Node (seconds, no browser). The two browser tests check that the game uses the
module's own objects, and that a module that does not load stops the game with a message instead of a blank page.
Run alone with: python3 -m pytest tests/test_geography.py"""
import hashlib, importlib.util, json, shutil, subprocess
import pytest
import game

MODULE = game.ROOT / 'src' / 'geography.js'
NAMES = ['O_LAT', 'O_LON', 'P', 'PP', 'WATER_FALLBACK', 'AREAS', 'HUB_R', 'ST', 'STP', 'LINES', 'transitRoute', 'nearestStation']

# Every output of the module on a fixed set of inputs, as one JSON string: the projection on a grid over the map,
# the data tables, routes between every pair of stations (plus names that are not stations) and the nearest
# station on a grid of points.
DUMP_JS = r"""function dump(G){const o={};
  o.consts=[G.O_LAT,G.O_LON,G.HUB_R];
  o.P=[];for(let la=59.20;la<=59.48;la+=0.01)for(let lo=17.80;lo<=18.25;lo+=0.01)o.P.push(G.P(la,lo));
  o.PP=G.PP([[59.33,18.06],[59.4,17.9]]);
  o.water=G.WATER_FALLBACK;o.areas=G.AREAS;o.ST=G.ST;o.STP=G.STP;o.lines=G.LINES;
  const names=Object.keys(G.ST).concat(['kista','tc','','Nowhere']);
  o.routes=[];for(const a of names)for(const b of names)o.routes.push([a,b,G.transitRoute(a,b)]);
  o.near=[];for(let x=-400;x<=400;x+=7)for(let z=-400;z<=400;z+=7)o.near.push(G.nearestStation(x,z));
  return JSON.stringify(o)}"""
# sha256 of dump() for the GEOGRAPHY section of index.html at 3eb5711, before it moved, and for src/geography.js
# after the move: the move changed no output. A deliberate change to the geography data or rules changes this
# value; check the new behaviour, then update it here.
GOLDEN = 'f3fdbd22fc7f2d7cf01ac90ce40b4792b241d51f421f119c38cbc1003c6965e3'


def node(expr):
    """The JSON value of a JavaScript expression evaluated in Node, with the module loaded as G."""
    exe = shutil.which('node')
    if not exe:
        pytest.skip('node is not installed')
    js = f'const G=require(process.argv[1]);{DUMP_JS}\nprocess.stdout.write(JSON.stringify({expr}))'
    r = subprocess.run([exe, '-e', js, str(MODULE)], capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_interface():
    assert node('Object.keys(G)') == NAMES
    assert node("['P','PP','transitRoute','nearestStation'].map(k=>typeof G[k])") == ['function'] * 4


def test_projection():
    """1 unit = 50 m, origin T-Centralen, x east, z south (AGENTS.md), the same as the tool that builds data/e.json."""
    assert node('G.P(G.O_LAT,G.O_LON)') == [0, 0]
    north, east = node('[G.P(G.O_LAT+50/111320,G.O_LON),G.P(G.O_LAT,G.O_LON+50/56817)]')
    assert north[0] == 0 and north[1] == pytest.approx(-1)
    assert east[0] == pytest.approx(1) and east[1] == 0
    spec = importlib.util.spec_from_file_location('osm_stations', game.ROOT / 'tools' / 'osm_stations.py')
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    points = [[59.3313, 18.0603], [59.4032, 17.9443], [59.3143, 18.0735], [59.2991, 18.0809]]
    for (lat, lon), xz in zip(points, node(f'{json.dumps(points)}.map(([a,b])=>G.P(a,b))')):
        assert xz == pytest.approx(list(tool.P(lat, lon)), abs=1e-9)


def test_districts_stations_and_lines():
    bad = node("""(()=>{const e=[];
      for(const k in G.AREAS){const a=G.AREAS[k],[x,z]=G.P(...a.ll);if(!G.ST[a.st])e.push(k+': station '+a.st);if(a.x!==x||a.z!==z)e.push(k+': position')}
      if(Object.keys(G.STP).join()!==Object.keys(G.ST).join())e.push('STP keys');
      for(const k in G.ST){const [x,z]=G.P(...G.ST[k]);if(G.STP[k][0]!==x||G.STP[k][1]!==z)e.push(k+': STP')}
      for(const L of G.LINES)for(const s of L.seq)if(!G.ST[s])e.push(L.id+': '+s);
      if(new Set(G.LINES.map(L=>L.id)).size!==G.LINES.length)e.push('line ids');
      return e})()""")
    assert bad == []


def test_routes():
    def route(a, b):
        return node(f"(r=>r&&{{min:r.min,legs:r.legs.map(l=>[l.line.id,l.stops[0],l.stops[l.stops.length-1]]),"
                    f"stations:r.stations.length,sameLines:r.legs.every(l=>G.LINES.includes(l.line))}})(G.transitRoute({json.dumps(a)},{json.dumps(b)}))")
    assert route('Kista', 'T-Centralen') == {'min': 16, 'legs': [['B11', 'Kista', 'T-Centralen']], 'stations': 9, 'sameLines': True}
    assert route('Rinkeby', 'Odenplan') == {'min': 24, 'legs': [['B10', 'Rinkeby', 'Fridhemsplan'], ['G', 'Fridhemsplan', 'Odenplan']], 'stations': 11, 'sameLines': True}
    assert route('Kista', 'Skansen') == {'min': 34, 'legs': [['B11', 'Kista', 'Kungsträdgården'], ['T7', 'Kungsträdgården', 'Skansen']], 'stations': 14, 'sameLines': True}
    assert route('Kista', 'Kista') == {'min': 0, 'legs': [], 'stations': 1, 'sameLines': True}
    assert route('kista', 'Kista') is None  # district keys are not station names
    # every station reaches every other, in the same time both ways
    assert node("""(()=>{const s=Object.keys(G.ST),e=[];for(const a of s)for(const b of s){const r=G.transitRoute(a,b),q=G.transitRoute(b,a);
      if(!r||!q||r.min!==q.min)e.push(a+'-'+b)}return e})()""") == []


def test_nearest_station():
    assert node("Object.keys(G.STP).filter(k=>{const n=G.nearestStation(...G.STP[k]);return n.name!==k||n.d!==0})") == []
    assert node("G.nearestStation(0,0)") == {'name': 'T-Centralen', 'd': 0}


def test_same_outputs_as_before_the_move():
    out = node('dump(G)')
    assert hashlib.sha256(out.encode('utf-8')).hexdigest() == GOLDEN


# ---------- in the game ----------
@pytest.mark.browser
@pytest.mark.hook
def test_game_uses_the_module(browser):
    """The game script's names are the module's own objects, not copies, and the city starts with them."""
    expose = 'window.__G={' + ','.join(NAMES + ['D']) + '};return API;'
    body = game.hooked_html().replace('return API;', expose)
    ctx = browser.new_context(viewport={'width': 1366, 'height': 768})
    ctx.route('**/index.html', lambda route: route.fulfill(status=200, content_type='text/html; charset=utf-8', body=body))
    page = ctx.new_page()
    err = game.Errors(page)
    try:
        game.boot(page)
        assert page.evaluate("() => !!window.__G && !!document.querySelector('canvas')"), 'the city did not start'
        names = json.dumps(NAMES)
        assert page.evaluate(f"() => {names}.filter(k => window.__G[k] !== window.StockholmLife.geography[k])") == []
        assert page.evaluate("() => window.__G.D === window.StockholmLife.geography.AREAS")
        assert err.uncaught == []
        assert err.local_failures() == []
    finally:
        ctx.close()


@pytest.mark.browser
def test_missing_module_stops_with_a_message(browser):
    ctx = browser.new_context(viewport={'width': 1366, 'height': 768})
    ctx.route('**/src/geography.js', lambda route: route.fulfill(status=404, content_type='text/plain', body='not found'))
    page = ctx.new_page()
    err = game.Errors(page)
    try:
        page.goto(game.BASE + '/index.html', wait_until='load', timeout=120000)
        assert game.wait_for(page, "() => (document.getElementById('loadtxt')||{}).textContent.includes('could not load src/geography.js')", 30), \
            page.evaluate("() => (document.getElementById('loadtxt')||{}).textContent")
        assert any('src/geography.js did not load' in e for e in err.uncaught), err.uncaught
        assert page.evaluate("() => !document.querySelector('canvas') && !document.querySelector('#modalRoot #go')"), 'the game started anyway'
    finally:
        ctx.close()
