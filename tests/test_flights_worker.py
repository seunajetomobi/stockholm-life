"""tools/flights-worker.js (the Cloudflare Worker relay): every upstream call has its own time limit, so one slow source cannot hold
/flights until Cloudflare gives up (2026-11-25: a 502 after 28.8 s). Node only, no network: fetch is a stub, and AbortSignal.timeout is
scaled down to 20 ms so the test does not wait the real 4 and 6 seconds. The Worker is an ES module, so it is loaded through a data: URL.
Run alone with: python3 -m pytest tests/test_flights_worker.py"""
import json, os, shutil, subprocess
import pytest
import game

WORKER = game.ROOT / 'tools' / 'flights-worker.js'

HARNESS = r"""
const fs = require('fs');
const real = AbortSignal.timeout.bind(AbortSignal);
AbortSignal.timeout = () => real(20);                       // 4 s / 6 s become 20 ms
const calls = [];
// hang: never answers unless the caller gave a signal and it fires (a fetch without a time limit would wait for ever)
const hang = (url, o) => new Promise((_, rej) => { calls.push(url); if (o && o.signal) o.signal.addEventListener('abort', () => rej(o.signal.reason)); });
const ok = body => async url => { calls.push(url); return new Response(JSON.stringify(body), { status: 200 }); };
const ADSB = { now: 1700000000, ac: [{ hex: 'abc', flight: 'SAS1 ', lat: 59.6, lon: 17.9, alt_baro: 3000, gs: 200 }] };
globalThis.fetch = (url, o) => globalThis.__stub(url, o);
(async () => {
  const mod = await import('data:text/javascript;base64,' + fs.readFileSync(process.argv[1]).toString('base64'));
  const W = mod.default, out = {};
  const ask = async (path, origin, env) => { const r = await W.fetch(new Request('https://relay.test' + path, origin ? { headers: { Origin: origin } } : {}), env || {}, { waitUntil() {} });
    return { status: r.status, cors: r.headers.get('Access-Control-Allow-Origin'), vary: r.headers.get('Vary'), body: await r.text() }; };
  const race = (p, ms) => Promise.race([p, new Promise(r => setTimeout(() => r({ status: 'HUNG' }), ms))]);
  const t0 = Date.now();
  %s
  process.stdout.write(JSON.stringify(out)); process.exit(0);
})();
"""


def run(body):
    exe = shutil.which('node')
    if not exe:
        pytest.skip('node is not installed')
    r = subprocess.run([exe, '-e', HARNESS % body, str(WORKER)], capture_output=True, text=True, timeout=60, env=os.environ)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_first_source_hangs_second_answers():
    o = run("""__stub = (u, op) => u.includes('adsb.lol') ? hang(u, op) : ok(ADSB)(u);
      const r = await race(ask('/flights?debug=1', 'https://stockholmsliv.app'), 3000);
      out.status = r.status; out.ms = Date.now() - t0; out.calls = calls.length;
      out.tried = r.body && JSON.parse(r.body).tried; out.src = r.body && JSON.parse(r.body).src;""")
    assert o['status'] == 200, o
    assert o['ms'] < 2000
    assert o['src'] == 'adsb.fi'
    assert o['tried'] == ['api.adsb.lol timeout', 'opendata.adsb.fi 200']
    assert o['calls'] == 2   # the second adsb.lol URL form was skipped after the timeout


def test_normal_response_shape_and_cors():
    o = run("""__stub = ok(ADSB);
      const r = await ask('/flights', 'https://stockholmsliv.app'); const j = JSON.parse(r.body);
      out.r = [r.status, r.cors, r.vary]; out.j = [j.src, j.ac.length, j.ac[0].cs, Object.keys(j)];
      out.other = (await ask('/flights', 'https://evil.example')).cors;""")
    assert o['r'] == [200, 'https://stockholmsliv.app', 'Origin']
    assert o['j'] == ['adsb.lol', 1, 'SAS1', ['now', 'src', 'ac']]
    assert o['other'] == 'https://seunajetomobi.github.io'


def test_all_sources_fail_502():
    o = run("""__stub = (u, op) => hang(u, op);
      const r = await race(ask('/flights', 'https://stockholmsliv.app'), 3000);
      out.status = r.status; out.cors = r.cors; out.error = r.body && JSON.parse(r.body).error; out.calls = calls.length;""")
    assert o['status'] == 502 and o['cors'] == 'https://stockholmsliv.app'
    assert o['error'] == 'no ADS-B source answered'
    assert o['calls'] == 3   # one try per host: adsb.lol, adsb.fi, OpenSky
    o = run("""__stub = async () => new Response('no', { status: 500 });
      out.status = (await ask('/flights')).status;""")
    assert o['status'] == 502


def test_news_and_waittime_unchanged():
    o = run("""__stub = async () => { throw new Error('must not be called'); };
      const n = await ask('/news?src=unknown', 'https://stockholmsliv.app'); const w = await ask('/waittime?airport=ARN', 'https://stockholmsliv.app');
      out.n = [n.status, n.cors, JSON.parse(n.body).error]; out.w = [w.status, w.cors, JSON.parse(w.body).error];""")
    assert o['n'] == [502, 'https://stockholmsliv.app', 'unknown or unavailable feed']
    assert o['w'] == [503, 'https://stockholmsliv.app', 'SWEDAVIA_KEY is not set on the relay']


def test_slow_news_and_swedavia_give_up():
    o = run("""__stub = (u, op) => hang(u, op);
      const n = await race(ask('/news?src=dn'), 3000), w = await race(ask('/waittime?airport=ARN', null, { SWEDAVIA_KEY: 'k' }), 3000);
      out.n = n.status; out.w = [w.status, w.body && JSON.parse(w.body).error];""")
    assert o['n'] == 502
    assert o['w'] == [502, 'Swedavia did not answer']
