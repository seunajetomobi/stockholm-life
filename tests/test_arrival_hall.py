"""The Arlanda arrivals hall: layout, people, uniforms, trolleys, kerb, and the popups on every screen size."""
import time
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



def _arrive(page, schengen=False, mobile=False):
    game.start_life(page, mobile=mobile)
    page.evaluate("""(sch) => { const S = window.__TS.S; S.flags.arlanda = 1; S.flags.passport = 0; S.flags.bags = 0; S.flags.customs = 0;
        S.schengen = sch; S.euFlight = sch; S.fromGroup = sch ? 'eu' : 'noneu'; S.lastLeg = sch ? 'Copenhagen' : 'Doha'; delete S.arrFlight;
        window.__TS.W.enterAirport() }""", schengen)
    time.sleep(3)
    game.clear_overlays(page)


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
                time.sleep(2.5)
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
            page.evaluate("([x, z]) => window.__TS.W.avSet(x, z)", [x, z]); time.sleep(1.5)
            for open_ in (False, True):
                page.evaluate("(o) => { const g = document.getElementById('apguide'); if (g && g.classList.contains('open') !== o) g.querySelector('.apmain').click() }", open_)
                time.sleep(0.4)
                o = hud_overlaps(page)
                if o:
                    bad[f'{step}/{"open" if open_ else "closed"}'] = o
                    game.shot(page, f'overlap-{size}-{step}-{"open" if open_ else "closed"}')
        assert not bad, bad
        assert err.uncaught == [], err.uncaught
    finally:
        ctx.close()


def test_vehicles_keep_their_lane_and_never_overlap(browser, server):
    """Coaches, taxis and cars outside the arrivals hall stay in two lanes and keep a gap to the vehicle ahead."""
    ctx, page, err = game.new_page(browser, hook=True)
    page.set_default_timeout(90000)
    try:
        game.boot(page)
        _arrive(page, mobile=False)
        page.evaluate("() => window.__TS.W.avSet(0, 0.49)")
        seen_move = set()
        last = None
        for _ in range(90):
            time.sleep(1)
            vs = page.evaluate("() => window.__TS.W.apVeh()")
            lanes = {}
            for i, v in enumerate(vs):
                if v['mode'] == 'gone':
                    continue
                lanes.setdefault(round(v['z'], 3), []).append(v)
                if last and abs(last[i]['x'] - v['x']) > 0.002:
                    seen_move.add(i)
            assert len(lanes) <= 2, ('more than two lanes', list(lanes))
            for z, row in lanes.items():
                row.sort(key=lambda v: v['x'])
                for a, b in zip(row, row[1:]):
                    assert b['x'] - a['x'] >= (a['len'] + b['len']) / 2 - 0.002, ('vehicles overlap', a, b)
            last = vs
        assert any(v['len'] > 0.3 for v in vs), 'coaches should be large'
        assert seen_move, 'no vehicle moved in 90 s'
        assert err.uncaught == [], err.uncaught
    finally:
        ctx.close()
