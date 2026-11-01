"""M14 regression: the station/train message strip (#csLine) is a short bar on phones and unchanged on desktop.
Before the fix (742403b) it stretched 365-421 px tall on phones. Ported from the audit's m14.py and m14b.py."""
import time
import pytest
import game

pytestmark = [pytest.mark.browser, pytest.mark.hook]
SIZES = [(390, 844, True), (520, 900, True), (1366, 768, False)]
OTHERS = {'hud': '#csHud', 'prompt': '#csPrompt', 'joystick': '#joy', 'run': '#runbtn', 'zoom': '.ctrls', 'dock': '#dock'}
MAX_H = 60  # px; one or two lines of 12-13 px text with padding


def strip(page, w, h, mobile, label):
    """Measure the strip against the other UI and check it; returns the measurements."""
    game.shot(page, f'm14-{w}-{label}')
    b = game.boxes(page, {'line': '#csLine', **OTHERS})
    assert 'line' in b, f'{label}: message strip not shown'
    line = b.pop('line')
    m = {'box': [round(v) for v in line], 'height': round(line[3] - line[1]),
         'overlaps': {k: round(game.overlap(line, v)) for k, v in b.items()},
         'transform': page.evaluate("() => getComputedStyle(document.getElementById('csLine')).transform")}
    assert m['height'] <= MAX_H, f'{label}: strip {m["height"]} px tall (M14 regression?) {m}'
    assert game.overflow_x(page) == 0, f'{label}: horizontal overflow'
    if mobile:
        assert {k: v for k, v in m['overlaps'].items() if v} == {}, f'{label}: strip covers other UI {m}'
        assert line[0] >= 0 and line[2] <= w, f'{label}: strip wider than the screen {m}'
    else:
        assert m['transform'] != 'none', f'{label}: desktop strip is no longer centred {m}'
        assert line[1] < h / 3, f'{label}: desktop strip moved out of the top third {m}'
    return m


@pytest.mark.parametrize('w,h,mobile', SIZES, ids=[f'{w}x{h}' for w, h, _ in SIZES])
def test_message_strip(browser, w, h, mobile):
    ctx, page, err = game.new_page(browser, w, h, mobile=mobile, hook=True)
    try:
        game.boot(page)
        if game.intro_shown(page):
            game.start_life(page, mobile=mobile)
        game.enter_station(page)
        game.clear_overlays(page)

        # 1. in the station, a platform message (the text format the game uses)
        page.evaluate("() => __T.csLine('Spår 1: pendeltåg 41 to Södertälje centrum arrives 08:09, departs 08:10', 30)")
        time.sleep(1.5)
        strip(page, w, h, mobile, 'station')

        # 2. boarding: the game's own "find a seat" message, with its "Sit down?" prompt open
        game.board_train(page)
        assert game.wait_for(page, "() => getComputedStyle(document.getElementById('csLine')).display !== 'none'", 60), 'no boarding message'
        strip(page, w, h, mobile, 'boarding')

        # 3. a worst case on phones: a three-line prompt under a two-line message
        if mobile and game.wait_for(page, "() => getComputedStyle(document.getElementById('csPrompt')).display !== 'none'", 30):
            page.evaluate("""() => { const s = document.querySelector('#csPrompt small');
              if (s) s.textContent = 'Take this seat and watch the journey through the window all the way to Södertälje centrum, with a stop at every station';
              __T.csLine('Pendeltåg 41 to Södertälje centrum · departs 08:01 · find a seat (walk to one) or stay by the doors', 30) }""")
            time.sleep(1.2)
            strip(page, w, h, mobile, 'tallprompt')

        # 4. seated, an arrival message
        page.evaluate("() => { const s = __T.JRS.seats.find(q => !q.taken && q.k === 2 && q.x === 0.77); __T.jrSit(s); __T.csLine('Stockholms södra · doors open on the right', 30) }")
        time.sleep(3)
        strip(page, w, h, mobile, 'seated')
        assert err.uncaught == []
    finally:
        ctx.close()


# Short phone screens: the ride HUD at the top grows with its buttons, so a strip placed a fixed distance above the
# bottom could run into it (10 px at 360x640 with the prompt open). Measured with the real "Sit down?" prompt.
SHORT = [(360, 640), (375, 667), (390, 844), (768, 1024)]
TWO_LINES = 'Pendeltåg 41 to Södertälje centrum · departs 08:01 · find a seat (walk to one) or stay by the doors'
LAYOUT_JS = """() => { const box = id => { const e = document.getElementById(id), b = e.getBoundingClientRect();
    return getComputedStyle(e).display === 'none' || !b.height ? null : [b.left, b.top, b.right, b.bottom] };
  return {line: box('csLine'), hud: box('csHud'), prompt: document.getElementById('csPrompt').innerHTML ? box('csPrompt') : null} }"""


def clear_layout(page, w, h, label, prompt_open):
    """The strip is on screen, fully inside the viewport, and overlaps neither the ride HUD nor an open prompt."""
    game.shot(page, f'm14-{w}x{h}-{label}')
    b = page.evaluate(LAYOUT_JS)
    r = {k: v and [round(x) for x in v] for k, v in b.items()}
    assert b['line'] and b['hud'], f'{label}: strip or ride HUD not shown {r}'
    assert (b['prompt'] is not None) == prompt_open, f'{label}: prompt should be {"open" if prompt_open else "closed"} {r}'
    if w <= 400:
        assert b['line'][3] - b['line'][1] >= 36, f'{label}: expected a two-line message {r}'
    assert game.overlap(b['line'], b['hud']) == 0, f'{label}: strip overlaps the ride HUD {r}'
    if prompt_open:
        assert game.overlap(b['line'], b['prompt']) == 0, f'{label}: strip overlaps the prompt {r}'
    assert b['line'][1] >= 0 and b['line'][3] <= h and b['line'][2] <= w, f'{label}: strip outside the screen {r}'
    return r


@pytest.mark.parametrize('w,h', SHORT, ids=[f'{w}x{h}' for w, h in SHORT])
def test_strip_clear_of_ride_hud(browser, w, h):
    ctx, page, err = game.new_page(browser, w, h, mobile=True, hook=True)
    try:
        game.boot(page)
        if game.intro_shown(page):
            game.start_life(page, mobile=True)
        game.enter_station(page)
        game.clear_overlays(page)
        game.board_train(page)
        assert game.wait_for(page, "() => !!document.getElementById('csPrompt').innerHTML", 30), 'no "Sit down?" prompt'
        page.evaluate(f"() => __T.csLine({TWO_LINES!r}, 30)")
        time.sleep(1.5)
        opened = clear_layout(page, w, h, 'prompt-open', True)
        page.evaluate("() => { const s = __T.JRS.seats.find(q => !q.taken && q.k === 2 && q.x === 0.77); __T.jrSit(s) }")
        assert game.wait_for(page, "() => !document.getElementById('csPrompt').innerHTML", 30), 'prompt did not close'
        page.evaluate(f"() => __T.csLine({TWO_LINES!r}, 30)")
        time.sleep(1.5)
        closed = clear_layout(page, w, h, 'prompt-closed', False)
        print(f'{w}x{h} open {opened} closed {closed}')
        assert err.uncaught == []
    finally:
        ctx.close()
