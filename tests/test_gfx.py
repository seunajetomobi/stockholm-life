"""Image effects on the High preset (index.html, GFX: SMAA anti-aliasing and a night-time bloom; docs/GFX.md).
High builds the effects from three.js r128 add-ons loaded on demand; Low loads nothing; a failed download keeps the plain
look and the game running."""
import pytest
import game

FX_URL = '/npm/three@0.128.0/examples/js/postprocessing/'
HIGH = "try{localStorage.setItem('sl-quality','high');localStorage.setItem('sl-quality-auto','1')}catch(e){}"  # no automatic switch to Fast
LOW = "try{localStorage.setItem('sl-quality','low')}catch(e){}"
STATE = "() => window.__TS.W.gfxState()"


def _start(page):
    game.boot(page)
    if game.intro_shown(page):
        game.start_life(page)


def test_high_builds_the_effects_and_the_glow_follows_the_night(browser, server):
    ctx, page, err = game.new_page(browser, hook=True, gfx=True, init_script=HIGH)
    page.set_default_timeout(120000)
    try:
        _start(page)
        st = page.evaluate(STATE)
        if not st['webgl2']:
            pytest.skip('this browser has no WebGL 2; the effects are off by design')
        assert game.wait_for(page, "() => window.__TS.W.gfxState().ready", 90), page.evaluate(STATE)
        st = page.evaluate(STATE)
        assert st['on'] and st['failed'] == '', st
        assert page.evaluate("() => typeof THREE.EffectComposer === 'function' && typeof THREE.SMAAPass === 'function'")
        page.evaluate("() => { window.__TS.S.hour = 12 }")
        assert game.wait_for(page, "() => window.__TS.W.gfxState().strength < 0.05", 60), page.evaluate(STATE)
        game.shot(page, 'gfx-high-day')
        page.evaluate("() => { window.__TS.S.hour = 23.5 }")
        assert game.wait_for(page, "() => window.__TS.W.gfxState().strength > 0.3", 60), page.evaluate(STATE)
        game.shot(page, 'gfx-high-night')
        assert err.uncaught == [], err.uncaught
    finally:
        ctx.close()


def test_low_loads_no_effects(browser, server):
    ctx, page, err = game.new_page(browser, hook=True, gfx=True, init_script=LOW)
    asked = []
    page.on('request', lambda r: asked.append(r.url) if FX_URL in r.url else None)
    page.set_default_timeout(120000)
    try:
        _start(page)
        page.wait_for_timeout(3000)
        st = page.evaluate(STATE)
        assert not st['on'] and not st['ready'], st
        assert asked == [], asked
        assert page.evaluate("() => typeof THREE.EffectComposer") == 'undefined'
        assert err.uncaught == [], err.uncaught
    finally:
        ctx.close()


def test_turned_off_by_the_setting(browser, server):
    ctx, page, err = game.new_page(browser, hook=True, gfx=False, init_script=HIGH)
    page.set_default_timeout(120000)
    try:
        _start(page)
        page.wait_for_timeout(3000)
        st = page.evaluate(STATE)
        assert not st['on'] and not st['ready'], st
        assert err.uncaught == [], err.uncaught
    finally:
        ctx.close()


def test_a_failed_download_keeps_the_plain_look(browser, server):
    ctx, page, err = game.new_page(browser, hook=True, gfx=True, init_script=HIGH)
    ctx.route('**' + FX_URL + '**', lambda route: route.abort())
    page.set_default_timeout(120000)
    try:
        _start(page)
        if not page.evaluate(STATE)['webgl2']:
            pytest.skip('this browser has no WebGL 2; the effects are off by design')
        assert game.wait_for(page, "() => !!window.__TS.W.gfxState().failed", 60), page.evaluate(STATE)
        st = page.evaluate(STATE)
        assert not st['ready'] and 'could not load' in st['failed'], st
        frames = page.evaluate("() => new Promise(r => { let n = 0; const f = () => (++n < 5 ? requestAnimationFrame(f) : r(n)); requestAnimationFrame(f) })")
        assert frames == 5  # the game keeps drawing
        assert page.evaluate("() => !!document.querySelector('#stage canvas')")
        assert err.uncaught == [], err.uncaught
    finally:
        ctx.close()
