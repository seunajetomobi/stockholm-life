"""Rides on SL's own boats from a pier: pendelbåt 80 and Djurgårdsfärjan 82; båt 89 is not offered, its piers are beyond the city map (which piers offer which line, the boat's path on the line, and the journey: fare, ride, arrival).

The same journey code as buses and trams (`pickBusStop`, `busRide`, `busTick`); the bus and tram tests in test_transit_rides.py pin that code for them.
Not offered: the Waxholmsbolaget, cruise, canal and Finland ferries (not commuter boats), and the Ressel, Movitz and Sjöstadstrafiken lines (not SL).
Run alone with: python3 -m pytest tests/test_boat_rides.py"""
import re, time
import pytest
import game

EXPOSE = 'window.__V={pickBusStop,poiActions,TICKET,TRANSIT,busTick,ridePath,rideShift,inWater,get rideState(){return rideState}};return API;'
LIFE = {'money': 1000, 'hour': 11, 'day': 3, 'mood': 50, 'slUntil': 0}   # day 3 is a Monday


@pytest.fixture(scope='module')
def city(browser):
    body = game.hooked_html().replace('return API;', EXPOSE)
    ctx = game.new_context(browser, viewport={'width': 1366, 'height': 768})
    ctx.route('**/index.html', lambda route: route.fulfill(status=200, content_type='text/html; charset=utf-8', body=body))
    page = ctx.new_page()
    err = game.Errors(page)
    game.boot(page, timeout=240)
    game.start_life(page)
    game.clear_overlays(page)
    yield page
    ctx.close()
    assert err.uncaught == []


# every ferry terminal of the city data with the boat lines it offers
PIERS = """() => { const W = window.__TS.W, V = window.__V, out = {piers: [], bad: [], other: []};
  for (let i = 0; i < 200000; i++) { const p = W.poi(i); if (!p) break; if (p.type !== 'ferry_terminal') continue;
    const L = W.transitLinesAt(p.x, p.z, ['ferry']); if (W.busLinesAt(p.x, p.z).length) out.other.push([i, p.name]);
    for (const l of L) { const R = V.TRANSIT[l.i], ds = l.next.map(n => n.d), names = l.next.map(n => n.name);
      if (R.m !== 'ferry' || l.m !== 'ferry' || R.look.kind !== 'SL boat' || !/^8[024]?$|^89$/.test(l.ref) || !l.next.length || ds.some((d, k) => k && d <= ds[k-1]) || ds[0] <= l.d0 + 0.2
          || ds.some(d => d > R.L) || new Set(names).size !== names.length || names.includes(p.name)) out.bad.push([i, p.name, l.ref, l.dest]) }
    if (L.length) out.piers.push([i, p.name, L.map(l => [l.ref, l.dest, l.next.map(n => n.name)])]) }
  return out }"""


@pytest.mark.browser
@pytest.mark.hook
def test_boat_lines_at_piers(city):
    r = city.evaluate(PIERS)
    assert r['bad'] == [] and r['other'] == [], r
    by = {}
    for _, name, lines in r['piers']:
        for ref, dest, nxt in lines:
            by.setdefault(ref, []).append((name, dest, nxt))
    assert set(by) == {'80', '82'}, sorted(by)   # no Waxholm, cruise, canal or other boats; båt 89's piers are beyond the city map
    assert len(r['piers']) >= 18, len(r['piers'])
    # pendelbåt 80 from Nybroplan to Ropsten: its piers in order, and the line's end is a pier too
    nyb = next(l for n, d, l in by['80'] if n == 'Nybroplan' and d == 'Ropsten')
    assert nyb == ['Allmänna gränd', 'Saltsjöqvarn', 'Finnboda hamn', 'Kvarnholmen', 'Blockhusudden', 'Nacka strand', 'Lidingö/Dalénum', 'Frihamnen', 'Ropsten'], nyb
    assert ('Ropsten', 'Nybroplan') in [(n, d) for n, d, _ in by['80']]   # from the end of a line
    # the loop lines from Ropsten are named by their last pier, not by Ropsten (where they end too)
    assert not any(n == 'Ropsten' and d == 'Ropsten' for n, d, _ in by['80']), by['80']
    assert any(n == 'Slussen' and d == 'Djurgården' for n, d, _ in by['82'])


@pytest.mark.browser
@pytest.mark.hook
def test_boat_actions_at_piers(city):
    r = city.evaluate("""() => { const W = window.__TS.W, V = window.__V, out = {};
      for (const name of ['Nybroplan', 'Ropsten', 'Slussen', 'Viking Line: Stadsgården, Stockholm']) {
        for (let i = 0; i < 200000; i++) { const p = W.poi(i); if (!p) break; if (p.type !== 'ferry_terminal' || p.name !== name) continue;
          const a = V.poiActions(p).map(x => x.l).filter(l => /^(Take boat|No )/.test(l)); if (a.length || name.startsWith('Viking')) { out[name] = a; break } } }
      return out }""")
    assert all(re.fullmatch(r'Take boat (80|82) towards \S.*', a) and '  ' not in a for n in ('Nybroplan', 'Ropsten', 'Slussen') for a in r[n]), r
    assert 'Take boat 80 towards Ropsten' in r['Nybroplan'] and 'Take boat 80 towards Nybroplan' in r['Ropsten'], r
    assert {'Take boat 80 towards Mor Annas brygga', 'Take boat 80 towards Storholmen norra'} <= set(r['Ropsten']), r   # the two loop lines are named by their last pier
    assert 'Take boat 82 towards Djurgården' in r['Slussen'], r
    assert r['Viking Line: Stadsgården, Stockholm'] == [], r   # the Finland ferries are not commuter boats


