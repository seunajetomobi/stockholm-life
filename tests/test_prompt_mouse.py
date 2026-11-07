"""Station and train prompts answered with a real mouse (page.mouse): move, press, at least two frames, release.
Other tests call the game's functions or element.click(), so they cannot see a press and a release landing on different
elements. Run on an older index.html with SL_INDEX_HTML=<file> for the negative control."""
import json
import time
import pytest
import game

pytestmark = [pytest.mark.browser, pytest.mark.hook]

FRAMES = "n => new Promise(r => { const f = () => n-- > 0 ? requestAnimationFrame(f) : r(); f() })"
# what the browser did with the mouse: the target of each event, and how often the prompt's contents were replaced
WATCH = """() => { const el = document.getElementById('csPrompt'), name = t => (t.className || t.id || t.tagName) + (t.isConnected ? '' : ' (removed)');
  window.__seen = {events: [], rebuilds: 0};
  for (const type of ['mousedown', 'mouseup', 'click']) document.addEventListener(type, e => window.__seen.events.push([type, name(e.target)]), true);
  new MutationObserver(l => { window.__seen.rebuilds += l.filter(m => m.type === 'childList').length }).observe(el, {childList: true}) }"""
SHOWN = "() => (document.querySelector('#csPrompt b') || {}).textContent || ''"
# Stand in the aisle beside one free seat, away from the open doors, and return the prompt ID the game should offer for it. The seat
# across the aisle is exactly as near and the game takes the first of two equal seats, so it is occupied to leave one nearest seat.
# Pass a seat's index to choose a row far from it.
NEAR_SEAT = """old => { const T = __T, X = T.JRS.seats, at = (q, x) => Math.abs(q.x - x) < 0.01, want = T.JR.doorSide > 0 ? -0.27 : 0.77;
  if (T.CS.sit) T.jrStand(true);
  const s = X.find(q => !q.taken && !q.tried && q.k === 2 && at(q, want) && (old == null || Math.abs(q.z - X[old].z) > 3));
  for (const q of X) if (q !== s && !q.taken && Math.abs(q.z - s.z) < 0.01 && (at(q, -0.27) || at(q, 0.77))) q.taken = 'test';
  s.tried = 1; window.__seat = s; T.av.position.set(0.25, 0, s.z); return 'seat' + X.indexOf(s) }"""
OFFERED = "id => !!__T.PRM.cur && __T.PRM.cur.id === id"


@pytest.fixture
def city(browser):
    ctx, page, err = game.new_page(browser, 1366, 768, hook=True)
    game.boot(page)
    if game.intro_shown(page):
        game.start_life(page)
    game.clear_overlays(page)
    yield page, err
    ctx.close()


@pytest.fixture
def seat_prompt(city):
    """Standing in the train beside a free seat, with "Sit down?" open."""
    page, err = city
    game.enter_station(page)
    game.board_train(page)
    game.clear_overlays(page)
    offer(page)
    page.evaluate(WATCH)
    return page, err


def offer(page, old=None):
    """Move beside a seat and wait until the prompt offers that seat. "Sit down?" alone is not enough: boarding leaves the player
    beside another seat, whose prompt has the same words and is still open until the next frame."""
    seat = page.evaluate(NEAR_SEAT, old)
    assert game.wait_for(page, f"() => ({OFFERED})({json.dumps(seat)}) && ({SHOWN})() === 'Sit down?'", 30), f'no "Sit down?" prompt for {seat}'
    return seat


def press_and_release(page, selector, frames=3):
    """The real input: the mouse goes to the button, presses, stays down for a few frames, and releases."""
    box = page.evaluate("s => { const b = document.querySelector(s).getBoundingClientRect(); return [b.left + b.width / 2, b.top + b.height / 2] }", selector)
    page.mouse.move(*box)
    page.evaluate(FRAMES, frames)
    page.mouse.down()
    page.evaluate(FRAMES, frames)
    page.mouse.up()


