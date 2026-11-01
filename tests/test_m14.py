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


# The strip must never cover a control. On short phones the ride HUD grows down to it (10 px at 360x640 with the
# prompt open); on tablets and small laptops the places bar and the "Next up" card sit beside it (at 768x1024 it hid
# the right 23 px of the Home button). Every visible control is measured, at many sizes, in the station and train.
CONTROLS = ('#csHud,#csPrompt,#board,#next,#ride,#places button,#inAct,#inhud,.ctrls button,.sos112,.carechip,'
            '#joy,#runbtn,#dock button')
TWO_LINES = 'Pendeltåg 41 to Södertälje centrum · departs 08:01 · find a seat (walk to one) or stay by the doors'
THREE_LINES = ('Pendeltåg 41 to Södertälje centrum departs 08:01 from spår 2 · find a seat (walk to one) or stay by the '
               'doors · next stop Stockholms södra, then Årstaberg and Älvsjö')
TALL_PROMPT = ('Take this seat and watch the journey through the window all the way to Södertälje centrum, with a stop '
               'at every station')
PHONES = [(360, 640), (375, 667), (390, 844), (520, 900), (601, 900), (640, 900), (768, 1024), (640, 360), (844, 390),
          (1024, 768)]
# For each visible control: its box and, where it meets the strip, whether it is still on top there: drawn above the
# strip (stacking order of their top-level parents) and the one that takes a tap at the centre of the shared area.
LAYOUT_JS = """(sel) => { const vis = e => { const b = e.getBoundingClientRect(), c = getComputedStyle(e);
    return b.width && b.height && c.display !== 'none' && c.visibility !== 'hidden' ? b : null };
  const l = document.getElementById('csLine'), lb = vis(l), lz = +getComputedStyle(l).zIndex || 0, out = [];
  const layer = e => { while (e.parentElement && e.parentElement.id !== 'stage' && e.parentElement !== document.body) e = e.parentElement;
    return e.id === 'dock' ? Infinity : +getComputedStyle(e).zIndex || 0 };
  for (const e of document.querySelectorAll(sel)) { const b = vis(e); if (!b || (e.id === 'csPrompt' && !e.innerHTML)) continue;
    let onTop = null;
    if (lb) { const x0 = Math.max(lb.left, b.left), x1 = Math.min(lb.right, b.right), y0 = Math.max(lb.top, b.top), y1 = Math.min(lb.bottom, b.bottom);
      if (x1 > x0 && y1 > y0) { const t = document.elementFromPoint((x0 + x1) / 2, (y0 + y1) / 2);
        onTop = layer(e) > lz && getComputedStyle(l).pointerEvents === 'none' && !!t && (t === e || e.contains(t)) } }
    out.push([(e.id || e.className.split(' ')[0] || e.parentElement.id) + (e.closest('#places,.ctrls,#dock') ? ':' + (e.innerText || e.getAttribute('aria-label') || '').trim().slice(0, 12) : ''),
              [b.left, b.top, b.right, b.bottom], onTop]) }
  return {line: lb && [lb.left, lb.top, lb.right, lb.bottom], vw: innerWidth, vh: innerHeight, ctl: out} }"""


def show(page, msg, w=None, h=None):
    if w:
        page.set_viewport_size({'width': w, 'height': h})
        time.sleep(1.2)
    page.evaluate(f"() => __T.csLine({msg!r}, 30)")
    time.sleep(0.8)
    return page.evaluate(LAYOUT_JS, CONTROLS)


def covered(d):
    """Every control the strip covers, even by part of a pixel, and a strip that leaves the screen. Only when nothing
    else fits may the strip share space with a control, and then only beneath it (the control drawn on top and tapped)."""
    line = d['line']
    if not line:
        return ['strip not shown']
    bad = [f'{n} {[round(v) for v in b]} ({game.overlap(line, b):.1f} px²)' for n, b, on_top in d['ctl']
           if game.overlap(line, b) > 0 and not on_top]
    if line[0] < 0 or line[1] < 0 or line[2] > d['vw'] or line[3] > d['vh']:
        bad.append('strip leaves the screen')
    return bad


def check(page, cases, state, prompt_open, sizes):
    for w, h in sizes:
        for lines, msg in (('2', TWO_LINES), ('3', THREE_LINES)):
            d = show(page, msg, w, h)
            assert any(n == 'csPrompt' for n, *_ in d['ctl']) == prompt_open, f'{state} {w}x{h}: prompt state wrong'
            under = [n for n, b, on_top in d['ctl'] if on_top]  # no-room fallback, see test_no_room_fallback
            cases.append((f'{state} {w}x{h} {lines}-line' + (f' (beneath {under})' if under else ''),
                          [round(v) for v in d['line'] or []], covered(d)))


