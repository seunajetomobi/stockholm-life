"""src/city-data.js, the fourth module moved out of index.html (docs/MODULES.md step 4): gunzipFetch and parseHours.

The unit tests run the module in Node (seconds, no browser); gunzipFetch runs against a stubbed fetch. The
functions are the original bodies, moved unchanged, so the tests pin their behaviour, quirks included. The browser
tests check that the game uses the module's own functions and loads the city data through them, and that a
module that does not load stops the game with a message instead of a blank page.
Run alone with: python3 -m pytest tests/test_city_data.py"""
import hashlib, json, shutil, subprocess
import pytest
import game

MODULE = game.ROOT / 'src' / 'city-data.js'
NAMES = ['gunzipFetch', 'parseHours']

# parseHours over a fixed list of inputs (valid, partial, malformed, empty, non-string), as one JSON string.
DUMP_JS = r"""function dump(G){const ins=[undefined,null,'',' ','closed','24/7 closed','Mo-Fr 10:00-16:00','Mo-Fr 10:00-16:00; Sa 10:00-15:00',
  '10:00-20:00','Mo-Su 08:30-18:00','Mo,We,Fr 09:00-12:00,13:00-17:00','Sa-Mo 10:00-14:00','Fr-Mo 06:00-22:00','Mo-Fr 10:00-16:00; Sa,Su off',
  'Mo-Fr 10:00-16:00; Su closed','Mo-Fr 10:00-16:00; PH off','Mo-Fr 10:00-16:00 || "by appointment"','Mo-Fr 10:00-16:00; week 1-53 Sa 10:00-12:00',
  'Xx-Fr 10:00-16:00','Mo-Xx 10:00-16:00','Mo-Fr sunrise-sunset','Mo-Fr 9:5-17:00','Mo 7:00-9:00,16:30-18:15','mo-fr 10:00-16:00','Mo-Fr 10:00-16:00;;',
  ';','Mo-Fr','Mo-Fr 10:00-16:00;Sa 10:00-15:00;Su 12:00-16:00','Tu 24:00-26:00','We 00:00-24:00',' Mo-Fr  10:00-16:00 ; Sa 10:00-15:00 ',
  'Mo-Fr 10:00-16:00, Sa 10:00-15:00',123,['Mo-Fr 10:00-16:00']];
  const o=[];for(const s of ins){try{o.push(JSON.stringify(G.parseHours(s)))}catch(e){o.push('throws '+e.constructor.name)}}
  return JSON.stringify(o)}"""
# sha256 of dump() for the original parseHours in index.html at 3c76cf7, before it moved, and for src/city-data.js
# after the move: the move changed no output. A deliberate change to the function changes this value; check the new
# behaviour, then update it here.
GOLDEN = '5313d95fe92aae2537d448ac626cfe0620e6bd387dc8cac836cd3ceed9c32405'