@pytest.mark.browser
@pytest.mark.hook
def test_boat_path_on_route_and_water(city):
    """A boat journey runs on the route line (no shift), a point every 0.04 units; every ride the game offers is on water (no stretch of land longer than 30 m); the rides
    are on lines 80 and 82. Båt 89 is not offered: the city map has no water west of Lilla Essingen, where its piers are."""
    r = city.evaluate("""() => { const V = window.__V, out = [];
      const dist = (R, q) => { let best = 1e9; for (let i = 1; i < R.pts.length; i++) { const ax = R.pts[i-1][0], az = R.pts[i-1][1], dx = R.pts[i][0] - ax, dz = R.pts[i][1] - az, L2 = dx*dx + dz*dz || 1e-9;
          let t = ((q.x - ax) * dx + (q.z - az) * dz) / L2; t = t < 0 ? 0 : t > 1 ? 1 : t; best = Math.min(best, Math.hypot(ax + dx * t - q.x, az + dz * t - q.z)) } return best };
      for (const R of V.TRANSIT) { if (R.m !== 'ferry' || R.look.kind !== 'SL boat') continue;
        const pts = V.ridePath(R, 0, R.L); let worst = 0, wet = 0, step = 0;
        for (const q of pts) worst = Math.max(worst, dist(R, {x: q.x, z: q.z}))
        for (let k = 1; k < pts.length; k++) step = Math.max(step, pts[k].distanceTo(pts[k-1]));
        out.push({ref: R.r.ref, name: R.r.name, n: pts.length, worst, step, shift: V.rideShift(R)}) }
      const rides = {n: 0, refs: new Set(), run: 0, wet: 1, dry: []};
      for (let i = 0; i < 200000; i++) { const p = window.__TS.W.poi(i); if (!p) break; if (p.type !== 'ferry_terminal') continue;
        for (const l of window.__TS.W.transitLinesAt(p.x, p.z, ['ferry'])) for (const n of l.next) { const R = V.TRANSIT[l.i], pts = V.ridePath(R, Math.max(0, l.d0 - 1.4), n.d);
          let run = 0, longest = 0, wet = 0; for (const q of pts) { if (V.inWater(q.x, q.z)) { run = 0; wet++ } else longest = Math.max(longest, ++run) }
          rides.n++; rides.refs.add(l.ref); rides.run = Math.max(rides.run, longest); rides.wet = Math.min(rides.wet, wet / pts.length); if (longest > 15) rides.dry.push([p.name, l.ref, n.name, longest]) } }
      return {routes: out, rides: {...rides, refs: [...rides.refs]}} }""")
    assert len(r['routes']) == 10 and {x['ref'] for x in r['routes']} == {'80', '82', '89'}, r
    for x in r['routes']:
        assert x['shift'] == 0 and x['worst'] < 1e-5 and x['step'] <= 0.0401 and x['n'] > 100, x
    rd = r['rides']
    assert rd['n'] > 100 and sorted(rd['refs']) == ['80', '82'] and rd['run'] <= 16 and rd['wet'] > 0.95 and rd['dry'] == [], rd


