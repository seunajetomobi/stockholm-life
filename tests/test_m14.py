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
