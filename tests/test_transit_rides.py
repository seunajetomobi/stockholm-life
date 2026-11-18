"""Rides on SL buses and trams from a stop: which lines a stop offers, and the journey itself (the fare, the ride, the arrival).

The bus tests were written first, against the code before trams were added, and pin what a bus journey does today (the lines at a
sample of real bus stops as a hash, and the money, time, mood, log and arrival of three complete journeys), so that adding trams
did not change it. The tram tests check the same things for trams on the real route data.
The names exposed to the tests come from `window.__V` (added here with the test hook, like the other hooked tests).
Run alone with: python3 -m pytest tests/test_transit_rides.py"""
import hashlib, json, re, time
import pytest
import game

EXPOSE = 'window.__V={pickBusStop,poiActions,TICKET,TRANSIT,busTick};return API;'

# every 7th bus stop of the city data, in data order: the lines the game offers there (route index, number, destination, colour, kind,
# where the stop is on the route, and the next stops with their positions), as one JSON string
BUS_LINES = """() => { const W = window.__TS.W, out = []; let k = 0;
  for (let i = 0; i < 200000; i++) { const p = W.poi(i); if (!p) break; if (p.type !== 'bus_stop') continue; if (k++ % 7) continue;
    out.push([i, W.busLinesAt(p.x, p.z).map(l => [l.i, l.ref, l.dest, l.col, l.kind, Math.round(l.d0 * 1e6), l.next.map(n => [n.name, Math.round(n.d * 1e6)])])]) }
  return JSON.stringify(out) }"""
# sha256 of that string for the code before trams (main 4b2e88a)
BUS_LINES_GOLDEN = 'e39c2f5c68fb4d253a9f7348fdadf349355fd0b63f25fcecab7708e6de522115'   # 371 stops


@pytest.fixture(scope='module')
def city(browser):
    body = game.hooked_html().replace('return API;', EXPOSE)
    ctx = browser.new_context(viewport={'width': 1366, 'height': 768})
    ctx.route('**/index.html', lambda route: route.fulfill(status=200, content_type='text/html; charset=utf-8', body=body))
    page = ctx.new_page()
    err = game.Errors(page)
    game.boot(page, timeout=240)
    game.start_life(page)
    game.clear_overlays(page)
    yield page
    ctx.close()
    assert err.uncaught == []


@pytest.mark.browser
@pytest.mark.hook
def test_bus_lines_at_stops_unchanged(city):
    out = city.evaluate(BUS_LINES)
    n = len(json.loads(out))
    got = hashlib.sha256(out.encode('utf-8')).hexdigest()
    assert n > 300 and sum(1 for s in json.loads(out) if s[1]) > 100, f'too few bus stops with lines: {n}'
    assert got == BUS_LINES_GOLDEN


# ---------- a complete journey ----------
# the first stop with lines that has at least three stops after it: [poi index, line index in the list]
FIND_STOP = """(type) => { const W = window.__TS.W, mode = type === 'tram_stop' ? 'tram' : 'bus';
  for (let i = 0; i < 200000; i++) { const p = W.poi(i); if (!p) break; if (p.type !== type) continue;
    const L = mode === 'tram' ? W.transitLinesAt(p.x, p.z, ['tram']) : W.busLinesAt(p.x, p.z);
    for (let j = 0; j < L.length; j++) if (L[j].next.length >= 3) return [i, j] } return null }"""
# start a journey the way the game does: pickBusStop(line), then the first destination in the list; returns what the game showed
START = """([pi, j, type, setup]) => { const T = window.__TS, W = T.W, V = window.__V, S = T.S, p = W.poi(pi);
  Object.assign(S, setup.life); S.flags.snow = false;
  const mode = type === 'tram_stop' ? 'tram' : 'bus';
  const L = (mode === 'tram' ? W.transitLinesAt(p.x, p.z, ['tram']) : W.busLinesAt(p.x, p.z))[j];
  W.placeAvatar(p.x, p.z, true); S.pos = {x: p.x, z: p.z};
  const before = {money: S.money, hour: S.hour, mood: S.mood, log: S.log.length};
  V.pickBusStop(L);
  const to = L.next[0], km = (to.d - L.d0) * 0.05, min = km / 20 * 60 + 4;
  if (setup.dodge) { const c = document.querySelector('#modalRoot #dodge'); if (!c) return {err: 'no fare-dodge box'}; c.checked = true }
  document.querySelector('#modalRoot .choice[data-i="0"]').click();
  return {before, L: {ref: L.ref, kind: L.kind, dest: L.dest}, to: {name: to.name, x: to.x, z: to.z}, min, hasCard: S.slUntil >= S.day, ticket: V.TICKET} }"""
FINISH = """() => { const T = window.__TS, S = T.S, W = T.W; return {busy: T.busy, money: S.money, hour: S.hour, mood: S.mood, log: S.log.slice(0, 3).map(l => l.t), at: W.avPos(), pos: S.pos} }"""


def journey(page, type, setup):
    found = page.evaluate(FIND_STOP, type)
    assert found, f'no {type} with lines and three stops after it'
    st = page.evaluate(START, [found[0], found[1], type, setup])
    assert 'err' not in st, st
    assert game.wait_for(page, "() => window.__TS.busy === true", 20), 'the journey did not start'
    # the test browser draws a frame a second or less, and the game caps a frame at 0.05 s, so a journey would take minutes of real time:
    # step the game's own busTick instead, 0.05 s at a time (what 20 frames a second would do), until the journey ends
    steps = page.evaluate("() => { let n = 0; while (window.__TS.busy && n < 8000) { window.__V.busTick(0.05); n++ } return n }")
    assert 20 < steps < 8000, f'the journey took {steps} steps'
    time.sleep(0.5)
    return st, page.evaluate(FINISH)


LIFE = {'money': 1000, 'hour': 11, 'day': 3, 'mood': 50, 'slUntil': 0}   # day 3 is a Monday (the game starts on Saturday 24 Oct)


@pytest.mark.browser
@pytest.mark.hook
def test_bus_journey_fare_time_arrival(city):
    """A bus journey: ticket paid, SL card (no fare), rush hour costs mood, fare dodging; the time, the log and the arrival at the stop."""
    # 1. no card, outside rush hour: the ticket is paid, no mood change
    st, fin = journey(city, 'bus_stop', {'life': LIFE})
    assert not st['hasCard'] and fin['money'] == 1000 - st['ticket'], (st, fin)
    assert fin['hour'] == pytest.approx(11 + st['min'] / 60, abs=0.02) and fin['mood'] == 50, fin
    assert re.search(rf"{re.escape(st['L']['kind'])} {st['L']['ref']} to {re.escape(st['to']['name'])}, .*\({st['ticket']} kr\)\.$", fin['log'][0]), fin['log']
    assert abs(fin['at']['x'] - st['to']['x']) < 0.6 and abs(fin['at']['z'] - st['to']['z']) < 0.6, (fin['at'], st['to'])
    # 2. an SL card, in rush hour (Monday 08:00): no fare, and one point of mood is lost
    st, fin = journey(city, 'bus_stop', {'life': {**LIFE, 'hour': 8, 'slUntil': 9}})
    assert st['hasCard'] and fin['money'] == 1000 and fin['mood'] == 49 and 'kr)' not in fin['log'][0], (st, fin)
    # 3. fare dodging: nothing is paid, and the log says so
    st, fin = journey(city, 'bus_stop', {'life': LIFE, 'dodge': True})
    assert fin['money'] == 1000 and 'without a ticket' in fin['log'][0], (st, fin)
