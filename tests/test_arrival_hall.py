"""The Arlanda arrivals hall: layout, people, uniforms, trolleys, kerb, and the popups on every screen size."""
import game
import pytest

SIZES = {'laptop': (1366, 768, False), 'tablet': (820, 1180, True), 'phone': (390, 780, True)}
HUD = {'board': '#board', 'next': '#next', 'places': '#places', 'inhud': '#inhud', 'guide': '#apguide', 'prompt': '#inAct', 'dock': '#dock', 'joy': '#joy', 'run': '#runbtn',
       'ctrls': '.ctrls', 'toast': '.toast', 'care': '.carechip', 'sos': '.sos112'}
ALL_SIZES = {'desktop': (1920, 1080, False), 'laptop': (1366, 768, False), 'tablet-land': (1024, 768, True), 'tablet': (820, 1180, True), 'phone': (390, 780, True), 'small-phone': (360, 640, True)}


def hud_overlaps(page):
    b = game.boxes(page, HUD)
    keys = sorted(b)
    return [(x, y, round(game.overlap(b[x], b[y]))) for i, x in enumerate(keys) for y in keys[i + 1:] if game.overlap(b[x], b[y]) > 4]


# Instead of fixed sleeps (Codex and code review, 2026-11-25): wait until the game has drawn at least `frames` frames,
# and, after a move, has redrawn the hall's guide once (apDraw, every second of game time), so the move has reached the
# HUD; then every HUD box (and, for screenshots, the camera) must stay the same for three frames in a row.
SETTLE = """([sel, frames, redraw, cam]) => new Promise(done => { const W = window.__TS.W, d0 = W.apDrawn(); let last = '', same = 0, n = 0;
  const f = () => { n++; const s = JSON.stringify([Object.values(sel).map(q => [...document.querySelectorAll(q)].map(e => {
      const r = e.getBoundingClientRect(); return [r.x, r.y, r.width, r.height].map(Math.round) })),
      cam ? W.camAt().map(v => Math.round(v * 1000)) : 0]);
    same = s === last ? same + 1 : 0; last = s;
    const ready = n >= frames && (!redraw || W.apDrawn() > d0) && same >= 3;
    if (ready || n > 900) done(ready); else requestAnimationFrame(f) };
  requestAnimationFrame(f) })"""


def settle(page, frames=6, redraw=True, camera=False):
    assert page.evaluate(SETTLE, [HUD, frames, redraw, camera]), 'the hall did not settle within 900 frames'


def _arrive(page, schengen=False, mobile=False):
    game.start_life(page, mobile=mobile)
    page.evaluate("""(sch) => { const S = window.__TS.S; S.flags.arlanda = 1; S.flags.passport = 0; S.flags.bags = 0; S.flags.customs = 0;
        S.schengen = sch; S.euFlight = sch; S.fromGroup = sch ? 'eu' : 'noneu'; S.lastLeg = sch ? 'Copenhagen' : 'Doha'; delete S.arrFlight;
        window.__TS.W.enterAirport() }""", schengen)
    assert game.wait_for(page, "() => document.body.classList.contains('arr') && window.__TS.W.apVeh().length >= 10", 60), 'the arrivals hall did not open'
    game.clear_overlays(page)
    settle(page)


@pytest.mark.parametrize('size', list(SIZES))
def test_hall_looks_right(browser, server, size):
    w, h, mob = SIZES[size]
    ctx, page, err = game.new_page(browser, width=w, height=h, mobile=mob, hook=True)
    try:
        game.boot(page)
        _arrive(page, mobile=mob)
        game.shot(page, f'arr-{size}-start')
        if size == 'laptop':
            for name, z in [('passport', -0.55), ('belt', -0.05), ('customs', 0.12), ('hall', 0.36), ('kerb', 0.49)]:
                page.evaluate("(z) => { window.__TS.W.avSet(0.05, z) }", z)
                settle(page, camera=True)
                game.shot(page, f'arr-{size}-{name}')
        assert err.uncaught == [], err.uncaught
    finally:
        ctx.close()


@pytest.mark.parametrize('size', list(ALL_SIZES))
def test_popups_never_overlap(browser, server, size):
    w, h, mob = ALL_SIZES[size]
    ctx, page, err = game.new_page(browser, width=w, height=h, mobile=mob, hook=True)
    try:
        game.boot(page)
        _arrive(page, mobile=mob)
        bad = {}
        for step, (x, z) in {'start': (0, -0.73), 'gate': (0, -0.55), 'belt': (0.05, 0.0), 'customs': (-0.3, 0.12), 'kerb': (0, 0.45)}.items():
            page.evaluate("([x, z]) => window.__TS.W.avSet(x, z)", [x, z])
            settle(page)
            for open_ in (False, True):
                page.evaluate("(o) => { const g = document.getElementById('apguide'); if (g && g.classList.contains('open') !== o) g.querySelector('.apmain').click() }", open_)
                settle(page, frames=2, redraw=False)
                o = hud_overlaps(page)
                if o:
                    bad[f'{step}/{"open" if open_ else "closed"}'] = o
                    game.shot(page, f'overlap-{size}-{step}-{"open" if open_ else "closed"}')
        assert not bad, bad
        assert err.uncaught == [], err.uncaught
    finally:
        ctx.close()


