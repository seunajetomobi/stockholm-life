"""The extra menus: accessibility, privacy and my data, help, what's new, install, keyboard use, loading tips, and Edit about me."""
import json
import struct
import game
import pytest
from test_title_page import _start

READY = "() => { const t = document.getElementById('title'); return t && !t.hidden && /Start/i.test(t.innerText) }"


def _open(browser, **kw):
    ctx, page, err = game.new_page(browser, hook=True, realtime=True, title=True, **kw)
    page.set_default_timeout(90000)
    game.boot(page)
    assert game.wait_for(page, READY, 60)
    return ctx, page, err


def card(page):
    return page.evaluate("() => document.getElementById('titleCard').innerText")


def test_options_is_a_menu_list_and_accessibility_works(browser, server):
    ctx, page, err = _open(browser)
    try:
        page.click('#tOpt')
        ids = page.evaluate("() => [...document.querySelectorAll('#titleCard .menulist button')].map(b => b.id)")
        assert ids == ['oAcc', 'oSet', 'oSaves', 'oAcct', 'oPriv', 'oHelp', 'oNew', 'oAbout', 'oInst'], ids
        page.click('#oAcc')
        assert 'Text size' in card(page) and 'High contrast' in card(page) and 'Reduce motion' in card(page)
        # text size: the slider scales menus and dialogs, and is remembered
        page.fill('#axTz', '3')
        assert page.evaluate("() => document.documentElement.style.getPropertyValue('--tz')") == '1.3'
        assert page.evaluate("() => document.getElementById('axTz').getAttribute('aria-valuetext')") == 'Extra large'
        assert page.evaluate("() => parseFloat(getComputedStyle(document.querySelector('#title .stack')).zoom)") == pytest.approx(1.3, abs=0.01)
        # high contrast and reduced motion are switches that set a class on the page
        page.click('.tog[data-k="hc"]')
        page.click('.tog[data-k="rm"]')
        assert page.evaluate("() => [document.body.classList.contains('hc'), document.body.classList.contains('rm')]") == [True, True]
        saved = page.evaluate("() => JSON.parse(localStorage.getItem('stockholmsliv-settings'))")
        assert saved['tz'] == 3 and saved['hc'] is True and saved['rm'] is True, saved
        # and they survive a reload
        page.reload(wait_until='load')
        game.wait_for(page, READY, 120)
        assert page.evaluate("() => [document.body.classList.contains('hc'), document.body.classList.contains('rm'), document.documentElement.style.getPropertyValue('--tz')]") == [True, True, '1.3']
        page.click('#tOpt'); page.click('#oAcc')
        page.fill('#axTz', '1')
        page.click('.tog[data-k="hc"]'); page.click('.tog[data-k="rm"]')
        assert page.evaluate("() => [document.body.classList.contains('hc'), document.body.classList.contains('rm')]") == [False, False]
        page.click('#axBack')
        assert 'Control hints' in card(page)
        assert err.uncaught == [], err.uncaught
    finally:
        ctx.close()


def test_privacy_download_and_delete(browser, server):
    ctx, page, err = _open(browser)
    try:
        page.click('#tOpt'); page.click('.tog[data-k="tips"]')          # something to be saved
        page.click('#oPriv')
        txt = card(page)
        assert 'stored on this device' in txt and 'No advertising, no tracking cookies and no analytics' in txt, txt
        with page.expect_download() as dl:
            page.click('#pvDownload')
        path = dl.value.path()
        data = json.loads(open(path, encoding='utf-8').read())
        assert data['app'] == 'stockholmsliv' and 'stockholmsliv-settings' in data['keys'], list(data['keys'])
        assert json.loads(data['keys']['stockholmsliv-settings'])['tips'] is False
        assert dl.value.suggested_filename.startswith('stockholmsliv-data-') and dl.value.suggested_filename.endswith('.json')
        # delete needs the word typed; Keep my data returns without deleting anything
        page.click('#pvDelete')
        assert page.evaluate("() => document.getElementById('pvDoDelete').disabled")
        page.fill('#pvConfirm', 'nope')
        assert page.evaluate("() => document.getElementById('pvDoDelete').disabled")
        page.click('#pvCancel')
        assert 'stockholmsliv-settings' in page.evaluate("() => Object.keys(localStorage)")
        page.click('#pvDelete')
        page.fill('#pvConfirm', 'delete')
        assert not page.evaluate("() => document.getElementById('pvDoDelete').disabled")
        with page.expect_navigation():
            page.click('#pvDoDelete')
        game.wait_for(page, READY, 120)
        left = page.evaluate("() => Object.keys(localStorage).filter(k => k.startsWith('stockholm-life') || k === 'stockholmsliv-settings' || k === 'stockholmsliv-intro-seen')")
        assert left == [], left
        assert err.uncaught == [], err.uncaught
    finally:
        ctx.close()


