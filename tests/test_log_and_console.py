"""Small defects from KNOWN_ISSUES: L1 (diary text is escaped), L3 (one adsbdb request per unknown callsign), L11 (no THREE.Color warning)."""
import json
import pytest
import game

pytestmark = pytest.mark.browser


def start(page):
    """Start a life by clicking from the page: a busy machine can keep Playwright's own click waiting for a stable button."""
    page.evaluate("() => document.querySelector('#modalRoot #go').click()")
    assert game.wait_for(page, "() => !document.querySelector('#modalRoot #go') && window.__TS && window.__TS.S && window.__TS.S.name", 120), 'life did not start'
    game.clear_overlays(page)


NAME = '<img src=x onerror=window.__pwned=1>'


def test_diary_shows_a_name_as_text(browser):
    """L1: log text goes into the diary with innerHTML; a player's name must show as text. Escaped at render, so old saves are safe too."""
    ctx, page, err = game.new_page(browser, hook=True)
    try:
        game.boot(page)
        start(page)
        page.evaluate("""(n) => { const S = window.__TS.S; S.name = n; window.__TS.log('Hello ' + n + ' & co', 'plus'); S.log.push({d: 1, h: 8, t: 'Old save: ' + n, cls: ''}); window.__T.render() }""", NAME)
        li = page.evaluate("() => [...document.querySelectorAll('#log li span')].map(e => [e.textContent, e.querySelectorAll('*').length])")
        assert any(t == 'Hello ' + NAME + ' & co' and n == 0 for t, n in li), li
        assert any(t == 'Old save: ' + NAME and n == 0 for t, n in li), li
        assert page.evaluate("() => document.querySelectorAll('#log img').length") == 0
        assert page.evaluate("() => window.__pwned") is None
        assert page.evaluate("() => document.querySelector('#log .plus')") is not None, 'the log class is kept'
        assert err.uncaught == []
    finally:
        ctx.close()


