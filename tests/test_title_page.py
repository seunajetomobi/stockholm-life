"""A title page with Start, How to play, Settings and Saves; a short introduction shown once; settings that are remembered (index.html, showTitle)."""
import game
import pytest

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
        page.click('#cNew')
        page.fill('#nfName', 'Test Person')
        page.click('#nfGo')
        assert game.wait_for(page, "() => { const t = document.getElementById('title'); return t && !t.hidden && /Skip/.test(t.innerText) }", 20), 'no introduction'
        page.screenshot(path='/tmp/title_intro.png')
        page.click('#iSkip')
        assert game.wait_for(page, "() => document.getElementById('title').hidden && window.__TS.S && window.__TS.S.name", 30), 'game did not start'
        assert page.evaluate("() => localStorage.getItem('stockholmsliv-intro-seen')") == '1'
        # the brand opens the title page again, now with Continue
        # (the arrival cutscene hides the control buttons for a while, so press it from the page)
        page.evaluate("() => document.getElementById('menuBtn').click()")
        assert game.wait_for(page, "() => { const t = document.getElementById('title'); return t && !t.hidden && /Start/.test(t.innerText) }", 10)
        page.click('#tPlay')
        assert game.wait_for(page, "() => { const t = document.getElementById('title'); return t && !t.hidden && /Continue your life/.test(t.innerText) }", 10)
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


def test_time_is_stockholm_even_when_the_device_clock_is_wrong(browser, server):
    """The device clock is set three hours wrong; the game still gets the true time from the server's Date header."""
    import time
    skew = "const R = Date, OFF = 3 * 3600e3; class D extends R { constructor(...a) { a.length ? super(...a) : super(R.now() + OFF) } static now() { return R.now() + OFF } } Date = D;"
    ctx, page, err = game.new_page(browser, hook=True, realtime=True, title=True, init_script=skew)
    page.set_default_timeout(90000)
    try:
        game.boot(page)
        assert game.wait_for(page, "() => { const t = document.getElementById('title'); return t && !t.hidden && /Start/.test(t.innerText) }", 60)
        got = page.evaluate("() => ({device: Date.now(), true_: window.StockholmLife['stockholm-time'].nowMs(), off: window.StockholmLife['stockholm-time'].getOffset()})")
        real = time.time() * 1000
        assert abs(got['device'] - real - 3 * 3600e3) < 5000, got        # the device really was three hours ahead
        assert abs(got['true_'] - real) < 4000, (got, real)               # and the game's time is still the true time
        assert err.uncaught == [], err.uncaught
    finally:
        ctx.close()


def test_no_ringing_on_the_title_page(browser, server):
    ctx, page, err = game.new_page(browser, hook=True, realtime=True, title=True)
    page.set_default_timeout(90000)
    try:
        game.boot(page)
        assert game.wait_for(page, "() => { const t = document.getElementById('title'); return !!(t && !t.hidden && window.__T && window.__T.incomingCall) }", 60)
        for _ in range(5):
            page.evaluate("() => window.__T.incomingCall()")
        page.wait_for_timeout(800)
        assert page.evaluate("() => document.querySelectorAll('.callscr,.ringing').length") == 0, 'a phone call showed on the title page'
        assert err.uncaught == [], err.uncaught
    finally:
        ctx.close()


def test_title_buttons_are_a_narrow_column(browser, server):
    ctx, page, err = game.new_page(browser, hook=True, realtime=True, title=True, width=1366, height=768)
    page.set_default_timeout(90000)
    try:
        game.boot(page)
        assert game.wait_for(page, "() => { const t = document.getElementById('title'); return t && !t.hidden && /Start/.test(t.innerText) }", 60)
        w = page.evaluate("() => [...document.querySelectorAll('#titleCard .btns button')].map(b => b.offsetWidth)")  # layout width: a focused button is drawn slightly larger
        assert len(w) == 5 and max(w) <= 262, w
        assert err.uncaught == [], err.uncaught
    finally:
        ctx.close()


