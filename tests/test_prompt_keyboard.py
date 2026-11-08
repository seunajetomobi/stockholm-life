"""Station and train prompts answered with the real keyboard (page.keyboard: key down, at least two frames, key up): E, Enter and Y
for Yes, Escape and N for No. A spy on the game's prompt counts each answer, so doing something twice fails even when it looks the same.
Run on an older index.html with SL_INDEX_HTML=<file> to compare. The keyboard does not use the buttons, so the build before the mouse fix
passes too: the controls for these tests are deliberately broken copies of the game (see tests/README.md)."""
import pytest
import game
from test_prompt_mouse import FRAMES, SHOWN, offer

pytestmark = [pytest.mark.browser, pytest.mark.hook]

# counts every answer given to whichever prompt the game makes current
SPY = """() => { const P = __T.PRM; let cur = P.cur; window.__n = {yes: 0, no: 0};
  const wrap = s => { if (s && !s.spied) { s.spied = 1; const y = s.yes, n = s.no; s.yes = () => { window.__n.yes++; y() }; s.no = () => { window.__n.no++; if (n) n() } } return s };
  wrap(cur); Object.defineProperty(P, 'cur', {get: () => cur, set: v => { cur = wrap(v) }, configurable: true}) }"""
RESET = "() => { window.__n.yes = 0; window.__n.no = 0 }"
COUNT = "() => window.__n"
CLOSED = "() => !document.getElementById('csPrompt').innerHTML && !__T.PRM.cur"
AWAY = "() => { __T.av.position.set(30, 0.01, 30) }"
TEST_PROMPT = "() => { __T.promptSet({id: 'test', q: 'Test?', sub: 'keyboard', yes() {}, no() {}}) }"


def press(page, key):
    """The real input: the key goes down, stays down for two frames, and comes up."""
    page.keyboard.down(key)
    page.evaluate(FRAMES, 2)
    page.keyboard.up(key)


# one page per class, closed when its class ends: two pages with the whole city open at once starve each other's frames
@pytest.fixture(scope='class')
def train(browser):
    """One boarding for the seat tests, each using its own seat. The train stays at the platform, so no stop or tunnel exit interrupts a test."""
    ctx, page, err = game.new_page(browser, 1366, 768, hook=True)
    game.boot(page)
    if game.intro_shown(page):
        game.start_life(page)
    game.clear_overlays(page)
    game.enter_station(page)
    game.board_train(page)
    game.clear_overlays(page)
    page.evaluate("() => { __T.JR.depAt = Infinity }")
    page.evaluate(SPY)
    yield page, err
    ctx.close()


@pytest.fixture(scope='class')
def street(browser):
    """One city for the tests on the street, away from the station until the last of them."""
    ctx, page, err = game.new_page(browser, 1366, 768, hook=True)
    game.boot(page)
    if game.intro_shown(page):
        game.start_life(page)
    game.clear_overlays(page)
    page.evaluate(AWAY)
    page.evaluate(SPY)
    yield page, err
    ctx.close()


