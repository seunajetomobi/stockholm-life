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
        for word in ('Stockholms', 'Start', 'Options', 'How to play'):
            assert word.lower() in text.lower(), (word, text)
        for gone in ('Settings', 'Saves', 'Load saved game'):
            assert gone.lower() not in text.lower(), (gone, text)   # Settings and saved games are inside Options
        # Settings: choose Low graphics and Live data off; both are remembered and survive a reload
        page.click('#tOpt')
        page.click('#oSet')
        page.click('.seg[data-k="quality"] button[data-v="low"]')
        page.click('.seg[data-k="live"] button[data-v="false"]')
        saved = page.evaluate("() => JSON.parse(localStorage.getItem('stockholmsliv-settings'))")
        assert saved['quality'] == 'low' and saved['live'] is False, saved
        page.click('#sBack')
        assert 'Control hints' in page.evaluate(VISIBLE)           # Back from Settings returns to Options
        page.click('#oBack')
        assert 'Start' in page.evaluate(VISIBLE)
        # Start: the first time the introduction shows; Skip goes straight into the game
        page.click('#tPlay')
        page.click('#cNew')
        _page1(page, name='Test Person')
        page.click('#nfGo')
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
        assert order == ['tPlay', 'tOpt', 'tHow'], order
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
        assert len(w) == 3 and max(w) <= 262, w
        assert err.uncaught == [], err.uncaught
    finally:
        ctx.close()


def _page1(page, nat='SE', status=None, name='Tester', age='30', gender='woman'):
    page.fill('#nfName', name)
    if age:
        page.select_option('#nfAge', age)
    if gender:
        page.select_option('#nfGender', gender)
    if nat != 'SE':
        page.select_option('#nfNat', nat)
        if status:
            page.select_option('#nfStatus', status)


