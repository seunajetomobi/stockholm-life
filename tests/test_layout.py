"""Responsive layout: no sideways scrolling, and the main controls inside the screen, at two phone widths and desktop."""
import pytest
import game

pytestmark = pytest.mark.browser
SIZES = [(390, 844, True), (520, 900, True), (1366, 768, False)]
CONTROLS = {'dock': '#dock', 'joystick': '#joy', 'run': '#runbtn', 'zoom': '.ctrls', 'places': '#places'}


@pytest.mark.parametrize('w,h,mobile', SIZES, ids=[f'{w}x{h}' for w, h, _ in SIZES])
def test_layout(browser, w, h, mobile):
    ctx, page, err = game.new_page(browser, w, h, mobile=mobile)
    try:
        game.boot(page)
        assert game.overflow_x(page) == 0, 'horizontal overflow on the intro'
        game.start_life(page, mobile=mobile)
        game.shot(page, f'layout-{w}')
        assert game.overflow_x(page) == 0, 'horizontal overflow while playing'
        seen = game.boxes(page, CONTROLS)
        assert 'dock' in seen, 'dock not visible'
        if mobile:
            assert 'joystick' in seen, 'joystick not visible on a touch screen'
        outside = {k: [round(v) for v in b] for k, b in seen.items() if b[0] < -1 or b[1] < -1 or b[2] > w + 1 or b[3] > h + 1}
        assert outside == {}, 'controls outside the viewport'
        assert err.uncaught == []
    finally:
        ctx.close()
