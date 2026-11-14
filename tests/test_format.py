"""src/util/format.js, the second module moved out of index.html (docs/MODULES.md): clamp, kr, hhmm and fmtDur.

The unit tests run the module in Node (seconds, no browser). Several expected values below are quirks of the
original code (a rounding that reads "60 min", "−0 kr"); the move kept them, and the tests pin them so that a
later "fix" is a visible, deliberate change. The two browser tests check that the game uses the module's own
functions, and that a module that does not load stops the game with a message instead of a blank page.
Run alone with: python3 -m pytest tests/test_format.py"""
import hashlib, json, shutil, subprocess
import pytest
import game

MODULE = game.ROOT / 'src' / 'util' / 'format.js'
NAMES = ['clamp', 'kr', 'hhmm', 'fmtDur']

# Every output of the module on fixed inputs, as one JSON string: clamp over limits including reversed and
# infinite ones, kr over rounding halves, negatives, large amounts and a fine grid, hhmm from -50 h to 50 h
# in steps of 0.01 h, fmtDur from 0 to 2000 minutes in steps of 0.1, and NaN and infinities for each.
DUMP_JS = r"""function dump(G){const o={};
  const S=x=>Object.is(x,-0)?'-0':String(x);
  const vals=[-5,0,3,10,15,NaN,Infinity,-Infinity];
  o.clamp=[];for(const v of vals.concat([-0.5,2.5,7.5]))for(const a of [0,3,-Infinity])for(const b of [10,3,0,Infinity])o.clamp.push(S(G.clamp(v,a,b)));
  const ks=[0,-0,0.4,-0.4,0.5,-0.5,0.6,-0.6,1.5,-1.5,999,999.5,1000,-1000,1234567,-1234567,1e12,NaN,Infinity,-Infinity];
  for(let n=-5000;n<=5000;n+=0.37)ks.push(n);for(let n=-3e6;n<=3e6;n+=12345.6)ks.push(n);
  o.kr=ks.map(n=>G.kr(n));
  const hs=[NaN,Infinity,-Infinity,23.999,23.99,24,-1,25.5,0,-0];for(let h=-50;h<=50;h+=0.01)hs.push(h);
  o.hhmm=hs.map(h=>G.hhmm(h));
  const ms=[NaN,Infinity,-Infinity,-5,0,0.2,59.5,59.4,60,119.6,59.99];for(let m=0;m<=2000;m+=0.1)ms.push(m);
  o.fmtDur=ms.map(m=>G.fmtDur(m));
  return JSON.stringify(o)}"""
# sha256 of dump() for the four lines of index.html at 3eb5711, before they moved, and for src/util/format.js
# after the move: the move changed no output. A deliberate change to these functions changes this value; check
# the new behaviour, then update it here.
GOLDEN = '3f9aa5f26f63726d28ad81cef3eda4b90b06f81976b7d93a13d32f48e20e7d4a'


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
    assert node('Object.values(G).map(f=>typeof f)') == ['function'] * 4


def test_clamp():
    assert node('[G.clamp(5,0,3),G.clamp(-1,0,3),G.clamp(1.5,0,3),G.clamp(3,0,3),G.clamp(0,0,3)]') == [3, 0, 1.5, 3, 0]
    assert node('G.clamp(1,3,0)') == 3                      # reversed limits: the lower limit wins, as in the original
    assert node('G.clamp(NaN,0,3)') is None                 # NaN stays NaN (JSON null)
    assert node('[G.clamp(9,-Infinity,Infinity),G.clamp(-9,0,Infinity)]') == [9, 0]


