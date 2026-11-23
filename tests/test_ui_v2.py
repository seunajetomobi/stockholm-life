"""Interface v2: the playing screen keeps its zones and nothing on it overlaps, on a phone, a tablet and a computer."""
import time
import pytest
import game

SIZES = {'desktop': (1920, 1080, False), 'laptop': (1366, 768, False), 'tablet': (820, 1180, True), 'phone': (390, 780, True), 'small-phone': (360, 640, True)}
HUD = {'clock': '.b-time', 'where': '.b-where', 'money': '.b-money', 'next': '#next', 'places': '#places', 'needs': '#needs', 'ctrls': '.ctrls', 'joy': '#joy', 'run': '#runbtn', 'dock': '#dock'}


def overlaps(page):
    b = game.boxes(page, HUD)
    keys = sorted(b)
    return [(x, y, round(game.overlap(b[x], b[y]))) for i, x in enumerate(keys) for y in keys[i + 1:] if game.overlap(b[x], b[y]) > 4]


@pytest.mark.parametrize('size', list(SIZES))
def test_playing_screen_zones_never_overlap(browser, server, size):
    w, h, mob = SIZES[size]
    ctx, page, err = game.new_page(browser, width=w, height=h, mobile=mob)
    try:
        game.boot(page)
        game.start_life(page, mobile=mob)
        game.shot(page, f'ui2-{size}')
        assert overlaps(page) == []
        for tab in ('here', 'me'):
            page.click(f'#dock [data-tab={tab}]'); time.sleep(1.2)
            game.shot(page, f'ui2-{size}-{tab}')
            page.click('#dclose'); time.sleep(0.5)
        assert game.overflow_x(page) == 0
        assert err.uncaught == [], err.uncaught
    finally:
        ctx.close()
