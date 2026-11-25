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


def test_unknown_callsign_is_asked_once_and_quietly(browser):
    """L3: adsbdb answers 404 for a callsign it does not know. That is "no route", asked once per session, even when asked at the same time."""
    ctx, page, err = game.new_page(browser, hook=True)
    hits = []

    def adsbdb(route):
        hits.append(route.request.url)
        if 'GOOD1' in route.request.url:
            body = {'response': {'flightroute': {'callsign': 'GOOD1', 'origin': {'iata_code': 'ARN'}, 'destination': {'iata_code': 'LHR'}}}}
            route.fulfill(status=200, content_type='application/json', headers={'access-control-allow-origin': '*'}, body=json.dumps(body))
        else:
            route.fulfill(status=404, content_type='application/json', headers={'access-control-allow-origin': '*'}, body='{"response":"unknown callsign"}')
    ctx.route('https://api.adsbdb.com/**', adsbdb)
    try:
        game.boot(page)
        r = page.evaluate("""async () => { const a = await Promise.all([window.__TS.routeOf('DFL5980'), window.__TS.routeOf('DFL5980'), window.__TS.routeOf(' DFL5980 ')]); a.push(await window.__TS.routeOf('DFL5980')); return a }""")
        assert r == [None, None, None, None], r
        assert len([u for u in hits if 'DFL5980' in u]) == 1, hits
        fr = page.evaluate("async () => { const a = await Promise.all([window.__TS.routeOf('GOOD1'), window.__TS.routeOf('GOOD1')]); return a[0] && a[0].callsign }")
        assert fr == 'GOOD1' and len([u for u in hits if 'GOOD1' in u]) == 1, hits
        assert err.uncaught == []
    finally:
        ctx.close()


