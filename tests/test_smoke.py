"""Smoke test on desktop (1366x768): boot, start a life, dock tabs, every phone app, the places bar.
Ported from the audit's smoke.py and smoke2.py. The tests in this file share one page and run in order."""
import time
import pytest
import game
from game import clear_overlays, modal_text

pytestmark = pytest.mark.browser


@pytest.fixture(scope='module')
def desk(browser):
    ctx, page, err = game.new_page(browser, 1366, 768)
    d = {'page': page, 'err': err, 'load': game.boot(page)}
    yield d
    ctx.close()
    if err.console or err.external_failures():  # shown with -s or in the -rA summary of a failure
        print('\nconsole errors:', err.console[:10], '\nexternal request failures:', err.external_failures()[:10])


def test_boot(desk):
    page, err = desk['page'], desk['err']
    assert page.evaluate("() => !!document.querySelector('canvas')"), 'no WebGL canvas'
    assert page.evaluate("() => document.querySelectorAll('.nogl').length") == 0, 'a no-WebGL / no-data message is shown'
    assert game.intro_shown(page), 'character creation not shown on a fresh profile'
    assert err.uncaught == []
    assert err.local_failures() == [], 'a game file failed to load'
    game.shot(page, 'smoke-1-loaded')
    print(f"loaded in {desk['load']} s")


def test_start_life_writes_save(desk):
    page = desk['page']
    game.start_life(page)
    s = game.saved(page)
    assert s, 'no save written after starting a life'
    assert s.get('name') and s.get('bg') == 'local', s and {k: s.get(k) for k in ('name', 'bg')}
    assert not game.intro_shown(page)
    assert desk['err'].uncaught == []
    game.shot(page, 'smoke-2-started')


@pytest.mark.parametrize('tab', ['here', 'phone', 'me', 'civic', 'diary'])
def test_dock_tab(desk, tab):
    page = desk['page']
    page.evaluate(f"() => document.querySelector('#dock button[data-tab={tab}]').click()")
    time.sleep(0.6)
    n = page.evaluate("() => { const p = document.querySelector('.pane:not([hidden])'); return p ? p.innerText.length : -1 }")
    assert n > 0, f'tab {tab} renders nothing'
    assert desk['err'].uncaught == []


def test_every_phone_app_opens(desk):
    """Click every tile on the phone (through the DOM, so a random incoming call cannot block the click)."""
    page, err = desk['page'], desk['err']
    clear_overlays(page)
    page.evaluate("() => document.querySelector('#dock button[data-tab=phone]').click()")
    time.sleep(0.5)
    labels = page.evaluate("() => [...document.querySelectorAll('#apps > *')].map(e => (e.innerText || e.getAttribute('aria-label') || '').trim().replace(/\\n/g, ' '))")
    assert len(labels) >= 39, f'expected at least 39 phone apps (as of 742403b), found {len(labels)}'
    broken = []
    for i, lab in enumerate(labels):
        e0 = len(err.uncaught)
        page.evaluate(f"() => document.querySelectorAll('#apps > *')[{i}].click()")
        time.sleep(1.5)
        if err.uncaught[e0:]:
            broken.append((lab, err.uncaught[e0:]))
        clear_overlays(page)
    assert broken == []
    game.shot(page, 'smoke-3-phone')


def test_places_bar(desk):
    """Every button on the places bar responds without errors; Centralen opens its travel card."""
    page, err = desk['page'], desk['err']
    labels = page.evaluate("() => [...document.querySelectorAll('#places button')].map(e => (e.innerText || e.getAttribute('aria-label') || '').trim())")
    assert labels, 'no places bar'
    for i, lab in enumerate(labels):
        e0 = len(err.uncaught)
        page.evaluate(f"() => document.querySelectorAll('#places button')[{i}].click()")
        time.sleep(2)
        txt = modal_text(page)
        assert err.uncaught[e0:] == [], lab
        if lab.lower().startswith('centralen'):
            assert 'STOCKHOLM CENTRAL' in txt.upper(), f'Centralen travel card not shown: {txt!r}'
        clear_overlays(page)
        time.sleep(0.5)