def test_help_news_install_and_swedish(browser, server):
    ctx, page, err = _open(browser)
    try:
        page.click('#tOpt'); page.click('#oHelp')
        assert page.evaluate("() => document.querySelectorAll('#titleCard details').length") == 6
        page.click('#titleCard summary:first-of-type')
        assert page.evaluate("() => document.querySelector('#titleCard details').open")
        href = page.evaluate("() => document.getElementById('hlReport').href")
        assert href.startswith('https://github.com/seunajetomobi/stockholm-life/issues/new?'), href
        body = __import__('urllib.parse', fromlist=['x']).unquote(href)
        assert 'Stockholmsliv 20' in body and 'Language: en' in body and 'Settings:' in body
        assert 'Tester' not in body and 'localStorage' not in body            # no names, no saves
        page.click('#hlCopy')
        assert game.wait_for(page, "() => document.getElementById('hlNote').innerText.trim() !== ''", 15), 'no message after Copy my details'
        page.click('#hlBack')
        # what's new
        page.click('#oNew')
        assert "What's new" in card(page) and '2026-11-23' in card(page)
        page.click('#nwBack')
        # install: with no browser prompt it explains how
        page.click('#oInst')
        assert 'Add to Home Screen' in page.evaluate("() => document.getElementById('oNote').innerText") and 'Android' in page.evaluate("() => document.getElementById('oNote').innerText")
        # Swedish
        page.click('#tLang button[data-l="sv"]')
        page.click('#oHelp')
        assert 'Sparas mitt liv?' in card(page) and 'Rapportera ett problem' in card(page)
        page.click('#hlBack'); page.click('#oPriv')
        assert 'Integritet och mina data' in card(page) and 'Radera mina data' in card(page)
        assert err.uncaught == [], err.uncaught
    finally:
        ctx.close()


def test_escape_goes_back_and_tab_stays_in_the_menu(browser, server):
    ctx, page, err = _open(browser)
    try:
        page.click('#tOpt'); page.click('#oAcc')
        page.keyboard.press('Escape')
        assert 'Control hints' in card(page)                              # Esc from Accessibility returns to Options
        page.keyboard.press('Escape')
        assert page.evaluate("() => !!document.getElementById('tPlay')")  # and from Options to the main menu
        page.click('#tPlay'); page.click('#cNew')
        page.keyboard.press('Escape')
        assert page.evaluate("() => !!document.getElementById('cNew')")   # Esc from the form returns to the choice
        # Tab never leaves the title page, in either direction
        for key in ['Tab'] * 14 + ['Shift+Tab'] * 14:
            page.keyboard.press(key)
            assert page.evaluate("() => document.getElementById('title').contains(document.activeElement)"), key
        assert err.uncaught == [], err.uncaught
    finally:
        ctx.close()