def test_start_choice_load_and_new_life_form(browser, server):
    """Start opens: load saved game or start a new life; Back returns; the form decides born-in-Sweden and the status."""
    ctx, page, err = game.new_page(browser, hook=True, realtime=True, title=True)
    page.set_default_timeout(90000)
    try:
        game.boot(page)
        assert game.wait_for(page, "() => { const t = document.getElementById('title'); return t && !t.hidden && /Start/.test(t.innerText) }", 60)
        page.click('#tPlay')
        txt = page.evaluate("() => document.getElementById('titleCard').innerText")
        assert 'Load saved game' in txt and 'Start a new life' in txt and 'Back' in txt, txt
        # Load saved game: a list of slots, nothing saved yet, Back goes to the choice again
        page.click('#cLoad')
        assert 'No saved lives yet' in page.evaluate("() => document.getElementById('titleCard').innerText")
        page.click('#lBack')
        assert page.evaluate("() => !!document.getElementById('cNew')")
        # New life: Swedish nationality means born in Sweden, and no immigration status
        page.click('#cNew')
        assert page.evaluate("() => document.getElementById('nfBorn').innerText") == 'Born in Sweden: yes (the form starts with Sweden)' or 'Born in Sweden: yes' in page.evaluate("() => document.getElementById('nfBorn').innerText")
        assert page.evaluate("() => getComputedStyle(document.getElementById('nfStatusRow')).display") == 'none'
        assert page.evaluate("() => getComputedStyle(document.getElementById('nfTownRow')).display") != 'none'
        # another nationality: born abroad, and the four statuses appear
        page.select_option('#nfNat', 'Nigeria')
        assert 'Born in Sweden: no' in page.evaluate("() => document.getElementById('nfBorn').innerText")
        assert page.evaluate("() => getComputedStyle(document.getElementById('nfStatusRow')).display") != 'none'
        assert page.evaluate("() => getComputedStyle(document.getElementById('nfTownRow')).display") == 'none', 'home town must be hidden for someone born abroad'
        opts = page.evaluate("() => [...document.querySelectorAll('#nfStatus option')].map(o => o.value)")
        assert opts == ['temporary', 'asylum', 'permanent', 'student'], opts
        # an EU citizen gets the two statuses that make sense
        page.select_option('#nfNat', 'Germany')
        opts = page.evaluate("() => [...document.querySelectorAll('#nfStatus option')].map(o => o.value)")
        assert opts == ['eu', 'student'], opts
        # validation: an empty name and a bad age are refused with a message
        page.fill('#nfName', '  ')
        page.click('#nfGo')
        assert page.evaluate("() => document.getElementById('nfErr').innerText") == 'Please enter a name.'
        page.fill('#nfName', 'Aisha')
        page.fill('#nfAge', '12')
        page.click('#nfGo')
        assert 'between 16 and 90' in page.evaluate("() => document.getElementById('nfErr').innerText")
        # Back keeps you on the choice screen
        page.click('#nfBack')
        assert page.evaluate("() => !!document.getElementById('cLoad')")
        assert err.uncaught == [], err.uncaught
    finally:
        ctx.close()


def _start(page, nat, status=None, age='30'):
    page.click('#tPlay')
    page.click('#cNew')
    page.fill('#nfName', 'Tester')
    page.fill('#nfAge', age)
    page.select_option('#nfNat', nat)
    if status:
        page.select_option('#nfStatus', status)
    page.click('#nfGo')
    game.wait_for(page, "() => { const t = document.getElementById('title'); return t && !t.hidden && /Skip/.test(t.innerText) }", 20)
    page.click('#iSkip')
    assert game.wait_for(page, "() => document.getElementById('title').hidden && window.__TS.S && window.__TS.S.name === 'Tester'", 60), 'the life did not start'


@pytest.mark.parametrize('nat,status,bg,permit', [
    ('Sweden', None, 'local', 1), ('Nigeria', 'temporary', 'newcomer', 0), ('Nigeria', 'asylum', 'asylum', 'asylum'),
    ('Nigeria', 'permanent', 'permanent', 1), ('Nigeria', 'student', 'student', 0)])
def test_form_choices_start_the_right_kind_of_life(browser, server, nat, status, bg, permit):
    ctx, page, err = game.new_page(browser, hook=True, realtime=True, title=True)
    page.set_default_timeout(90000)
    try:
        game.boot(page)
        assert game.wait_for(page, "() => { const t = document.getElementById('title'); return t && !t.hidden && /Start/.test(t.innerText) }", 60)
        _start(page, nat, status)
        got = page.evaluate("() => ({bg: window.__TS.S.bg, permit: window.__TS.S.docs.permit, status: (window.__TS.S.origin || {}).status || '', nat: window.__TS.S.nat || (window.__TS.S.origin || {}).nat, age: window.__TS.S.me && window.__TS.S.me.age})")
        assert got['bg'] == bg and got['permit'] == permit, got
        assert got['status'] == (status or ''), got
        assert got['age'] == 30, got
        assert err.uncaught == [], err.uncaught
    finally:
        ctx.close()