def report(page, name):
    """Kept for the review: what the browser saw, and the screen."""
    seen = page.evaluate("() => window.__seen")
    print(f'\n{name}: {json.dumps(seen)}')
    game.shot(page, f'prompt-mouse-{name}')
    return seen


def test_sit_yes_with_mouse(seat_prompt):
    page, err = seat_prompt
    press_and_release(page, '#csPrompt .y')
    seated = game.wait_for(page, "() => __T.CS.sit === window.__seat && !document.getElementById('csPrompt').innerHTML", 10)
    seen = report(page, 'sit-yes')
    assert seated, f'one click on Yes did not seat the player: {seen}'
    assert game.wait_for(page, "() => document.getElementById('jrSit').textContent.includes('Stand up')", 10), 'the button does not say Stand up'
    assert game.wait_for(page, "() => { const v = document.getElementById('jrView'); return getComputedStyle(v).display !== 'none' && /You|Eyes/.test(v.textContent) }", 10), 'no camera button'
    assert err.uncaught == []


def test_sit_no_with_mouse(seat_prompt):
    page, err = seat_prompt
    press_and_release(page, '#csPrompt .n')
    closed = game.wait_for(page, "() => !document.getElementById('csPrompt').innerHTML", 10)
    seen = report(page, 'sit-no')
    assert closed, f'one click on No did not close the prompt: {seen}'
    page.evaluate(FRAMES, 5)
    assert page.evaluate("() => !__T.CS.sit && !document.getElementById('csPrompt').innerHTML"), 'No must not seat the player or reopen the prompt'
    assert err.uncaught == []


def test_buttons_stay_the_same_elements(seat_prompt):
    """The cause of a lost click: the game makes a new prompt object every frame, and while it offers the same seat the buttons must
    stay, including when the player shifts slightly. The watch starts once this seat is offered, so a change of seat is not counted."""
    page, _ = seat_prompt
    page.evaluate("""() => { const P = __T.PRM; window.__y = document.querySelector('#csPrompt .y'); window.__n = document.querySelector('#csPrompt .n');
      window.__cur = P.cur; __T.av.position.z += 0.02 }""")
    page.evaluate(FRAMES, 10)
    r = page.evaluate("""() => { const P = __T.PRM; return {asked_again: P.cur !== window.__cur, seat: P.cur.id === window.__cur.id, connected: window.__y.isConnected,
      yes: window.__y === document.querySelector('#csPrompt .y'), no: window.__n === document.querySelector('#csPrompt .n')} }""")
    seen = report(page, 'identity')
    assert r['asked_again'], f'the game did not ask for the prompt again, so this proves nothing: {r}'
    assert r['seat'], f'the offered seat changed during the watch: {r}'
    assert r['connected'] and r['yes'] and r['no'] and seen['rebuilds'] == 0, (r, seen)


def test_changed_content_still_updates(city):
    """The game's own promptSet, all in one JS turn so no frame interferes: the same content keeps the buttons and uses the
    newest prompt; any change that shows on screen rebuilds them; no prompt empties it."""
    page, err = city
    r = page.evaluate("""() => { const set = __T.promptSet, el = document.getElementById('csPrompt'), y = () => el.querySelector('.y'), out = {};
      const base = {id: 'x', q: 'Q', sub: 'S', yes: () => { window.__yes = 'old' }};
      set(base); const first = y();
      set({...base, yes: () => { window.__yes = 'new' }}); out.kept = y() === first;
      y().click(); out.yes = window.__yes; out.closed = !el.innerHTML;
      const shown = {q: () => ({...base, q: 'Q2'}), sub: () => ({...base, sub: 'S2'}), yesL: () => ({...base, yesL: 'Yes2'}), noL: () => ({...base, noL: 'No2'}),
        extra: () => ({...base, extra: [{l: 'X2', fn() {}}]}), id: () => ({...base, id: 'y'})};
      out.changed = {};
      for (const k in shown) { set(base); const before = y(), text = el.innerText; set(shown[k]()); out.changed[k] = y() !== before && (k === 'id' || el.innerText !== text) }
      set({...base, extra: [{l: 'X', fn() {}}]}); const a = y(); set({...base, extra: [{l: 'X3', fn() {}}]}); out.changed.extraLabel = y() !== a && el.innerText.includes('X3');
      out.roles = [getComputedStyle(el).display, el.getAttribute('role'), el.querySelectorAll('button').length];
      set(null); out.empty = !el.innerHTML && getComputedStyle(el).display === 'none';
      return out }""")
    print('\nchanged-content:', json.dumps(r))
    assert r['kept'], r
    assert r['yes'] == 'new' and r['closed'], r
    assert all(r['changed'].values()), r
    assert r['roles'] == ['grid', 'dialog', 3], r
    assert r['empty'], r
    assert err.uncaught == []


