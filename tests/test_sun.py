"""src/rules/sun.js, the third module moved out of index.html (docs/MODULES.md): sunInfo, daylight, sunrise, sunset, isLight and
the WMO weather-code tables WMO, wmo and WXICON.

The unit tests run the module in Node (seconds, no browser). The date is now an argument (`sunInfo(date)`, `isLight(hour,
date)`); the game script keeps `today()` and passes it. The latitude is fixed (Stockholm, 59.33 N), so equatorial, polar-day and
polar-night conditions are not supported by this model and are not tested as such; the test below shows that the sun at this
latitude never reaches them. The expected values are a published reference with a stated tolerance, plus a hash of every
output on a fixed set of inputs that was computed once against the code BEFORE the move, so the move changed no output.
The two browser tests check that the game uses the module's own functions, and that a module that does not load stops the game
with a message instead of a blank page. Run alone with: python3 -m pytest tests/test_sun.py"""
import hashlib, json, os, shutil, subprocess
import pytest
import game

MODULE = game.ROOT / 'src' / 'rules' / 'sun.js'
NAMES = ['RAD', 'LAT', 'lastSun', 'sunInfo', 'daylight', 'sunrise', 'sunset', 'isLight', 'WMO', 'wmo', 'WXICON']

# Every output of the module on fixed inputs, as one JSON string: for 1,100 days from 2026-10-24 (the game's first day) the
# day length, solar noon, highest sun, sunrise and sunset; isLight every 7th day on a grid of hours from -1 to 25; odd dates
# (the year 2000, a leap day, the two daylight-saving days of 2024, the year 2100, an invalid date); the WMO table; and wmo and
# WXICON for codes from -2 to 101 and for strings, null, undefined, NaN and infinities.
DUMP_JS = r"""function dump(G){const o={};
  const START=new Date(2026,9,24),dateOf=n=>{const x=new Date(START);x.setDate(x.getDate()+n-1);return x};
  o.days=[];o.light=[];
  for(let n=1;n<=1100;n++){const d=dateOf(n),s=G.sunInfo(d);o.days.push([s.dl,s.noon,s.maxEl,G.daylight(d),G.sunrise(d),G.sunset(d)]);
    if(n%7===1)for(let h=-1;h<=25;h+=0.125)o.light.push(G.isLight(h,d)?1:0)}
  const odd=[new Date(2000,0,1),new Date(2024,1,29),new Date(2024,2,31),new Date(2024,9,27),new Date(2100,11,31),new Date(1999,5,21,23,59),new Date(NaN)];
  o.odd=odd.map(d=>{const s=G.sunInfo(d);return [s.dl,s.noon,s.maxEl,G.sunrise(d),G.sunset(d),G.isLight(12,d)?1:0,G.isLight(NaN,d)?1:0]});
  o.wmo=JSON.stringify(G.WMO);const codes=[];for(let c=-2;c<=101;c++)codes.push(c);codes.push('45','x',null,undefined,NaN,Infinity,-Infinity,0.5);
  o.wmoOf=codes.map(c=>G.wmo(c));o.icon=codes.map(c=>G.WXICON(c));
  return JSON.stringify(o,(k,v)=>v===undefined?'undefined':(typeof v==='number'&&!Number.isFinite(v)?String(v):v))}
"""
# sha256 of dump() for the original lines of index.html at 2cd7a9a, before they moved (run through a stub `today()`), and for
# src/rules/sun.js after the move: the move changed no output. It is the same in the time zones UTC and Europe/Stockholm. A
# deliberate change to these functions changes this value; check the new behaviour, then update it here.
GOLDEN = '2b2f0cd685ab8dfa0765c729e45aa2a4d6f706ee1f415b8457571bed4890bf7b'