def test_kr_money():
    assert node('G.kr(-1234567)') == '−1 234 567 kr'   # a real minus sign (U+2212), a space between thousands
    assert node('[G.kr(0),G.kr(999),G.kr(1000),G.kr(1234.5),G.kr(0.5),G.kr(1.4)]') == ['0 kr', '999 kr', '1 000 kr', '1 235 kr', '1 kr', '1 kr']
    # quirks kept from the original: a small negative amount rounds to zero but keeps the sign, and halves round
    # towards +infinity (Math.round): -0.5 gives "−0 kr" and -1.5 gives "−1 kr", while 0.5 and 1.5 give 1 and 2
    assert node('[G.kr(-0.4),G.kr(-0.5),G.kr(-1.5),G.kr(1.5)]') == ['−0 kr', '−0 kr', '−1 kr', '2 kr']
    assert node('G.kr(1e12)') == '1 000 000 000 000 kr'


def test_hhmm_wraps_at_24():
    assert node('[G.hhmm(0),G.hhmm(8.25),G.hhmm(12.5),G.hhmm(23.5)]') == ['00:00', '08:15', '12:30', '23:30']
    assert node('[G.hhmm(24),G.hhmm(25.5),G.hhmm(48),G.hhmm(-1),G.hhmm(-25.5)]') == ['00:00', '01:30', '00:00', '23:00', '22:30']
    assert node('[G.hhmm(23.999),G.hhmm(7.9999)]') == ['00:00', '08:00']   # minutes round up to 60: carry into the hour, wrap at 24


def test_fmtdur_rounds_as_the_original():
    assert node('[G.fmtDur(0.2),G.fmtDur(1),G.fmtDur(45),G.fmtDur(59.4)]') == ['1 min', '1 min', '45 min', '59 min']
    assert node('[G.fmtDur(60),G.fmtDur(125),G.fmtDur(600),G.fmtDur(61)]') == ['1 h 00 min', '2 h 05 min', '10 h 00 min', '1 h 01 min']
    # quirks kept from the original: 59.5 rounds to "60 min" (not "1 h 00 min"), 119.6 to "1 h 60 min"
    assert node('[G.fmtDur(59.5),G.fmtDur(119.6)]') == ['60 min', '1 h 60 min']


def test_same_outputs_as_before_the_move():
    out = node('dump(G)')
    assert hashlib.sha256(out.encode('utf-8')).hexdigest() == GOLDEN


# ---------- in the game ----------
@pytest.mark.browser
@pytest.mark.hook
def test_game_uses_the_module(browser):
    """The game script's names are the module's own functions, not copies, and the city starts with them."""
    expose = 'window.__F={' + ','.join(NAMES) + '};return API;'
    body = game.hooked_html().replace('return API;', expose)
    ctx = browser.new_context(viewport={'width': 1366, 'height': 768})
    ctx.route('**/index.html', lambda route: route.fulfill(status=200, content_type='text/html; charset=utf-8', body=body))
    page = ctx.new_page()
    err = game.Errors(page)
    try:
        game.boot(page)
        assert page.evaluate("() => !!window.__F && !!document.querySelector('canvas')"), 'the city did not start'
        names = json.dumps(NAMES)
        assert page.evaluate(f"() => {names}.filter(k => window.__F[k] !== window.StockholmLife.format[k])") == []
        assert page.evaluate("() => window.__F.kr(-1234) === '\\u22121 234 kr' && window.__F.hhmm(25.5) === '01:30'")
        assert err.uncaught == []
        assert err.local_failures() == []
    finally:
        ctx.close()


@pytest.mark.browser
def test_missing_module_stops_with_a_message(browser):
    ctx = browser.new_context(viewport={'width': 1366, 'height': 768})
    ctx.route('**/src/util/format.js', lambda route: route.fulfill(status=404, content_type='text/plain', body='not found'))
    page = ctx.new_page()
    err = game.Errors(page)
    try:
        page.goto(game.BASE + '/index.html', wait_until='load', timeout=120000)
        assert game.wait_for(page, "() => (document.getElementById('loadtxt')||{}).textContent.includes('could not load src/util/format.js')", 30), \
            page.evaluate("() => (document.getElementById('loadtxt')||{}).textContent")
        assert any('src/util/format.js did not load' in e for e in err.uncaught), err.uncaught
        assert page.evaluate("() => !document.querySelector('canvas') && !document.querySelector('#modalRoot #go')"), 'the game started anyway'
    finally:
        ctx.close()
