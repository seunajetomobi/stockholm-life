"""Vehicles stay on the road: buses are moved over to the kerb side of their route line inside the street, not out of it onto the pavement.

The route line of a bus comes from the route data and can run close to the edge of the carriageway. The game used to move every bus a fixed
distance to the kerb side of that line (half way to the edge on a two-way street), so where the line already hugged the edge the bus ended up
outside the street (measured in Vasastan: a bus 3.7 m outside the carriageway, on the pavement). The shift is now capped at the depth the
line has inside the carriageway, less the bus's half width (`busKerb`, `BUS_HALF` in index.html).

test_bus_keeps_inside_the_street is geometry on the loaded city, without randomness: it walks the bus routes near a place where the old rule put
a bus outside, applies the game's rule and checks the result, and it shows that the old rule (the uncapped shift) does leave the street there.
test_traffic_stays_on_carriageways is a guard: cars driving on the ordinary road classes (4 to 9) stay inside the carriageway. Neither test changes
anything in the game. Run alone with: python3 -m pytest tests/test_vehicle_lanes.py"""
import time
import pytest
import game

# a place in Vasastan (world units, 1 unit = 50 m) where a bus route line runs along the edge of a carriageway
SPOT = (-11.37, -25.59)
EXPOSE = 'window.__V={busKerb,roadDepth,TRANSIT,agents,get G(){return G}};return API;'

# every bus route line within 8 units of the spot, in steps of 0.02 units (1 m): the shift the game would apply, and where that puts the bus
WALK = """([sx, sz]) => { const V = window.__V, out = {points: 0, inside: 0, newOut: [], oldOut: [], routes: 0};
  for (const R of V.TRANSIT) { if (R.m !== 'bus') continue; const P = R.pts; let used = false;
    for (let i = 1; i < P.length; i++) { const ax = P[i-1][0], az = P[i-1][1], bx = P[i][0], bz = P[i][1], L = Math.hypot(bx - ax, bz - az); if (L < 1e-6) continue;
      const dx = (bx - ax) / L, dz = (bz - az) / L;
      for (let s = 0; s < L; s += 0.02) { const x = ax + dx * s, z = az + dz * s; if (Math.hypot(x - sx, z - sz) > 8) continue;
        const k = V.busKerb(x, z), pre = V.roadDepth(x, z)[0]; if (!k || pre < 0) continue; used = true; out.points++;
        const post = (o) => V.roadDepth(x - dz * o, z + dx * o)[0];
        if (post(Math.min(k.lo, k.cap)) < 0) out.newOut.push([x, z, k.lo, k.cap]);
        if (post(k.lo) < 0) out.oldOut.push([x, z, k.lo]) } }
    if (used) out.routes++ }
  return out }"""

CARS = """() => { const V = window.__V, out = []; for (const a of V.agents) { if (a.kind !== 'car' || !a.g.visible || a.e < 0) continue;
  const cls = V.G.E[a.e][2]; if (cls < 4 || cls > 9) continue; const r = V.roadDepth(a.g.position.x, a.g.position.z);
  if (!r[1]) continue;   // no road data here yet (the tile is not built): nothing to compare with
  out.push([cls, r[0], a.v || 0]) } return out }"""


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
    page.evaluate("([x, z]) => window.__TS.W.placeAvatar(x, z, true)", list(SPOT))
    assert game.wait_for(page, f"() => window.__V && window.__V.roadDepth({SPOT[0]}, {SPOT[1]})[1] !== null", 120), 'the streets around the spot did not load'
    time.sleep(3)
    yield page
    ctx.close()
    assert err.uncaught == []


@pytest.mark.browser
@pytest.mark.hook
def test_bus_keeps_inside_the_street(city):
    r = city.evaluate(WALK, list(SPOT))
    assert r['points'] > 200 and r['routes'] >= 1, f'too few bus route points near the spot to mean anything: {r["points"]} on {r["routes"]} routes'
    assert r['newOut'] == [], f'with the cap, a bus is still moved out of the street at {r["newOut"][:3]}'
    # the old rule really did put a bus outside the street here (otherwise this test would not notice it coming back)
    assert len(r['oldOut']) >= 5, f'the uncapped shift stays inside the street at this spot: {len(r["oldOut"])} points; choose another spot'


@pytest.mark.browser
@pytest.mark.hook
def test_traffic_stays_on_carriageways(city):
    seen = []
    for _ in range(8):
        seen += city.evaluate(CARS)
        time.sleep(1.5)
    assert len(seen) >= 8 and any(v > 0.01 for _, _, v in seen), f'no moving cars to check: {len(seen)} samples'
    out = [s for s in seen if s[1] < 0]
    assert out == [], f'cars on road classes 4 to 9 outside the carriageway: {out[:5]}'