def test_start_choice_load_and_new_life_form(browser, server):
    """Start opens: load saved game or start a new life; Back returns; the form decides born-in-Sweden, the home town and the status."""
    ctx, page, err = game.new_page(browser, hook=True, realtime=True, title=True)
    page.set_default_timeout(90000)
    try:
        game.boot(page)
        assert game.wait_for(page, "() => { const t = document.getElementById('title'); return t && !t.hidden && /Start/.test(t.innerText) }", 60)
        page.click('#tPlay')
        txt = page.evaluate("() => document.getElementById('titleCard').innerText")
        assert 'Start a new life' in txt and 'Back' in txt, txt
        assert 'Load saved game' not in txt and 'Continue your life' not in txt, txt   # nothing saved yet: no Continue
        # Saved games live inside Options: nothing saved yet, Back returns to Options
        page.click('#cBack')
        page.click('#tOpt')
        page.click('#oSaves')
        assert 'No saved lives yet' in page.evaluate("() => document.getElementById('titleCard').innerText")
        page.click('#lBack')
        assert 'Control hints' in page.evaluate("() => document.getElementById('titleCard').innerText")
        page.click('#oBack')
        page.click('#tPlay')
        page.click('#cNew')
        disp = lambda q: page.evaluate("(q) => getComputedStyle(document.querySelector(q)).display", q)
        # placeholders: nothing is prefilled
        assert page.evaluate("() => document.getElementById('nfName').placeholder") == 'Fill in your name'
        assert page.evaluate("() => document.getElementById('nfName').value") == ''
        # age is a drop-down, 16 to 90
        ages = page.evaluate("() => [...document.querySelectorAll('#nfAge option')].map(o => o.value).filter(Boolean)")
        assert ages[0] == '16' and ages[-1] == '90' and len(ages) == 75, (ages[:2], ages[-2:], len(ages))
        # every gender identity is on offer
        gens = page.evaluate("() => [...document.querySelectorAll('#nfGender option')].map(o => o.value).filter(Boolean)")
        for g in ('woman', 'man', 'nonbinary', 'transwoman', 'transman', 'genderqueer', 'genderfluid', 'agender', 'bigender', 'twospirit', 'intersex', 'questioning', 'other', 'nosay'):
            assert g in gens, (g, gens)
        # validation messages come one at a time, before a gender is chosen
        page.click('#nfGo')
        assert page.evaluate("() => document.getElementById('nfErr').innerText") == 'Please enter a name.'
        page.fill('#nfName', 'Aisha')
        page.click('#nfGo')
        assert page.evaluate("() => document.getElementById('nfErr').innerText") == 'Please select your age.'
        page.select_option('#nfAge', '30')
        page.click('#nfGo')
        assert page.evaluate("() => document.getElementById('nfErr').innerText") == 'Please select your gender identity.'
        assert disp('#nfGenderTextRow') == 'none'
        page.select_option('#nfGender', 'other')
        assert disp('#nfGenderTextRow') != 'none'
        # all the world's countries, Sweden first
        n = page.evaluate("() => [...document.querySelectorAll('#nfNat option')].map(o => o.value)")
        assert len(n) == 197 and n[0] == 'SE' and 'NG' in n and 'VA' in n and 'TW' in n, (len(n), n[:3])
        # Swedish nationality: born here, a Swedish home town, no immigration status
        assert 'Born in Sweden: yes' in page.evaluate("() => document.getElementById('nfBorn').innerText")
        assert disp('#nfStatusRow') == 'none' and disp('#nfTownRow') != 'none'
        towns = page.evaluate("() => [...document.querySelectorAll('#nfTown option')].map(o => o.value)")
        assert towns[0] == 'Stockholm' and 'Göteborg' in towns, towns
        # another nationality: born abroad, the home town list becomes that country's, and the four statuses appear
        page.select_option('#nfNat', 'NG')
        assert 'Born in Sweden: no' in page.evaluate("() => document.getElementById('nfBorn').innerText")
        assert disp('#nfStatusRow') != 'none'
        towns = page.evaluate("() => [...document.querySelectorAll('#nfTown option')].map(o => o.value)")
        assert 'Lagos' in towns and 'Stockholm' not in towns and towns[-1] == '__other', towns
        opts = page.evaluate("() => [...document.querySelectorAll('#nfStatus option')].map(o => o.value)")
        assert opts == ['temporary', 'asylum', 'permanent', 'student'], opts
        page.select_option('#nfTown', '__other')
        assert disp('#nfTownTextRow') != 'none'
        # an EU citizen gets the two statuses that make sense
        page.select_option('#nfNat', 'DE')
        opts = page.evaluate("() => [...document.querySelectorAll('#nfStatus option')].map(o => o.value)")
        assert opts == ['eu', 'student'], opts
        page.select_option('#nfGender', 'transwoman')
        page.click('#nfGo')
        # step 2: background and about you
        assert 'step 2 / 2' in page.evaluate("() => document.getElementById('titleCard').innerText").lower()
        assert page.evaluate("() => [...document.querySelectorAll('#nfEdu option')].length") == 4
        page.click('.chips[data-k="skills"] button:nth-child(1)')
        for i in range(2, 6):
            page.click(f'.chips[data-k="skills"] button:nth-child({i})')
        assert 'most you can' in page.evaluate("() => document.getElementById('nfErr').innerText")
        page.click('#nfBack')
        assert page.evaluate("() => document.getElementById('nfName').value") == 'Aisha'   # step 1 kept what you wrote
        page.click('#nfBack')
        assert page.evaluate("() => !!document.getElementById('cNew')")
        assert err.uncaught == [], err.uncaught
    finally:
        ctx.close()


def _start(page, nat='SE', status=None, extra=None):
    page.click('#tPlay')
    page.click('#cNew')
    _page1(page, nat, status)
    page.click('#nfGo')
    if extra:
        extra(page)
    page.click('#nfGo')
    game.wait_for(page, "() => { const t = document.getElementById('title'); return t && !t.hidden && /Skip/.test(t.innerText) }", 20)
    page.click('#iSkip')
    assert game.wait_for(page, "() => document.getElementById('title').hidden && window.__TS.S && window.__TS.S.name === 'Tester'", 60), 'the life did not start'