def test_new_seat_gets_new_prompt(seat_prompt):
    """Walking to another seat changes which seat the prompt offers, even though its words are the same: the buttons are replaced
    exactly once, and one click on Yes takes the new seat and not the old one."""
    page, err = seat_prompt
    page.evaluate("() => { window.__y = document.querySelector('#csPrompt .y'); window.__old = window.__seat; window.__seen.rebuilds = 0 }")
    old = page.evaluate("() => __T.JRS.seats.indexOf(window.__old)")
    offer(page, old)
    assert page.evaluate("() => document.querySelector('#csPrompt .y') !== window.__y"), 'the prompt still offers the old seat'
    seen = page.evaluate("() => window.__seen")
    assert seen['rebuilds'] == 1, f'changing seat once should replace the buttons once: {seen}'
    press_and_release(page, '#csPrompt .y')
    assert game.wait_for(page, "() => __T.CS.sit === window.__seat", 10), report(page, 'new-seat')
    assert page.evaluate("() => window.__seat !== window.__old && !window.__old.taken"), 'the old seat was taken'
    assert err.uncaught == []


def test_get_off_with_mouse(city):
    """The other prompt the train builds every frame. All seats are taken so the door prompt is the one offered."""
    page, err = city
    game.enter_station(page)
    game.board_train(page)
    game.clear_overlays(page)
    page.evaluate("() => { for (const s of __T.JRS.seats) s.taken = s.taken || 'test' }")
    at_door = "() => { const T = __T; if (T.JR.phase === 'run') T.jrSkipNext(); T.av.position.set(T.JR.doorSide * (T.IW - 0.2), 0, T.zcOf(2) + T.DOORZ); return document.querySelector('#csPrompt b')?.textContent || '' }"
    t0 = time.time()
    while not page.evaluate(at_door).startswith('Get off') and time.time() - t0 < 150:
        time.sleep(1)
    assert page.evaluate(SHOWN).startswith('Get off'), 'no "Get off" prompt'
    page.evaluate(WATCH)
    press_and_release(page, '#csPrompt .y')
    off = game.wait_for(page, "() => __T.CS.mode !== 'ride'", 60)
    seen = report(page, 'get-off')
    assert off, f'one click on Yes did not get off the train: {seen}'
    assert err.uncaught == []


def test_enter_station_with_mouse(city):
    """The street prompt at the station doors. It is rebuilt less often than the train's, so an older build can get this right by luck."""
    page, err = city
    page.evaluate("() => { const w = __T.CS_DOORS[0].w; __T.av.position.set(w.x, 0.01, w.z) }")
    assert game.wait_for(page, f"({SHOWN})() === 'Enter the station?'", 30), 'no "Enter the station?" prompt'
    page.evaluate(WATCH)
    press_and_release(page, '#csPrompt .y')
    entered = game.wait_for(page, "() => __T.CS.mode === 'station'", 60)
    seen = report(page, 'enter-station')
    assert entered, f'one click on Yes did not enter the station: {seen}'
    assert err.uncaught == []
