"""Two small interface defects: the empty hover tip oval at the top-left, and the developer credit under the dock on phones."""
import pytest
import game

pytestmark = pytest.mark.browser

TIP = """() => { const e = document.querySelector('.hovertip'); if (!e) return null; const b = e.getBoundingClientRect();
  return {hidden: e.hidden, text: e.innerHTML, display: getComputedStyle(e).display, w: b.width, h: b.height} }"""
BOXES = """() => { const f = s => { const b = document.querySelector(s).getBoundingClientRect(); return [b.left, b.top, b.right, b.bottom] };
  return {credit: f('.credit'), dock: f('#dock')} }"""


def test_hovertip_is_invisible_while_empty(browser, server):
    ctx, page, err = game.new_page(browser, hook=True)
    try:
        game.boot(page)
        game.start_life(page)
        t = page.evaluate(TIP)
        assert t is not None, 'the hover tip element was not created'
        assert t['text'] == '' and t['hidden'] is True
        assert t['display'] == 'none' and t['w'] == 0 and t['h'] == 0, f'empty hover tip still has a box: {t}'
        # with text it still shows as before
        page.evaluate("() => { const e = document.querySelector('.hovertip'); e.innerHTML = '<b>Hej</b><span>test</span>'; e.hidden = false }")
        t = page.evaluate(TIP)
        assert t['display'] == 'grid' and t['w'] > 0 and t['h'] > 0
        assert err.uncaught == []
    finally:
        ctx.close()


@pytest.mark.parametrize('w,h', [(390, 844), (360, 640)], ids=['390x844', '360x640'])
def test_credit_clear_of_dock_on_phones(browser, server, w, h):
    ctx, page, err = game.new_page(browser, w, h, mobile=True, hook=True)
    try:
        game.boot(page)
        game.start_life(page, mobile=True)
        b = page.evaluate(BOXES)
        c, d = b['credit'], b['dock']
        assert c[3] <= h + 0.5, f'credit below the screen: {b}'
        assert c[1] >= d[3] - 0.5, f'credit overlaps the dock (credit {c}, dock {d})'
        assert err.uncaught == []
    finally:
        ctx.close()