@pytest.mark.parametrize('nat,status,bg,permit', [
    ('SE', None, 'local', 1), ('NG', 'temporary', 'newcomer', 0), ('NG', 'asylum', 'asylum', 'asylum'),
    ('NG', 'permanent', 'permanent', 1), ('NG', 'student', 'student', 0), ('NO', 'eu', 'newcomer', 1)])
def test_form_choices_start_the_right_kind_of_life(browser, server, nat, status, bg, permit):
    ctx, page, err = game.new_page(browser, hook=True, realtime=True, title=True)
    page.set_default_timeout(90000)
    try:
        game.boot(page)
        assert game.wait_for(page, "() => { const t = document.getElementById('title'); return t && !t.hidden && /Start/.test(t.innerText) }", 60)
        _start(page, nat, status)
        got = page.evaluate("() => ({bg: window.__TS.S.bg, permit: window.__TS.S.docs.permit, status: (window.__TS.S.origin || {}).status || '', age: window.__TS.S.me && window.__TS.S.me.age, gl: window.__TS.S.me && window.__TS.S.me.genderLabel, g: window.__TS.S.me && window.__TS.S.me.gender})")
        assert got['bg'] == bg and got['permit'] == permit, got
        assert got['status'] == ({'eu': ''}.get(status, status) or ''), got
        assert got['age'] == 30 and got['gl'] == 'Woman' and got['g'] == 'f', got
        assert err.uncaught == [], err.uncaught
    finally:
        ctx.close()


def test_background_details_reach_the_life(browser, server):
    """Education, profession, skills, personality, interests, about-you text, home town and gender identity are kept."""
    ctx, page, err = game.new_page(browser, hook=True, realtime=True, title=True)
    page.set_default_timeout(90000)
    try:
        game.boot(page)
        assert game.wait_for(page, "() => { const t = document.getElementById('title'); return t && !t.hidden && /Start/.test(t.innerText) }", 60)

        def extra(pg):
            pg.select_option('#nfEdu', 'uni')
            pg.fill('#nfProf', 'nurse')
            pg.click('.chips[data-k="skills"] button:nth-child(4)')       # Care work
            pg.click('.chips[data-k="traits"] button:nth-child(10)')      # Kind
            pg.click('.chips[data-k="hobbies"] button:nth-child(4)')      # Music
            pg.select_option('#nfSv', 'basic')
            pg.fill('#nfBio', 'I want to work in care in Stockholm.')
        # a non-Swedish life with a chosen home town: Lagos
        page.click('#tPlay'); page.click('#cNew'); _page1(page, 'NG', 'temporary', gender='nonbinary'); page.select_option('#nfTown', 'Lagos'); page.click('#nfGo')
        extra(page)
        page.click('#nfGo')
        game.wait_for(page, "() => { const t = document.getElementById('title'); return t && !t.hidden && /Skip/.test(t.innerText) }", 20)
        page.click('#iSkip')
        assert game.wait_for(page, "() => document.getElementById('title').hidden && window.__TS.S && window.__TS.S.name === 'Tester'", 60)
        me = page.evaluate("() => window.__TS.S.me")
        assert me['edu'] == 'uni' and me['prof'] == 'nurse' and me['skills'] == ['Care work'] and me['traits'] == ['kind'] and me['hobbies'] == ['Music'], me
        assert me['homeTown'] == 'Lagos' and me['genderLabel'] == 'Non-binary' and me['gender'] == 'x' and me['bornSweden'] is False, me
        assert me['bio'] == 'I want to work in care in Stockholm.', me
        assert page.evaluate("() => window.__TS.S.svenska") >= 15
        assert err.uncaught == [], err.uncaught
    finally:
        ctx.close()