def test_edit_about_me_changes_the_life(browser, server):
    ctx, page, err = _open(browser)
    try:
        _start(page, nat='NG', status='temporary')
        page.evaluate("() => document.getElementById('editMe').click()")
        page.fill('#emName', 'Amara')
        page.fill('#emProf', 'baker')
        page.fill('#emBio', 'New bio.')
        page.select_option('#emLang', 'French'); page.select_option('#emLv', 'fluent'); page.click('#emAdd')
        page.check('#emHob input[data-h="Music"]')
        page.click('#emSave')
        got = page.evaluate("() => ({n: window.__TS.S.name, p: window.__TS.S.me.prof, b: window.__TS.S.me.bio, l: window.__TS.S.me.languages, h: window.__TS.S.me.hobbies})")
        assert got == {'n': 'Amara', 'p': 'baker', 'b': 'New bio.', 'l': [{'l': 'French', 'lv': 'fluent'}], 'h': ['Music']}, got
        # an empty name is refused
        page.evaluate("() => document.getElementById('editMe').click()")
        page.fill('#emName', ' ')
        page.click('#emSave')
        assert page.evaluate("() => document.getElementById('emErr').innerText") == 'Please enter a name.'
        assert page.evaluate("() => window.__TS.S.name") == 'Amara'
        assert err.uncaught == [], err.uncaught
    finally:
        ctx.close()


def test_about_me_escapes_saved_data_and_delete_reports_failure(browser, server):
    """Codex review of PR 56: saved traits/languages must not become HTML; a failed delete must say so."""
    ctx, page, err = _open(browser)
    try:
        _start(page, nat='NG', status='temporary')
        page.evaluate("""() => { const me = window.__TS.S.me;
            me.traits = ['<img src=x onerror="window.__xss=1">'];
            me.languages = [{l: 'French', lv: '<b id=xlv>fluent</b>'}];
            document.getElementById('editMe').click() }""")
        page.click('#emSave')
        assert page.evaluate("() => [!!document.querySelector('#aboutSec img'), !!document.getElementById('xlv'), window.__xss || 0]") == [False, False, 0]
        assert '<img' in page.evaluate("() => document.getElementById('aboutSec').innerText")
        assert err.uncaught == [], err.uncaught
    finally:
        ctx.close()


def test_privacy_delete_reports_data_that_could_not_be_removed(browser, server):
    ctx, page, err = _open(browser)
    try:
        page.click('#tOpt'); page.click('#oPriv'); page.click('#pvDelete')
        page.evaluate("() => { Storage.prototype.removeItem = function () {} }")
        page.fill('#pvConfirm', 'DELETE')
        page.click('#pvDoDelete')
        assert game.wait_for(page, "() => document.getElementById('pvErr').innerText.length > 5", 10)
        assert page.evaluate("() => !!document.getElementById('pvDoDelete')")  # still on the screen: no reload
        assert err.uncaught == [], err.uncaught
    finally:
        ctx.close()


def _png_size(path):
    b = path.read_bytes()
    assert b[:8] == b'\x89PNG\r\n\x1a\n'
    return struct.unpack('>II', b[16:24])


def test_installable_manifest_icons_and_loading_tips():
    root = game.ROOT
    m = json.loads((root / 'manifest.webmanifest').read_text(encoding='utf-8'))
    assert m['name'] == 'Stockholmsliv' and m['display'] == 'standalone' and m['theme_color'] == '#006aa7' and m['start_url'] == './'
    # Android and Chrome: 192 and 512 icons, and a separate maskable one (never "any maskable" in one icon)
    got = sorted((i['sizes'], i['purpose']) for i in m['icons'])
    assert got == [('192x192', 'any'), ('512x512', 'any'), ('512x512', 'maskable')], got
    for i in m['icons']:
        w, h = map(int, i['sizes'].split('x'))
        assert _png_size(root / i['src']) == (w, h), i
    # iPhone and iPad: a 180 pixel touch icon, and the standalone-app tags
    assert _png_size(root / 'assets' / 'icons' / 'apple-touch-icon-180.png') == (180, 180)
    assert _png_size(root / 'assets' / 'icons' / 'favicon-32.png') == (32, 32)
    assert (root / 'assets' / 'icons' / 'logo.svg').is_file()
    html = (root / 'index.html').read_text(encoding='utf-8')
    for tag in ('<link rel="manifest" href="manifest.webmanifest">', '<meta name="theme-color" content="#006aa7">',
                '<link rel="apple-touch-icon" sizes="180x180" href="assets/icons/apple-touch-icon-180.png">',
                '<meta name="apple-mobile-web-app-capable" content="yes">', '<meta name="mobile-web-app-capable" content="yes">',
                '<meta name="apple-mobile-web-app-title" content="Stockholmsliv">', '<link rel="icon" type="image/png" sizes="32x32" href="assets/icons/favicon-32.png">'):
        assert tag in html, tag
    assert 'id="loadtip"' in html and "const TIPS={en:[" in html and "sv:['Butiker och kontor" in html