# Reference: sunrise-sunset.org (https://api.sunrise-sunset.org/json?lat=59.33&lng=18.06&date=YYYY-MM-DD&formatted=0), the same
# latitude the game uses and 18.06 E. Checked 2026-11-17. Its UTC times are converted to Swedish local time of that day (CET =
# UTC+1, CEST = UTC+2) and written as decimal hours: (date, sunrise, sunset, day length from its day_length field).
# The game's formula is an approximation (a fixed -0.833 degrees, a simple declination and equation of time, 18.06 E, a
# whole-day daylight-saving switch), so the accepted tolerance is 0.17 h (10 minutes) for sunrise and sunset and 0.3 h (18
# minutes) for day length. The largest differences observed when this was written were 7.6 minutes and 14.4 minutes.
REFERENCE = [
    ('2026-03-20', 5.816, 18.025, 12.209),   # March equinox, CET
    ('2026-03-29', 6.371, 19.379, 13.008),   # the day summer time starts (CEST)
    ('2026-06-21', 3.514, 22.138, 18.624),   # June solstice, CEST
    ('2026-09-23', 6.577, 18.760, 12.183),   # September equinox, CEST
    ('2026-10-24', 7.791, 17.274, 9.483),    # the game's first day, CEST
    ('2026-10-25', 6.832, 16.229, 9.397),    # the day summer time ends (CET)
    ('2026-12-21', 8.720, 14.806, 6.086),    # December solstice, CET
]
RISE_SET_TOL, LENGTH_TOL = 0.17, 0.3


def node(expr):
    """The JSON value of a JavaScript expression evaluated in Node (time zone Europe/Stockholm), with the module loaded as G."""
    exe = shutil.which('node')
    if not exe:
        pytest.skip('node is not installed')
    js = f'const G=require(process.argv[1]);const D=(y,m,d)=>new Date(y,m-1,d);{DUMP_JS}\nprocess.stdout.write(JSON.stringify({expr}))'
    r = subprocess.run([exe, '-e', js, str(MODULE)], capture_output=True, text=True, timeout=120, env={**os.environ, 'TZ': 'Europe/Stockholm'})
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_interface():
    assert node('Object.keys(G)') == NAMES
    assert node('Object.values(G).map(v=>typeof v)') == ['number', 'number', 'function', 'function', 'function', 'function', 'function',
                                                           'function', 'object', 'function', 'function']
    assert node('[G.LAT,G.RAD]') == [59.33, 0.017453292519943295]


@pytest.mark.parametrize('day,rise,sset,length', REFERENCE)
def test_stockholm_matches_the_published_times(day, rise, sset, length):
    y, m, d = map(int, day.split('-'))
    got = node(f'[G.sunrise(D({y},{m},{d})),G.sunset(D({y},{m},{d})),G.daylight(D({y},{m},{d}))]')
    assert abs(got[0] - rise) <= RISE_SET_TOL, f'{day}: sunrise {got[0]:.3f} h, reference {rise}'
    assert abs(got[1] - sset) <= RISE_SET_TOL, f'{day}: sunset {got[1]:.3f} h, reference {sset}'
    assert abs(got[2] - length) <= LENGTH_TOL, f'{day}: day length {got[2]:.3f} h, reference {length}'


def test_seasons_at_stockholm():
    # the solstices and the equinoxes, from the formula's own constants (declination 23.44 degrees)
    jun, dec, mar = node('[G.sunInfo(D(2026,6,21)),G.sunInfo(D(2026,12,21)),G.sunInfo(D(2026,3,20))]')
    assert 18.5 < jun['dl'] < 18.7 and 6.0 < dec['dl'] < 6.2 and 11.9 < mar['dl'] < 12.15
    assert jun['maxEl'] == pytest.approx(90 - 59.33 + 23.44, abs=0.1) and dec['maxEl'] == pytest.approx(90 - 59.33 - 23.44, abs=0.1)
    assert mar['maxEl'] == pytest.approx(90 - 59.33, abs=1.0)   # 20 March is within a day of the formula's own equinox (declination -0.8 degrees)
    # the day lengthens every day from December to June and shortens every day from June to December
    up = node('Array.from({length:182},(_, i)=>G.daylight(D(2026,12,22+i)))')
    down = node('Array.from({length:182},(_, i)=>G.daylight(D(2027,6,22+i)))')
    assert all(b > a for a, b in zip(up, up[1:])) and all(b < a for a, b in zip(down, down[1:]))
    # at this latitude the sun always rises and sets, so the polar-day and polar-night branch (the clamp) is never reached
    dl = node('(()=>{const a=[];for(let n=0;n<7305;n++)a.push(G.daylight(new Date(2026,0,1+n)));return [Math.min(...a),Math.max(...a)]})()')
    assert 5.9 < dl[0] and dl[1] < 18.7


