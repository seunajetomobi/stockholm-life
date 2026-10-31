"""Save and load: reload restores the life, a corrupted save starts fresh, an old v3 save migrates to v4.
These check today's behaviour, including the known silent overwrite of a corrupted save (KNOWN_ISSUES H5)."""
import json
import pytest
import game

pytestmark = pytest.mark.browser
KEYS = ('name', 'day', 'hour', 'money', 'pos')


def test_reload_restores_life(browser):
    ctx, page, err = game.new_page(browser)
    try:
        game.boot(page)
        game.start_life(page)
        before = game.saved(page)
        assert before, 'no save after starting a life'
        page.reload(wait_until='load')
        page.wait_for_function("() => !document.getElementById('loading')", timeout=180000)
        page.wait_for_timeout(3000)
        after = game.saved(page)
        assert not game.intro_shown(page), 'intro shown again after reload'
        assert {k: after.get(k) for k in KEYS} == {k: before.get(k) for k in KEYS}
        assert err.uncaught == []
    finally:
        ctx.close()


# set the save only on the first page load of the context, so the game's own rewrite is not undone
ONCE = "try {{ if (!sessionStorage.getItem('t')) {{ localStorage.setItem({k}, {v}); sessionStorage.setItem('t', 1) }} }} catch (e) {{}}"


def test_corrupted_save_starts_fresh(browser):
    ctx, page, err = game.new_page(browser, init_script=ONCE.format(k=json.dumps(game.SAVE_KEY), v=json.dumps('{not json')))
    try:
        game.boot(page)
        assert game.intro_shown(page), 'a corrupted save should lead to character creation'
        assert err.uncaught == []
    finally:
        ctx.close()


def test_legacy_v3_save_migrates(browser):
    old = {'name': 'Old', 'bg': 'newcomer', 'day': 3, 'hour': 10, 'money': 1200, 'energy': 70, 'mood': 50, 'social': 10,
           'svenska': 5, 'skill': 40, 'queue': 0, 'home': 'rinkebyRoom', 'loc': 'tc', 'job': None, 'flags': {}, 'log': [], 'applied': {}}
    ctx, page, err = game.new_page(browser, init_script=ONCE.format(k=json.dumps('stockholm-life-v3'), v=json.dumps(json.dumps(old))))
    try:
        game.boot(page)
        assert not game.intro_shown(page), 'the v3 life was not loaded'
        hud = page.evaluate("() => [document.getElementById('time').innerText, document.getElementById('money').innerText]")
        assert hud[0] == '10:00', hud
        assert hud[1].replace(' ', ' ').replace(' ', ' ') == '1 200 kr', hud
        s = game.saved(page)
        assert s and s.get('name') == 'Old', 'v4 save not written from the v3 save'
        assert err.uncaught == []
    finally:
        ctx.close()