def test_store_badges_are_the_official_ones_side_by_side_and_not_links_yet(browser, server):
    ctx, page, err = _open(browser, width=390, height=800, mobile=True)
    try:
        r = page.evaluate("""() => { const s = [...document.querySelectorAll('#titleCard .store')], imgs = s.map(e => e.querySelector('img')), b = document.querySelector('#titleCard .btns').getBoundingClientRect();
          const rc = s.map(e => e.getBoundingClientRect());
          return {n: s.length, links: s.filter(e => e.tagName === 'A').length, srcs: imgs.map(i => i.getAttribute('src')), alts: imgs.map(i => i.alt), loaded: imgs.map(i => i.complete && i.naturalWidth > 0),
                  sameRow: Math.abs(rc[0].top - rc[1].top) < 6, leftOf: rc[0].right <= rc[1].left, below: rc.every(x => x.top >= b.bottom), caption: document.querySelector('#titleCard .stsoon').innerText,
                  heights: rc.map(x => Math.round(x.height)), sw: document.documentElement.scrollWidth, vw: innerWidth} }""")
        assert r['n'] == 2 and r['links'] == 0, r                                   # not links: the apps are not published
        assert r['srcs'] == ['assets/stores/app-store-en.svg', 'assets/stores/google-play-en.png'], r
        assert r['alts'] == ['Download on the App Store', 'Get it on Google Play'] and all(r['loaded']), r
        assert r['sameRow'] and r['leftOf'] and r['below'] and r['sw'] <= r['vw'], r   # side by side, under the buttons, no sideways scroll
        assert 'coming soon' in r['caption'].lower() and r['heights'] == [44, 44], r
        page.click('#tLang button[data-l="sv"]')
        r2 = page.evaluate("() => ({srcs: [...document.querySelectorAll('#titleCard .store img')].map(i => i.getAttribute('src')), cap: document.querySelector('#titleCard .stsoon').innerText})")
        assert r2['srcs'] == ['assets/stores/app-store-sv.svg', 'assets/stores/google-play-sv.png'] and 'kommer snart' in r2['cap'].lower(), r2
        assert err.uncaught == [], err.uncaught
    finally:
        ctx.close()


def test_official_badge_files_are_present_and_plain():
    d = game.ROOT / 'assets' / 'stores'
    for f in ('app-store-en.svg', 'app-store-sv.svg'):
        x = (d / f).read_text(encoding='utf-8')
        assert x.startswith('<svg') and 'App_Store_Badge' in x, f
        assert not any(bad in x.lower() for bad in ('<script', 'onload', 'http://www.w3.org/1999/xlink', '<foreignobject', 'href="http')), f
    for f in ('google-play-en.png', 'google-play-sv.png'):
        assert _png_size(d / f) == (646, 250), f
    assert 'Official badges, used unchanged' in (d / 'README.md').read_text(encoding='utf-8')


def test_store_addresses_are_one_setting():
    html = (game.ROOT / 'index.html').read_text(encoding='utf-8')
    assert "const STORE={ios:'',android:''};" in html          # empty until the apps are published
    assert 'href="${STORE[k]}"' in html and 'rel="noopener"' in html