def journey(page, name, ref, dest, pick, setup, midcheck=None):
    """Start a journey the way the game does (pickBusStop(line), then the destination `pick`: 'first' or 'last'), step busTick until it ends."""
    st = page.evaluate("""([name, ref, dest, pick, setup]) => { const T = window.__TS, W = T.W, V = window.__V, S = T.S;
      let found = null;
      for (let i = 0; i < 200000 && !found; i++) { const p = W.poi(i); if (!p) break; if (p.type !== 'ferry_terminal' || p.name !== name) continue;
        const L = W.transitLinesAt(p.x, p.z, ['ferry']).find(l => l.ref === ref && l.dest === dest); if (L) found = [p, L] }
      if (!found) return {err: 'no such line at that pier'};
      const [p, L] = found; Object.assign(S, setup.life); S.flags.snow = false;
      W.placeAvatar(p.x, p.z, true); S.pos = {x: p.x, z: p.z};
      const before = {money: S.money, hour: S.hour, mood: S.mood, log: S.log.length};
      V.pickBusStop(L);
      const k = pick === 'last' ? L.next.length - 1 : 0, to = L.next[k], km = (to.d - L.d0) * 0.05, min = km / 20 * 60 + 4;
      if (setup.dodge) { const c = document.querySelector('#modalRoot #dodge'); if (!c) return {err: 'no fare-dodge box'}; c.checked = true }
      const note = document.querySelector('#modalRoot .note').innerText;
      document.querySelector(`#modalRoot .choice[data-i="${k}"]`).click();
      const chip = document.getElementById('ride').innerText;
      return {before, chip, note, n: L.next.length, L: {ref: L.ref, kind: L.kind, dest: L.dest}, to: {name: to.name, x: to.x, z: to.z}, min, hasCard: S.slUntil >= S.day, ticket: V.TICKET} }""",
                      [name, ref, dest, pick, setup])
    assert 'err' not in st, st
    assert game.wait_for(page, "() => window.__TS.busy === true", 20), 'the journey did not start'
    if midcheck:
        midcheck(st)
    # a frame of the test browser takes a second or so and the game caps one at 0.05 s: step the game's own busTick instead
    steps = page.evaluate("() => { let n = 0; while (window.__TS.busy && n < 20000) { window.__V.busTick(0.05); n++ } return n }")
    assert 20 < steps < 20000, f'the journey took {steps} steps'
    time.sleep(0.5)
    return st, page.evaluate("() => { const T = window.__TS, S = T.S; return {busy: T.busy, money: S.money, hour: S.hour, mood: S.mood, log: S.log.slice(0, 3).map(l => l.t), at: T.W.avPos()} }")


def boat_midcheck(page):
    def check(st):
        assert st['L']['kind'] in st['chip'] and 'waiting at the stop' in st['chip'], st['chip']
        assert 'Boats in SL' in st['note'], st['note']
        r = page.evaluate("""() => { const B = window.__V.rideState; window.__boat = B.g; window.__stops = B.stops;
          let n = 0; B.g.traverse(o => { if (o.isMesh) n++ });
          return {ins: B.g.parent === window.__T.scene, boat: B.g.userData.boat === 1, meshes: n, cars: B.cars.length, mode: B.R.m, sorted: B.stops.every((d, k) => !k || d > B.stops[k-1])} }""")
        assert r['ins'] and r['boat'] and r['meshes'] > 0 and r['cars'] == 0 and r['mode'] == 'ferry' and r['sorted'], r
    return check


CASES = [('Nybroplan', '80', 'Ropsten', 'first'), ('Nybroplan', '80', 'Ropsten', 'last'),   # the last is nine piers on
         ('Slussen', '82', 'Djurgården', 'last')]                                        # the Djurgården ferry


@pytest.mark.browser
@pytest.mark.hook
@pytest.mark.parametrize('name,ref,dest,pick', CASES)
def test_boat_journey_fare_time_arrival(city, name, ref, dest, pick):
    """A complete boat journey: the ticket, the time, the log, arrival at the destination pier, and the boat gone afterwards; then an SL card and fare dodging."""
    st, fin = journey(city, name, ref, dest, pick, {'life': LIFE}, boat_midcheck(city))
    assert st['L']['kind'] == 'SL boat' and not st['hasCard'] and fin['money'] == 1000 - st['ticket'], (st, fin)
    assert fin['hour'] == pytest.approx(11 + st['min'] / 60, abs=0.02) and fin['mood'] == 50, fin
    assert re.search(rf"SL boat {ref} to {re.escape(st['to']['name'])}, .*\({st['ticket']} kr\)\.$", fin['log'][0]), fin['log']
    assert abs(fin['at']['x'] - st['to']['x']) < 0.6 and abs(fin['at']['z'] - st['to']['z']) < 0.6, (fin['at'], st['to'])
    assert city.evaluate("() => window.__V.rideState === null && window.__boat.parent === null && document.getElementById('ride').style.display === 'none'"), 'the boat was left in the scene'
    if pick == 'last':
        st, fin = journey(city, name, ref, dest, pick, {'life': {**LIFE, 'hour': 8, 'slUntil': 9}})
        assert st['hasCard'] and fin['money'] == 1000 and fin['mood'] == 49, (st, fin)
        st, fin = journey(city, name, ref, dest, pick, {'life': LIFE, 'dodge': True})
        assert fin['money'] == 1000 and 'without a ticket' in fin['log'][0], (st, fin)


@pytest.mark.browser
@pytest.mark.hook
def test_boat_calls_at_every_pier(city):
    """The boat calls at each pier between the start and the destination, in order, and the destination is the last stop of the ride."""
    st, _ = journey(city, 'Nybroplan', '80', 'Ropsten', 'last', {'life': LIFE}, lambda st: city.evaluate("""() => { const B = window.__V.rideState;
      window.__calls = {n: B.stops.length, len: B.len, first: B.stops[0], last: B.stops[B.stops.length - 1]} }"""))
    c = city.evaluate("() => window.__calls")
    # the start, eight piers between (Allmänna gränd to Frihamnen) and the end: Ropsten is the 9th pier after Nybroplan
    assert c['n'] == 10 and c['first'] < c['last'] and abs(c['last'] - c['len']) < 1e-9, c
