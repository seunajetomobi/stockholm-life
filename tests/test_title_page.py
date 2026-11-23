"""A title page with Start, How to play, Settings and Saves; a short introduction shown once; settings that are remembered (index.html, showTitle)."""
import game

VISIBLE = "() => { const t = document.getElementById('title'); return !!t && !t.hidden && t.innerText }"


def test_title_intro_settings_flow(browser, server):
    ctx, page, err = game.new_page(browser, hook=True, realtime=True, title=True)
    page.set_default_timeout(90000)  # the software-GL browser is slow when the machine is busy
    try:
        game.boot(page)
        assert game.wait_for(page, "() => { const t = document.getElementById('title'); return t && !t.hidden && /Start/.test(t.innerText) }", 60), 'no title page'
        text = page.evaluate(VISIBLE)
        for word in ('Stockholms', 'Start', 'How to play', 'Settings', 'Saves'):
            assert word.lower() in text.lower(), (word, text)
        # Settings: choose Low graphics and Live data off; both are remembered and survive a reload
        page.click('#tSet')
        page.click('.seg[data-k="quality"] button[data-v="low"]')
        page.click('.seg[data-k="live"] button[data-v="false"]')
        saved = page.evaluate("() => JSON.parse(localStorage.getItem('stockholmsliv-settings'))")
        assert saved == {'quality': 'low', 'live': False}, saved
        page.click('#sBack')
        assert 'Start' in page.evaluate(VISIBLE)
        # Start: the first time the introduction shows; Skip goes straight into the game
        page.click('#tPlay')
        assert game.wait_for(page, "() => { const t = document.getElementById('title'); return t && !t.hidden && /Skip/.test(t.innerText) }", 20), 'no introduction'
        page.screenshot(path='/tmp/title_intro.png')
        page.click('#iSkip')
        assert game.wait_for(page, "() => document.getElementById('title').hidden && window.__TS.S && window.__TS.S.name", 30), 'game did not start'
        assert page.evaluate("() => localStorage.getItem('stockholmsliv-intro-seen')") == '1'
        # the brand opens the title page again, now with Continue
        # (the arrival cutscene hides the control buttons for a while, so press it from the page)
        page.evaluate("() => document.getElementById('menuBtn').click()")
        assert game.wait_for(page, "() => { const t = document.getElementById('title'); return t && !t.hidden && /Continue/.test(t.innerText) }", 10)
        assert err.uncaught == [], err.uncaught
    finally:
        ctx.close()
