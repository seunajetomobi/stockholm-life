"""Real time is the default: the game starts at once, with no intro, and the clock and date are Stockholm's own (src/rules/realtime.js)."""
import game

STOCKHOLM_NOW = """() => { const p = window.StockholmLife['stockholm-time'].partsAt(Date.now());
  return {y: p.year, m: p.month, d: p.day, h: p.hour, min: p.minute} }"""


def test_starts_at_once_on_stockholm_time(browser, server):
    ctx, page, err = game.new_page(browser, hook=True, realtime=True)
    try:
        game.boot(page)
        # no intro: a life exists without clicking Start, and no start dialog is open
        assert game.wait_for(page, "() => window.__TS && window.__TS.S && window.__TS.S.name", 60), 'no life started by itself'
        assert page.evaluate("() => !document.querySelector('.modal.open, #modal.open, .modal:not(.hidden) #go')"), 'the intro is showing'
        now = page.evaluate(STOCKHOLM_NOW)
        got = page.evaluate("() => { const S = window.__TS.S; return {day: S.day, hour: S.hour, t0: S.t0, time: document.getElementById('time').textContent, date: document.getElementById('date').textContent} }")
        assert got['day'] == 1, got
        hh, mm = got['time'].split(':')
        assert abs((int(hh) * 60 + int(mm)) - (now['h'] * 60 + now['min'])) <= 2, (got, now)
        assert str(now['d']) in got['date'], (got['date'], now)
        assert err.uncaught == []
    finally:
        ctx.close()


def test_old_clock_still_available_with_realtime_off(browser, server):
    ctx, page, err = game.new_page(browser, hook=True)
    try:
        game.boot(page)
        game.start_life(page)
        assert page.evaluate("() => window.__TS.S.day") == 1
        assert 'okt' in page.evaluate("() => document.getElementById('date').textContent")
        assert err.uncaught == []
    finally:
        ctx.close()


def test_sick_pay_is_added_once_per_calendar_day(browser, server):
    """Sleeping twice on the same real-time day must not pay sjukpenning twice (Codex review of #53)."""
    ctx, page, err = game.new_page(browser, hook=True, realtime=True)
    try:
        game.boot(page)
        assert game.wait_for(page, "() => window.__TS && window.__TS.S && window.__TS.S.name", 60)
        pays = page.evaluate("""() => { const S = window.__TS.S;
          S.job = 'barista'; S.docs.fk = 1; S.flags.karens = 1; S.sick = S.day + 5; S.pay = 0; S.home = S.home === 'none' ? 'room' : S.home;
          const out = [];
          for (let i = 0; i < 3; i++) { window.__TS.sleep(false); out.push(S.pay) }
          return out }""")
        assert pays[1] == pays[0] and pays[2] == pays[0], pays
        assert err.uncaught == []
    finally:
        ctx.close()
