"""Every menu closes on a click outside it (owner, 2026-11-25): the title page's panels, the game's dialogs and the drawer.
A click outside does what the menu's own Back, Close or Cancel does; a dialog the player must answer stays open; a drag or
a text selection that starts inside and ends outside closes nothing (index.html: titleBack, scrimDismiss, drawerOutside)."""
import game

BESIDE = (40, 384)   # at 1366 x 768: left of the title card and of every dialog, clear of the corner widgets
ON_DIM = (8, 384)    # the dimmed area round a dialog
PANEL = "() => {{ const t = document.getElementById('title'); return !!(t && !t.hidden && !t.classList.contains('out') && document.getElementById('{}')) }}"
DIALOG = "() => !!document.querySelector('#modalRoot .modal')"
NO_DIALOG = "() => !document.querySelector('#modalRoot .modal')"
DRAWER_OPEN = "() => !document.getElementById('drawer').hidden"


def test_title_panels_close_on_a_click_beside_them(browser, server):
    ctx, page, err = game.new_page(browser, hook=True, realtime=True, title=True)
    page.set_default_timeout(90000)
    try:
        game.boot(page)
        assert game.wait_for(page, PANEL.format('tPlay'), 60), 'no title page'
        page.mouse.click(*BESIDE)                 # the main menu has nothing to close
        page.wait_for_timeout(800)
        assert page.evaluate(PANEL.format('tPlay')), 'the main menu went away on a click beside it'
        for opener, back in (('tOpt', 'oBack'), ('tHow', 'iSkip'), ('tPlay', 'cBack')):
            page.evaluate(f"() => document.getElementById('{opener}').click()")
            assert game.wait_for(page, PANEL.format(back), 60), f'{opener} did not open its panel'
            page.mouse.click(*BESIDE)
            assert game.wait_for(page, PANEL.format('tPlay'), 60), f'the panel of {opener} stayed open after a click beside it'
        # a press inside the panel that is released beside it (a drag, a text selection) closes nothing
        page.evaluate("() => document.getElementById('tOpt').click()")
        assert game.wait_for(page, PANEL.format('oBack'), 60)
        r = page.evaluate("() => { const r = document.querySelector('#titleCard .card').getBoundingClientRect(); return [r.x + 16, r.y + 16] }")
        page.mouse.move(*r)
        page.mouse.down()
        page.mouse.move(*BESIDE, steps=6)
        page.mouse.up()
        page.wait_for_timeout(1500)
        assert page.evaluate(PANEL.format('oBack')), 'Options closed after a drag that ended beside it'
        # How to play: Escape now goes back too, as its Back button does
        page.evaluate("() => document.getElementById('oBack').click()")
        assert game.wait_for(page, PANEL.format('tHow'), 60)
        page.evaluate("() => document.getElementById('tHow').click()")
        assert game.wait_for(page, PANEL.format('iSkip'), 60)
        page.keyboard.press('Escape')
        assert game.wait_for(page, PANEL.format('tPlay'), 60), 'Escape did not leave How to play'
        assert err.uncaught == [], err.uncaught
    finally:
        ctx.close()