def node(expr, setup=''):
    """The JSON value of a JavaScript expression evaluated in Node, with the module loaded as G."""
    exe = shutil.which('node')
    if not exe:
        pytest.skip('node is not installed')
    js = f'const G=require(process.argv[1]);{DUMP_JS}\n{setup}\n(async()=>{{process.stdout.write(JSON.stringify(await ({expr})))}})().catch(e=>{{console.error(e);process.exit(1)}})'
    r = subprocess.run([exe, '-e', js, str(MODULE)], capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


# A stubbed fetch: STUB(status, bytes-expression) answers every call and records the url.
STUB = """const URLS=[];const stub=(ok,status,make)=>{globalThis.fetch=async url=>{URLS.push(url);return {ok,status,arrayBuffer:async()=>{const b=make();return b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength)}}}};
const zlib=require('zlib');const enc=s=>new Uint8Array(Buffer.from(s));"""


def test_interface():
    assert node('Object.keys(G)') == NAMES
    assert node('Object.values(G).map(f=>typeof f)') == ['function'] * 2


def test_parse_hours_common_forms():
    assert node("G.parseHours('Mo-Fr 10:00-16:00; Sa 10:00-15:00')") == \
        {'1': [[10, 16]], '2': [[10, 16]], '3': [[10, 16]], '4': [[10, 16]], '5': [[10, 16]], '6': [[10, 15]]}
    assert node("G.parseHours('10:00-20:00')") == {str(d): [[10, 20]] for d in range(7)}   # no days: every day
    assert node("G.parseHours('Mo,We 08:30-12:00,13:00-17:15')") == {'1': [[8.5, 12], [13, 17.25]], '3': [[8.5, 12], [13, 17.25]]}
    assert node("G.parseHours('Fr-Mo 06:00-22:00')") == {str(d): [[6, 22]] for d in (5, 6, 0, 1)}   # a range wraps over the weekend
    assert node("G.parseHours('Mo-Fr 10:00-16:00; Sa,Su off')")['0'] == []   # off/closed: an empty list, not missing


def test_parse_hours_gives_up_with_null():
    for s in ['closed', 'Mo-Fr 10:00-16:00; PH off', 'Mo-Fr 10:00-16:00 || "x"', 'Mo-Fr 10:00-16:00; week 1-53 Sa 10:00-12:00',
              'Xx-Fr 10:00-16:00', 'Mo-Fr sunrise-sunset', 'Mo-Fr', '']:
        assert node(f'G.parseHours({json.dumps(s)})') is None, s
    assert node('[G.parseHours(undefined),G.parseHours(null)]') == [None, None]
    assert node("G.parseHours(' ')") == {}   # quirk kept from the original: only spaces is an empty (not missing) timetable


def test_parse_hours_same_outputs_as_before_the_move():
    out = node('dump(G)')
    assert hashlib.sha256(out.encode('utf-8')).hexdigest() == GOLDEN


def test_gunzip_fetch_plain_json():
    r = node("(async()=>{stub(true,200,()=>enc('{\"a\":[1,2,{\"b\":null}]}'));return [await G.gunzipFetch('data/x.json'),URLS]})()", STUB)
    assert r == [{'a': [1, 2, {'b': None}]}, ['data/x.json']]
    # non-ASCII text is decoded as UTF-8
    assert node("(async()=>{stub(true,200,()=>enc('{\"n\":\"Södermalm åäö\"}'));return await G.gunzipFetch('u')})()", STUB) == {'n': 'Södermalm åäö'}


def test_gunzip_fetch_gzip_json():
    setup = STUB + "const gz=s=>()=>new Uint8Array(zlib.gzipSync(Buffer.from(s)));"
    assert node("(async()=>{stub(true,200,gz('{\"a\":[1,2,3],\"s\":\"åäö\"}'));return await G.gunzipFetch('u')})()", setup) == {'a': [1, 2, 3], 's': 'åäö'}
    # the magic number decides, not the file name
    assert node("(async()=>{stub(true,200,gz('[1]'));return await G.gunzipFetch('data/plain.json')})()", setup) == [1]


def test_gunzip_fetch_errors():
    # a failed request names the url and the status
    assert node("(async()=>{stub(false,404,()=>enc(''));try{await G.gunzipFetch('data/gone.json')}catch(e){return [e.constructor.name,e.message]}})()", STUB) == ['Error', 'data/gone.json 404']
    # a browser without DecompressionStream says so
    setup = STUB + "const gz=s=>()=>new Uint8Array(zlib.gzipSync(Buffer.from(s)));"
    assert node("(async()=>{stub(true,200,gz('[1]'));const d=globalThis.DecompressionStream;delete globalThis.DecompressionStream;try{await G.gunzipFetch('u')}catch(e){return [e.constructor.name,e.message]}finally{globalThis.DecompressionStream=d}})()", setup) \
        == ['Error', 'This browser cannot unpack the map data']
    # invalid JSON throws a SyntaxError, as before; so does a truncated gzip stream (reported as a rejected promise)
    assert node("(async()=>{stub(true,200,()=>enc('{nope'));try{await G.gunzipFetch('u')}catch(e){return e.constructor.name}})()", STUB) == 'SyntaxError'
    assert node("(async()=>{stub(true,200,()=>zlib.gzipSync(Buffer.from('[1,2,3]')).subarray(0,12));try{await G.gunzipFetch('u')}catch(e){return 'rejected'}})()", STUB) == 'rejected'
    # a network failure propagates unchanged
    assert node("(async()=>{globalThis.fetch=async()=>{throw new TypeError('Failed to fetch')};try{await G.gunzipFetch('u')}catch(e){return [e.constructor.name,e.message]}})()", STUB) == ['TypeError', 'Failed to fetch']


# ---------- in the game ----------
@pytest.mark.browser
@pytest.mark.hook
def test_game_uses_the_module(browser):
    """The game script's names are the module's own functions, and the city data came through gunzipFetch."""
    expose = 'window.__C={' + ','.join(NAMES) + '};return API;'
    body = game.hooked_html().replace('return API;', expose)
    ctx = browser.new_context(viewport={'width': 1366, 'height': 768})
    ctx.route('**/index.html', lambda route: route.fulfill(status=200, content_type='text/html; charset=utf-8', body=body))
    page = ctx.new_page()
    err = game.Errors(page)
    try:
        game.boot(page)
        assert page.evaluate("() => !!window.__C && !!document.querySelector('canvas')"), 'the city did not start'
        names = json.dumps(NAMES)
        assert page.evaluate(f"() => {names}.filter(k => window.__C[k] !== window.StockholmLife['city-data'][k])") == []
        # the real data files load through the game's gunzipFetch (a gzip file and the plain JSON behind it)
        assert page.evaluate("async () => { const o = await window.__C.gunzipFetch('data/e.json'); return Object.keys(o).length > 0 }")
        assert page.evaluate("() => JSON.stringify(window.__C.parseHours('Mo-Fr 10:00-16:00'))") == json.dumps({'1': [[10, 16]], '2': [[10, 16]], '3': [[10, 16]], '4': [[10, 16]], '5': [[10, 16]]}, separators=(',', ':'))
        assert err.uncaught == []
        assert err.local_failures() == []
    finally:
        ctx.close()


@pytest.mark.browser
def test_missing_module_stops_with_a_message(browser):
    ctx = browser.new_context(viewport={'width': 1366, 'height': 768})
    ctx.route('**/src/city-data.js', lambda route: route.fulfill(status=404, content_type='text/plain', body='not found'))
    page = ctx.new_page()
    err = game.Errors(page)
    try:
        page.goto(game.BASE + '/index.html', wait_until='load', timeout=120000)
        assert game.wait_for(page, "() => (document.getElementById('loadtxt')||{}).textContent.includes('could not load src/city-data.js')", 30), \
            page.evaluate("() => (document.getElementById('loadtxt')||{}).textContent")
        assert any('src/city-data.js did not load' in e for e in err.uncaught), err.uncaught
        assert page.evaluate("() => !document.querySelector('canvas') && !document.querySelector('#modalRoot #go')"), 'the game started anyway'
    finally:
        ctx.close()