class TestOnTheTrain:
    @pytest.mark.parametrize('key', ['e', 'Enter', 'y'])
    def test_sit_yes_with_key(self, train, key):
        page, err = train
        offer(page)
        page.evaluate(RESET)
        press(page, key)
        assert game.wait_for(page, f"() => __T.CS.sit === window.__seat && ({CLOSED})()", 10), f'{key} did not seat the player: {page.evaluate(COUNT)}'
        assert page.evaluate(COUNT) == {'yes': 1, 'no': 0}, f'{key} must answer Yes exactly once'
        assert game.wait_for(page, "() => document.getElementById('jrSit').textContent.includes('Stand up')", 10), 'the button does not say Stand up'
        press(page, key)  # the prompt has gone, so the same key must now do nothing
        page.evaluate(FRAMES, 2)
        assert page.evaluate(COUNT) == {'yes': 1, 'no': 0}, f'a second {key} answered again'
        assert page.evaluate(f"() => __T.CS.sit === window.__seat && ({CLOSED})()"), f'a second {key} changed the state'
        assert err.uncaught == []


    @pytest.mark.parametrize('key', ['Escape', 'n'])
    def test_sit_no_with_key(self, train, key):
        page, err = train
        offer(page)
        page.evaluate(RESET)
        press(page, key)
        assert game.wait_for(page, f"({CLOSED})", 10), f'{key} did not close the prompt: {page.evaluate(COUNT)}'
        assert page.evaluate(COUNT) == {'yes': 0, 'no': 1}, f'{key} must answer No exactly once'
        page.evaluate(FRAMES, 3)
        assert page.evaluate(f"() => !__T.CS.sit && ({CLOSED})()"), f'{key} must not seat the player or reopen the prompt'
        assert page.evaluate(COUNT) == {'yes': 0, 'no': 1}
        assert err.uncaught == []


    def test_get_off_with_key(self, train):
        """The other prompt the train builds every frame. Last in the train's tests, because it leaves the train."""
        page, err = train
        page.evaluate("() => { const T = __T; if (T.CS.sit) T.jrStand(true); for (const s of T.JRS.seats) s.taken = s.taken || 'test'; T.av.position.set(T.JR.doorSide * (T.IW - 0.2), 0, T.zcOf(2) + T.DOORZ) }")
        assert game.wait_for(page, f"() => ({SHOWN})().startsWith('Get off')", 60), 'no "Get off" prompt'
        page.evaluate(RESET)
        press(page, 'e')
        assert game.wait_for(page, "() => __T.CS.mode !== 'ride'", 60), f'E did not get off the train: {page.evaluate(COUNT)}'
        assert page.evaluate(COUNT) == {'yes': 1, 'no': 0}, 'E must answer Yes exactly once'
        assert err.uncaught == []


class TestOnTheStreet:
    def test_held_key_answers_once(self, street):
        """A held key repeats in the browser. Only the first press may answer."""
        page, err = street
        page.evaluate(TEST_PROMPT)
        page.evaluate(RESET)
        page.keyboard.down('e')
        for _ in range(3):
            page.keyboard.down('e')  # Playwright sends these as auto-repeat
        page.evaluate(FRAMES, 2)
        page.keyboard.up('e')
        assert page.evaluate(COUNT) == {'yes': 1, 'no': 0}
        assert page.evaluate(CLOSED)
        assert err.uncaught == []


    def test_typing_in_a_field_does_not_answer(self, street):
        page, err = street
        page.evaluate(TEST_PROMPT)
        page.evaluate(RESET)
        page.evaluate("() => { const i = document.createElement('input'); i.id = 'testInput'; document.body.appendChild(i); i.focus() }")
        page.keyboard.type('yen')
        page.keyboard.press('Enter')
        page.keyboard.press('Escape')
        state = page.evaluate("() => { const i = document.getElementById('testInput'), v = i.value; i.remove(); return {typed: v, open: !!__T.PRM.cur} }")
        assert page.evaluate(COUNT) == {'yes': 0, 'no': 0}, 'typing answered the prompt'
        assert state == {'typed': 'yen', 'open': True}
        page.evaluate("() => __T.promptSet(null)")
        assert err.uncaught == []


    def test_open_modal_blocks_the_keys(self, street):
        page, err = street
        page.evaluate(TEST_PROMPT)
        page.evaluate(RESET)
        page.evaluate("() => { document.getElementById('modalRoot').innerHTML = '<p>test</p>' }")
        for key in ('e', 'Enter', 'y', 'Escape', 'n'):
            page.keyboard.press(key)
        assert page.evaluate(COUNT) == {'yes': 0, 'no': 0}, 'a key answered the prompt behind a modal'
        page.evaluate("() => { document.getElementById('modalRoot').innerHTML = ''; __T.promptSet(null) }")
        assert err.uncaught == []


    def test_enter_station_with_key(self, street):
        """The street prompt at the station doors. Last in the street's tests, because it leaves the street."""
        page, err = street
        page.evaluate("() => { const w = __T.CS_DOORS[0].w; __T.av.position.set(w.x, 0.01, w.z) }")
        assert game.wait_for(page, f"({SHOWN})() === 'Enter the station?'", 30), 'no "Enter the station?" prompt'
        page.evaluate(RESET)
        press(page, 'e')
        assert game.wait_for(page, "() => __T.CS.mode === 'station'", 60), f'E did not enter the station: {page.evaluate(COUNT)}'
        assert page.evaluate(COUNT) == {'yes': 1, 'no': 0}, 'E must answer Yes exactly once'
        assert err.uncaught == []
