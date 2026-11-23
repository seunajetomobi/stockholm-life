"""A title page with Start, How to play, Settings and Saves; a short introduction shown once; settings that are remembered (index.html, showTitle)."""
import game

STOCKHOLM_NOW = """() => { const p = window.StockholmLife['stockholm-time'].partsAt(Date.now());
  return {y: p.year, m: p.month, d: p.day, h: p.hour, min: p.minute} }"""
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
        assert saved['quality'] == 'low' and saved['live'] is False, saved
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


def _jpeg_size(path):
    b = path.read_bytes()
    i = 2
    while i < len(b):
        assert b[i] == 0xFF, 'not a JPEG marker stream'
        m = b[i + 1]
        n = int.from_bytes(b[i + 2:i + 4], 'big')
        if m in (0xC0, 0xC1, 0xC2):
            return int.from_bytes(b[i + 7:i + 9], 'big'), int.from_bytes(b[i + 5:i + 7], 'big')
        i += 2 + n
    raise AssertionError('no size found')


def test_background_photos_are_there_in_three_sizes_and_credited():
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    html = (root / 'index.html').read_text(encoding='utf-8')
    for name, size in (('3840', (3840, 2160)), ('1920', (1920, 1080)), ('1280', (1280, 720))):
        f = root / 'assets' / 'title' / f'stadshuset-{name}.jpg'
        assert f.is_file(), f
        assert _jpeg_size(f) == size, (f, _jpeg_size(f))
        assert f'assets/title/stadshuset-{name}.jpg' in html
    # the 4K picture stays a sensible download
    assert (root / 'assets' / 'title' / 'stadshuset-3840.jpg').stat().st_size < 2_000_000
    # the picture is an AI-generated image provided by the owner, and the page says so in both languages
    assert "imgcredit:'Background image: AI-generated'" in html and "imgcredit:'Bakgrundsbild: AI-genererad'" in html


def test_title_is_one_row_on_a_phone(browser, server):
    ctx, page, err = game.new_page(browser, hook=True, realtime=True, title=True, width=390, height=800, mobile=True)
    page.set_default_timeout(90000)
    try:
        game.boot(page)
        assert game.wait_for(page, "() => { const t = document.getElementById('title'); return t && !t.hidden && /Start/.test(t.innerText) }", 60)
        h = page.evaluate("() => { const e = document.querySelector('#title h1'); const r = e.getBoundingClientRect(); return {h: r.height, fs: parseFloat(getComputedStyle(e).fontSize), w: r.width, vw: innerWidth} }")
        assert h['h'] < h['fs'] * 1.4, h          # one line, not wrapped
        assert h['w'] <= h['vw'] - 16, h           # and it fits the screen
        assert err.uncaught == []
    finally:
        ctx.close()


def test_top_widgets_language_and_options(browser, server):
    """Live Stockholm time and weather top left, SV | EN top right, an Options screen (reference design from the owner)."""
    ctx, page, err = game.new_page(browser, hook=True, realtime=True, title=True)
    page.set_default_timeout(90000)
    try:
        game.boot(page)
        assert game.wait_for(page, "() => { const t = document.getElementById('title'); return t && !t.hidden && /Start/.test(t.innerText) }", 60)
        # the time box shows Stockholm's own time (within two minutes) and the date
        now = page.evaluate(STOCKHOLM_NOW)
        box = page.evaluate("() => document.getElementById('tWx').innerText")
        hh, mm = box.split(' ')[0].split(':')
        assert abs((int(hh) * 60 + int(mm)) - (now['h'] * 60 + now['min'])) <= 2, (box, now)
        assert str(now['y']) in box, box
        # five buttons, in the order of the design
        order = page.evaluate("() => [...document.querySelectorAll('#titleCard button')].map(b => b.id)")
        assert order == ['tPlay', 'tOpt', 'tHow', 'tSet', 'tSaves'], order
        # language: Swedish changes the page and is remembered
        page.click('#tLang button[data-l="sv"]')
        assert 'Starta' in page.evaluate("() => document.getElementById('titleCard').innerText")
        assert page.evaluate("() => localStorage.getItem('stockholmsliv-lang')") == 'sv'
        page.click('#tLang button[data-l="en"]')
        assert 'Start' in page.evaluate("() => document.getElementById('titleCard').innerText")
        # options: switching the control hints off hides the hint line, and it is saved
        page.click('#tOpt')
        page.click('.seg[data-k="hints"] button[data-v="false"]')
        assert page.evaluate("() => document.body.classList.contains('nohints')")
        assert page.evaluate("() => JSON.parse(localStorage.getItem('stockholmsliv-settings')).hints") is False
        assert err.uncaught == [], err.uncaught
    finally:
        ctx.close()