def test_vehicles_keep_their_lane_and_never_overlap(browser, server):
    """Coaches, taxis and cars outside the arrivals hall stay in two lanes and keep a gap to the vehicle ahead (10 minutes of simulated traffic)."""
    ctx, page, err = game.new_page(browser, hook=True)
    page.set_default_timeout(90000)
    try:
        game.boot(page)
        _arrive(page, mobile=False)
        # code review 2026-11-25: stalls 0.14 apart left two 0.125-long taxis 0.015 short of apAhead's gap, so an arriving
        # vehicle stopped short of its stall and waited there; neighbouring stalls must leave room for both and the gap
        kerb = sorted((v['stall'], v['len']) for v in page.evaluate("() => window.__TS.W.apVeh()") if v['stall'] is not None)
        tight = [(a, b) for (a, la), (b, lb) in zip(kerb, kerb[1:]) if b - a < (la + lb) / 2 + 0.03 - 1e-9]
        assert len(kerb) == 7 and not tight, f'stalls too close for two vehicles and their gap: {tight}'
        # the spawn case directly, before the random traffic below (two timers ending in the same tick put two vehicles at the same entry point before apClear)
        p = page.evaluate("() => window.__TS.W.apSpawnPair()")
        assert p['live'] == 1, f'exactly one of two vehicles may enter at the same spot in the same tick: {p}'
        r = page.evaluate("() => window.__TS.W.apVehSim(6000)")
        assert not r['bad'], r['bad'][:5]
        assert r['lanes'] <= 2, r
        assert r['moved'] >= 5, r
        assert r['big'], 'coaches should be large'
        assert err.uncaught == [], err.uncaught
    finally:
        ctx.close()


def test_a_trolley_comes_from_a_rack_and_goes_back_to_one(browser, server):
    """Codex review, 2026-11-25: returning a trolley only took it off the player. Taking one takes it off that rack; returning
    puts it on the rack where it is returned (here the other one); an empty rack says so."""
    ctx, page, err = game.new_page(browser, hook=True)
    page.set_default_timeout(90000)
    try:
        game.boot(page)
        _arrive(page, mobile=False)
        racks = lambda: page.evaluate("() => window.__TS.W.apRacks()")
        assert racks() == {'-0.46': 5, '0.46': 5}, racks()
        assert page.evaluate("() => window.__TS.W.apTrolleyAt(-0.46)") is True
        assert racks() == {'-0.46': 4, '0.46': 5}, racks()
        assert page.evaluate("() => window.__TS.W.apTrolleyAt(0.46)") is False
        assert racks() == {'-0.46': 4, '0.46': 6}, racks()
        for _ in range(4):
            assert page.evaluate("() => window.__TS.W.apTrolleyAt(-0.46)") is True
            page.evaluate("() => window.__TS.W.apTrolleyAt(0.46)")
        assert racks() == {'-0.46': 0, '0.46': 10}, racks()
        assert page.evaluate("() => window.__TS.W.apTrolleyAt(-0.46)") is False, 'an empty rack gives no trolley'
        assert err.uncaught == [], err.uncaught
    finally:
        ctx.close()


def test_hall_rules_leave_stations_alone(browser, server):
    """Regression (feat/arrival-hall 2fc936c): scoping the arrivals-hall layout to the hall also rewrote main's phone rule
    that hides the places bar, Next up, the hint and the care chip inside every building and station. On a phone in
    Stockholm Central they must stay hidden, as on main."""
    ctx, page, err = game.new_page(browser, 390, 844, mobile=True, hook=True)
    try:
        game.boot(page)
        if game.intro_shown(page):
            game.start_life(page, mobile=True)
        game.enter_station(page)
        game.clear_overlays(page)
        shown = page.evaluate("""() => [...document.querySelectorAll('.next,.places,#hint,.hint,.carechip')]
            .filter(e => getComputedStyle(e).display !== 'none').map(e => e.id || e.className)""")
        assert page.evaluate("() => document.body.classList.contains('inside')"), 'the station did not set body.inside'
        assert shown == [], f'shown on a phone inside the station: {shown}'
        assert err.uncaught == [], err.uncaught
    finally:
        ctx.close()