def test_dialogs_close_on_a_click_on_the_dim_area(browser, server):
    ctx, page, err = game.new_page(browser, hook=True)
    page.set_default_timeout(90000)
    try:
        game.boot(page)
        if game.intro_shown(page):              # the new-life form must be answered: a click outside leaves it
            page.mouse.click(*ON_DIM)
            page.wait_for_timeout(1500)
            assert game.intro_shown(page), 'the new-life form closed on a click outside it'
            game.start_life(page)
        game.clear_overlays(page)
        # a real dialog, the phone dialer: a click on the dim area presses its Close
        page.evaluate("() => window.__TU.openCalls()")
        assert game.wait_for(page, DIALOG, 20)
        page.mouse.click(*ON_DIM)
        assert game.wait_for(page, NO_DIALOG, 20), 'the dialer stayed open after a click outside it'
        # Close before Back (Arlanda security has both), and the button's own handler runs
        game.clear_overlays(page)
        page.evaluate("""() => { window.__pressed = ''; window.__TU.modal('<p>Test</p><div class="btns"><button id="back">Flights</button><button id="no">Close</button></div>', m => {
            m.querySelector('#back').onclick = () => { window.__pressed = 'back'; window.__TU.closeModal() };
            m.querySelector('#no').onclick = () => { window.__pressed = 'no'; window.__TU.closeModal() } }) }""")
        page.mouse.click(*ON_DIM)
        assert game.wait_for(page, "() => window.__pressed !== ''", 20)
        assert page.evaluate("() => window.__pressed") == 'no', 'a click outside pressed Back, not Close'
        # once something is typed in a dialog, a stray click outside does not throw it away (its Close still works)
        game.clear_overlays(page)
        page.evaluate("""() => { window.__pressed = ''; window.__TU.modal('<input id="amt"><div class="btns"><button id="no">Cancel</button></div>', m => {
            m.querySelector('#no').onclick = () => { window.__pressed = 'no'; window.__TU.closeModal() } }) }""")
        page.fill('#amt', '250')
        page.mouse.click(*ON_DIM)
        page.wait_for_timeout(1500)
        assert page.evaluate(DIALOG) and page.evaluate("() => window.__pressed") == '', 'a dialog with typed input closed on a click outside it'
        page.evaluate("() => window.__TU.closeModal()")
        # a dialog without a close button stays open: the player must answer it
        game.clear_overlays(page)
        page.evaluate("""() => window.__TU.modal('<p>Answer me</p><div class="btns"><button id="yes">OK</button></div>')""")
        page.mouse.click(*ON_DIM)
        page.wait_for_timeout(1500)
        assert page.evaluate(DIALOG), 'a dialog the player must answer closed on a click outside it'
        page.evaluate("() => window.__TU.closeModal()")
        # a press inside the dialog released on the dim area (a drag, a text selection) closes nothing
        game.clear_overlays(page)
        page.evaluate("() => window.__TU.openCalls()")
        assert game.wait_for(page, DIALOG, 20)
        r = page.evaluate("() => { const r = document.querySelector('#modalRoot .modal').getBoundingClientRect(); return [r.x + r.width / 2, r.y + 12] }")
        page.mouse.move(*r)
        page.mouse.down()
        page.mouse.move(*ON_DIM, steps=6)
        page.mouse.up()
        page.wait_for_timeout(1500)
        assert page.evaluate(DIALOG), 'the dialer closed after a drag that ended outside it'
        # Quit: a click outside is "Keep playing", never "Quit without saving" (which reloads the page)
        game.clear_overlays(page)
        page.evaluate("() => { window.__same_page = 1; window.__TU.quitGame() }")
        assert game.wait_for(page, "() => !!document.querySelector('#modalRoot #qCancel')", 20)
        page.mouse.click(*ON_DIM)
        assert game.wait_for(page, NO_DIALOG, 20), 'Quit stayed open after a click outside it'
        page.wait_for_timeout(1500)
        assert page.evaluate("() => window.__same_page") == 1, 'the page reloaded: a click outside Quit did more than keep playing'
        assert err.uncaught == [], err.uncaught
    finally:
        ctx.close()


ON_MAP = """() => { const d = document.getElementById('drawer'), r = d.hidden ? null : d.getBoundingClientRect(), W = innerWidth, H = innerHeight;
  for (let dy = 0; dy < H / 2; dy += 24) for (const y of [H * 0.55 - dy, H * 0.55 + dy]) for (let dx = 0; dx < W / 2; dx += 24) for (const x of [W / 2 - dx, W / 2 + dx]) {
    if (x < 4 || y < 4 || x > W - 4 || y > H - 4) continue;
    const e = document.elementFromPoint(x, y);
    if (e && e.tagName === 'CANVAS' && !(r && x >= r.left && x <= r.right && y >= r.top && y <= r.bottom)) return [x, y] }
  return null }"""