def test_summer_time_moves_solar_noon_by_an_hour():
    # the game switches the whole day on the last Sundays of March and October (2026-03-29 and 2026-10-25)
    a, b, c, d = node('[G.sunInfo(D(2026,3,28)).noon,G.sunInfo(D(2026,3,29)).noon,G.sunInfo(D(2026,10,24)).noon,G.sunInfo(D(2026,10,25)).noon]')
    assert b - a == pytest.approx(1, abs=0.05) and d - c == pytest.approx(-1, abs=0.05)


def test_is_light():
    assert node('[G.isLight(12,D(2026,6,21)),G.isLight(2,D(2026,6,21)),G.isLight(23,D(2026,6,21))]') == [True, False, False]
    assert node('[G.isLight(8,D(2026,12,21)),G.isLight(9,D(2026,12,21)),G.isLight(15,D(2026,12,21))]') == [False, True, False]
    # the limits belong to the day (>= and <=), and the next representable hour outside them does not
    assert node('(()=>{const d=D(2026,10,24),r=G.sunrise(d),s=G.sunset(d);return [G.isLight(r,d),G.isLight(r-1e-9,d),G.isLight(s,d),G.isLight(s+1e-9,d)]})()') \
        == [True, False, True, False]
    # hours outside 0..24 are not wrapped; nothing but a number between the limits is light
    assert node('[G.isLight(-1,D(2026,6,21)),G.isLight(25,D(2026,6,21)),G.isLight(NaN,D(2026,6,21)),G.isLight(undefined,D(2026,6,21))]') == [False] * 4


def test_invalid_input_as_the_original():
    # quirks kept from the original: an invalid date gives NaN (JSON null) everywhere, and a missing date throws
    assert node('(()=>{const s=G.sunInfo(new Date(NaN));return [s.dl,s.noon,s.maxEl,G.sunrise(new Date(NaN)),G.isLight(12,new Date(NaN))]})()') == [None, None, None, None, False]
    assert node('(()=>{try{G.sunInfo(undefined)}catch(e){return e.constructor.name}})()') == 'TypeError'


def test_wmo_tables():
    t = node('G.WMO')
    assert len(t) == 28 and t['0'] == ['Clear sky', 'clear'] and t['45'] == ['Fog', 'cloud'] and t['61'] == ['Light rain', 'rain']
    assert t['71'] == ['Light snow', 'snow'] and t['95'] == ['Thunderstorm', 'rain'] and t['99'] == ['Thunderstorm with hail', 'rain']
    assert t['56'] == t['57'] == ['Freezing drizzle', 'rain'] and t['66'] == t['67'] == ['Freezing rain', 'rain']
    assert {v[1] for v in t.values()} == {'clear', 'cloud', 'rain', 'snow'}
    assert node('[G.wmo(63),G.wmo(1000),G.wmo(-1),G.wmo("45"),G.wmo(undefined),G.wmo(null)]') \
        == [['Rain', 'rain'], ['Unknown', 'cloud'], ['Unknown', 'cloud'], ['Fog', 'cloud'], ['Unknown', 'cloud'], ['Unknown', 'cloud']]
    # the icon: sun to code 1, partly cloudy 2, cloud 3, fog up to 48 (any code), then by the class of the code; 95 and up is a storm
    assert node('[0,1,2,3,10,45,48,51,63,71,77,85,95,99].map(G.WXICON)') == ['\u2600', '\u2600', '\u26c5', '\u2601', '\U0001f32b', '\U0001f32b', '\U0001f32b',
                                                                          '\U0001f327', '\U0001f327', '\u2744', '\u2744', '\u2744', '\u26c8', '\u26c8']
    assert node('G.WXICON(60)') == '\U0001f327'   # quirk kept: an unknown code above 48 shows rain


