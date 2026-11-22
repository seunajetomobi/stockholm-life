"""The date in the top board carries the name day and the red day of the game date as its tooltip (src/rules/namnsdag.js, src/rules/holidays.js)."""
import game


def test_date_tooltip_has_the_name_day(browser, server):
    ctx, page, err = game.new_page(browser, hook=True)
    try:
        game.boot(page)
        game.start_life(page)
        # day 1 is Saturday 24 October 2026; its name day comes from the list, so compare with the module itself
        got = page.evaluate("() => [document.getElementById('date').title, window.StockholmLife.namnsdag.namnsdagOn(10, 24)]")
        assert got[1], 'no name day on 24 October in the list'
        assert got[0] == 'Namnsdag: ' + ', '.join(got[1]), got
        # day 8 is Saturday 31 October 2026, All Saints' Day, a red day; the board redraws by itself
        page.evaluate("() => { window.__TS.S.day = 8; window.__TS.S.hour = 12; window.__T.render() }")
        title = page.evaluate("() => document.getElementById('date').title")
        assert 'Röd dag: Alla helgons dag' in title, title
        assert err.uncaught == []
    finally:
        ctx.close()
