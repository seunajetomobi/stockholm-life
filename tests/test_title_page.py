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
    # the owner asked for no label on the title page; the origin is recorded in assets/title/CREDITS.md
    assert 'imgcredit' not in html  # no label on the page (assets/title/CREDITS.md still records where the picture came from)


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
    """SV | EN top right, map credit bottom left, an Options screen (reference design from the owner)."""
    ctx, page, err = game.new_page(browser, hook=True, realtime=True, title=True)
    page.set_default_timeout(90000)
    try:
        game.boot(page)
        assert game.wait_for(page, "() => { const t = document.getElementById('title'); return t && !t.hidden && /Start/.test(t.innerText) }", 60)
        now = page.evaluate(STOCKHOLM_NOW)
        # nothing top left any more: no date, clock or weather box
        assert page.evaluate("() => !document.getElementById('tWx')")
        # the map credit sits in the bottom-left corner and the AI label is gone
        r = page.evaluate("() => { const e = document.getElementById('tOsm'), b = e.getBoundingClientRect(); return {l: b.left, bot: innerHeight - b.bottom, txt: e.innerText, all: document.getElementById('title').innerText} }")
        assert r['l'] < 40 and r['bot'] < 40, r
        assert 'OpenStreetMap' in r['txt'] and 'contributors' in r['txt'], r
        assert 'AI' not in r['all'] and 'generated' not in r['all'].lower(), r
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


def test_title_name_uses_the_swedish_flag_colours(browser, server):
    ctx, page, err = game.new_page(browser, hook=True, realtime=True, title=True)
    page.set_default_timeout(90000)
    try:
        game.boot(page)
        assert game.wait_for(page, "() => { const t = document.getElementById('title'); return t && !t.hidden && /Start/.test(t.innerText) }", 60)
        c = page.evaluate("() => { const h = document.querySelector('#title h1'), s = h.querySelector('span'), g = e => getComputedStyle(e); return {a: g(h).color, as: g(h).webkitTextStrokeColor, b: g(s).color, bs: g(s).webkitTextStrokeColor} }")
        assert c['a'] == 'rgb(254, 204, 2)' and c['as'] == 'rgb(0, 106, 167)', c   # STOCKHOLMS: flag yellow, flag-blue outline
        assert c['b'] == 'rgb(0, 106, 167)' and c['bs'] == 'rgb(254, 204, 2)', c   # LIV: flag blue, flag-yellow outline
        assert err.uncaught == [], err.uncaught
    finally:
        ctx.close()


def test_title_blocks_the_game_and_buttons_animate(browser, server):
    """Until the player chooses on the title page nothing else answers; the buttons animate on hover."""
    ctx, page, err = game.new_page(browser, hook=True, realtime=True, title=True)
    page.set_default_timeout(90000)
    try:
        game.boot(page)
        assert game.wait_for(page, "() => { const t = document.getElementById('title'); return t && !t.hidden && /Start/.test(t.innerText) && window.__TS && window.__TS.S }", 60)
        before = page.evaluate("() => JSON.stringify(window.__TS.S.pos)")
        for k in ('w', 'a', 's', 'd', 'e', 'ArrowUp'):
            page.keyboard.down(k)
        page.wait_for_timeout(1500)
        for k in ('w', 'a', 's', 'd', 'e', 'ArrowUp'):
            page.keyboard.up(k)
        assert page.evaluate("() => JSON.stringify(window.__TS.S.pos)") == before, 'the avatar moved behind the title page'
        assert page.evaluate("() => document.body.classList.contains('titleopen')")
        assert page.evaluate("() => !document.querySelector('.modal')"), 'a dialog opened behind the title page'
        # hover: the button lifts and widens its lettering
        t0 = page.evaluate("() => { const b = document.getElementById('tOpt'); const s = getComputedStyle(b); return [s.transform, s.letterSpacing] }")
        page.hover('#tOpt')
        page.wait_for_timeout(500)
        t1 = page.evaluate("() => { const b = document.getElementById('tOpt'); const s = getComputedStyle(b); return [s.transform, s.letterSpacing] }")
        assert t0 != t1 and t1[0] != 'none', (t0, t1)
        assert err.uncaught == [], err.uncaught
    finally:
        ctx.close()