DRAWER_SHUT = "() => document.getElementById('drawer').hidden"


def _drawer_page(browser, width, height, mobile):
    ctx, page, err = game.new_page(browser, width, height, mobile=mobile, hook=True)
    page.set_default_timeout(90000)
    game.boot(page)
    if game.intro_shown(page):
        game.start_life(page, mobile=mobile)
    return ctx, page, err


def _open(page, tab):
    game.clear_overlays(page)                    # random calls and tips first (this also closes the drawer)
    page.evaluate(f"() => window.__TU.setTab('{tab}')")
    assert game.wait_for(page, DRAWER_OPEN, 20), f'{tab} did not open'
    pt = page.evaluate(ON_MAP)
    assert pt, 'no free point on the map'
    return pt


def test_a_drawer_menu_closes_on_a_tap_on_the_map(browser, server):
    """Laptop: Phone, Bag... close on a tap on the map; a drag of the map or a tap inside the drawer leaves them open."""
    ctx, page, err = _drawer_page(browser, 1366, 768, False)
    try:
        pt = _open(page, 'bag')
        page.mouse.move(*pt)                     # dragging the map (turning the camera) leaves it open
        page.mouse.down()
        page.mouse.move(pt[0] + 60, pt[1] + 10, steps=6)
        page.mouse.up()
        page.wait_for_timeout(1500)
        assert page.evaluate(DRAWER_OPEN), 'the drawer closed when the map was dragged'
        dt = page.evaluate("() => { const r = document.getElementById('dtitle').getBoundingClientRect(); return [r.x + 4, r.y + r.height / 2] }")
        page.mouse.click(*dt)                    # a tap inside the drawer leaves it open
        page.wait_for_timeout(1000)
        assert page.evaluate(DRAWER_OPEN), 'the drawer closed on a tap inside it'
        page.mouse.click(*page.evaluate(ON_MAP))  # a tap on the map closes it
        assert game.wait_for(page, DRAWER_SHUT, 20), 'the bag stayed open after a tap on the map'
        # on a wide screen the Here panel is docked beside the map, open by default: a tap on the map leaves it
        pt = _open(page, 'here')
        page.mouse.click(*pt)
        page.wait_for_timeout(1500)
        assert page.evaluate(DRAWER_OPEN), 'the docked Here panel closed on a tap on the map'
        assert err.uncaught == [], err.uncaught
    finally:
        ctx.close()


def test_on_a_phone_the_drawer_closes_on_a_tap_on_the_map(browser, server):
    """Phone: the drawer covers the map, so every tab, Here too, closes on a tap on the map."""
    ctx, page, err = _drawer_page(browser, 390, 844, True)
    try:
        # a pinch (a second finger down before the first comes up) is not a tap: the drawer stays (Codex review)
        pt = _open(page, 'here')
        page.evaluate("""([x, y]) => { const c = document.elementFromPoint(x, y);
            const ev = (type, id, primary, dx) => c.dispatchEvent(new PointerEvent(type, {pointerId: id, isPrimary: primary,
              pointerType: 'touch', clientX: x + dx, clientY: y, bubbles: true, cancelable: true}));
            ev('pointerdown', 11, true, 0); ev('pointerdown', 12, false, 40); ev('pointerup', 12, false, 40); ev('pointerup', 11, true, 0) }""", pt)
        page.wait_for_timeout(1200)
        assert page.evaluate(DRAWER_OPEN), 'a two-finger pinch on the map closed the drawer'
        for tab in ('here', 'phone'):
            pt = _open(page, tab)
            page.touchscreen.tap(*pt)
            assert game.wait_for(page, DRAWER_SHUT, 20), f'{tab} stayed open after a tap on the map on a phone'
        assert err.uncaught == [], err.uncaught
    finally:
        ctx.close()