def test_same_outputs_as_before_the_move():
    out = node('dump(G)')
    assert hashlib.sha256(out.encode('utf-8')).hexdigest() == GOLDEN


def test_needs_the_format_module():
    """Loaded without src/util/format.js (it needs clamp), the module stops with a message that names the file."""
    exe = shutil.which('node')
    if not exe:
        pytest.skip('node is not installed')
    js = "const vm=require('vm'),fs=require('fs');try{vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{})}catch(e){process.stdout.write(e.message)}"
    r = subprocess.run([exe, '-e', js, str(MODULE)], capture_output=True, text=True, timeout=60)
    assert r.stdout == 'src/rules/sun.js needs src/util/format.js loaded first', (r.stdout, r.stderr)


# ---------- in the game ----------
@pytest.mark.browser
@pytest.mark.hook
def test_game_uses_the_module(browser):
    """The game's wmo and WXICON are the module's own functions, its sun functions give the module's answers for the game's date,
    the city starts, and the module adds no name to the page but its own."""
    expose = 'window.__F={sunInfo,daylight,sunrise,sunset,isLight,wmo,WXICON,today};return API;'
    body = game.hooked_html().replace('return API;', expose)
    ctx = browser.new_context(viewport={'width': 1366, 'height': 768})
    ctx.route('**/index.html', lambda route: route.fulfill(status=200, content_type='text/html; charset=utf-8', body=body))
    page = ctx.new_page()
    err = game.Errors(page)
    try:
        game.boot(page)
        assert page.evaluate("() => !!window.__F && !!document.querySelector('canvas')"), 'the city did not start'
        assert page.evaluate("() => window.__F.wmo === window.StockholmLife.sun.wmo && window.__F.WXICON === window.StockholmLife.sun.WXICON")
        same = page.evaluate("""() => { const F = window.__F, M = window.StockholmLife.sun, d = F.today(), bad = [];
            if (JSON.stringify(F.sunInfo()) !== JSON.stringify(M.sunInfo(d))) bad.push('sunInfo');
            if (F.daylight() !== M.daylight(d)) bad.push('daylight');
            if (F.sunrise() !== M.sunrise(d) || F.sunset() !== M.sunset(d)) bad.push('sunrise/sunset');
            for (let h = -1; h <= 25; h += 0.25) if (F.isLight(h) !== M.isLight(h, d)) bad.push('isLight ' + h);
            return bad }""")
        assert same == [], same
        assert sorted(page.evaluate("() => Object.keys(window.StockholmLife)")) == ['city-data', 'format', 'geography', 'stockholm-time', 'sun', 'tables']
        assert page.evaluate("() => ['SUN','sunInfo','sunrise','sunset','isLight','daylight','wmo','WMO','WXICON','RAD','LAT','lastSun'].filter(k => k in window)") == []
        assert err.uncaught == []
        assert err.local_failures() == []
    finally:
        ctx.close()


@pytest.mark.browser
def test_missing_module_stops_with_a_message(browser):
    ctx = browser.new_context(viewport={'width': 1366, 'height': 768})
    ctx.route('**/src/rules/sun.js', lambda route: route.fulfill(status=404, content_type='text/plain', body='not found'))
    page = ctx.new_page()
    err = game.Errors(page)
    try:
        page.goto(game.BASE + '/index.html', wait_until='load', timeout=120000)
        assert game.wait_for(page, "() => (document.getElementById('loadtxt')||{}).textContent.includes('could not load src/rules/sun.js')", 30), \
            page.evaluate("() => (document.getElementById('loadtxt')||{}).textContent")
        assert any('src/rules/sun.js did not load' in e for e in err.uncaught), err.uncaught
        assert page.evaluate("() => !document.querySelector('canvas') && !document.querySelector('#modalRoot #go')"), 'the game started anyway'
    finally:
        ctx.close()