def report(cases):
    bad = [c for c in cases if c[2]]
    print('\n'.join(f'{n}: strip {b} {v or "clear"}' for n, b, v in cases))
    assert not bad, f'{len(bad)} of {len(cases)} layouts cover a control:\n' + '\n'.join(f'{n}: strip {b} covers {v}' for n, b, v in bad)


def ride_states(page, cases, sizes, tall_prompt):
    """Station, boarding with the "Sit down?" prompt open (also made three lines tall), and seated with it closed:
    three different ride HUDs."""
    game.enter_station(page)
    game.clear_overlays(page)
    check(page, cases, 'station', False, sizes)
    game.board_train(page)
    assert game.wait_for(page, "() => !!document.getElementById('csPrompt').innerHTML", 30), 'no "Sit down?" prompt'
    check(page, cases, 'boarding', True, sizes)
    if tall_prompt:
        page.evaluate(f"() => {{ const s = document.querySelector('#csPrompt small'); if (s) s.textContent = {TALL_PROMPT!r} }}")
        check(page, cases, 'tall-prompt', True, sizes)
    page.evaluate("() => { const s = __T.JRS.seats.find(q => !q.taken && q.k === 2 && q.x === 0.77); __T.jrSit(s) }")
    assert game.wait_for(page, "() => !document.getElementById('csPrompt').innerHTML", 30), 'prompt did not close'
    check(page, cases, 'seated', False, sizes)


def test_strip_avoids_controls_phone_tablet(browser):
    """Portrait and landscape phones and tablets; one boot, the viewport resized."""
    ctx, page, err = game.new_page(browser, 390, 844, mobile=True, hook=True)
    try:
        game.boot(page)
        if game.intro_shown(page):
            game.start_life(page, mobile=True)
        cases = []
        ride_states(page, cases, PHONES, True)
        report(cases)
        assert err.uncaught == []
    finally:
        ctx.close()


def test_strip_avoids_controls_desktop(browser):
    ctx, page, err = game.new_page(browser, 1366, 768, mobile=False, hook=True)
    try:
        game.boot(page)
        if game.intro_shown(page):
            game.start_life(page)
        cases = []
        ride_states(page, cases, [(1366, 768), (1280, 720), (1920, 1080), (1024, 768)], True)
        report(cases)
        # where nothing is in the way the desktop strip keeps its centred place below the top bar
        d = show(page, TWO_LINES, 1366, 768)
        assert page.evaluate("() => document.getElementById('csLine').style.top") == '', 'desktop strip moved without need'
        assert abs((d['line'][0] + d['line'][2]) / 2 - 683) < 1, f'desktop strip not centred {d["line"]}'
        assert err.uncaught == []
    finally:
        ctx.close()


def test_home_button_768x1024(browser):
    """Regression (PR #4 review): at 768x1024 the strip covered the right 23 px of the places bar's Home button."""
    ctx, page, err = game.new_page(browser, 768, 1024, mobile=True, hook=True)
    try:
        game.boot(page)
        if game.intro_shown(page):
            game.start_life(page, mobile=True)
        game.enter_station(page)
        game.clear_overlays(page)
        game.board_train(page)
        assert game.wait_for(page, "() => !!document.getElementById('csPrompt').innerHTML", 30), 'no "Sit down?" prompt'
        game.shot(page, 'm14-768x1024-home')
        d = page.evaluate(LAYOUT_JS, CONTROLS)
        home = [b for n, b, _ in d['ctl'] if n.startswith('places') and 'Home' in n]
        assert home and d['line'], f'Home button or strip not shown {d}'
        assert game.overlap(d['line'], home[0]) == 0, f'strip {d["line"]} covers the Home button {home[0]}'
        assert covered(d) == [], f'strip covers {covered(d)}'
        assert err.uncaught == []
    finally:
        ctx.close()


def test_no_room_fallback(browser):
    """At 640x360 (a phone on its side) a three-line message fits nowhere between the ride HUD, the joystick, Run, the
    zoom buttons and the dock. The strip then shares space with as little as it can, beneath it: the control stays
    drawn on top and takes the taps."""
    ctx, page, err = game.new_page(browser, 640, 360, mobile=True, hook=True)
    try:
        game.boot(page)
        if game.intro_shown(page):
            game.start_life(page, mobile=True)
        game.enter_station(page)
        game.clear_overlays(page)
        game.board_train(page)
        assert game.wait_for(page, "() => !!document.getElementById('csPrompt').innerHTML", 30), 'no "Sit down?" prompt'
        d = show(page, THREE_LINES)
        game.shot(page, 'm14-640x360-noroom')
        shared = [(n, [round(v) for v in b], on_top) for n, b, on_top in d['ctl'] if on_top is not None]
        print('strip', [round(v) for v in d['line']], 'shares space with', shared)
        assert shared, f'expected no room at 640x360, but strip {d["line"]} is clear'
        assert all(on_top for *_, on_top in shared), f'a control is under the strip or loses taps: {shared}'
        assert covered(d) == [], covered(d)
        assert err.uncaught == []
    finally:
        ctx.close()
