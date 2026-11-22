"""A Swedish public holiday keeps Sunday opening hours (Lag 1989:253 via src/rules/holidays.js): the same Saturday is open or shut depending on whether it is a red day.

Day 1 is Saturday 24 October 2026 (an ordinary Saturday); day 8 is Saturday 31 October 2026, Alla helgons dag, a red day."""
import game


def test_systembolaget_is_shut_on_a_red_saturday_but_open_on_a_normal_one(browser, server):
    ctx, page, err = game.new_page(browser, hook=True)
    try:
        game.boot(page)
        game.start_life(page)
        r = page.evaluate("""() => { const T = window.__TS, K = window.__T, out = {};
          for (const d of [1, 8, 9]) { T.S.day = d; out[d] = [K.openDay(), K.isOpen('sys', 12, 0), K.isOpen('sys', 11, 1)] }
          return out }""")
        assert r['1'] == [6, True, True], r      # Saturday 24 Oct: Sat hours 10-15
        assert r['8'] == [0, False, False], r    # Saturday 31 Oct, Alla helgons dag: like a Sunday, shut
        assert r['9'] == [0, False, False], r    # Sunday 1 Nov
        assert err.uncaught == []
    finally:
        ctx.close()
