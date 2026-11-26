"""Stage R2, slice (a): the world follows real time (docs/REALTIME_SPEC.md), applied to the real-time mode itself (owner,
2026-11-26: no separate switch for these corrections).

With real time on, under a fake real time: the date, the sun (against the sunrise-sunset.org references in tests/test_sun.py),
the season and the sky's inputs (the hour the sky shows, its night factor, the sun light) are those of that Stockholm moment
from the first frames in the city (on main the sky starts at 08:00 and eases over); crossing midnight never shows daylight
(on main the eased hour sweeps back through the day); the offline weather is rolled for the real month when the Stockholm day
changes and on a reload after days away (on main it goes stale); the election falls on a real Sunday.
With real time off (the old game clock), the game behaves as on main.

The fake time is installed before the game's scripts run: the page's StockholmLife namespace is a Proxy that calls
stockholm-time's own setFakeNow the moment that module registers (sessionStorage `slTestFakeNow` overrides it, for a reload).
Live weather (Open-Meteo) is blocked, so the offline weather is what the game shows. Run alone with:
python3 -m pytest tests/test_realtime_world.py"""
from datetime import datetime, timezone
import pytest
import game
from test_sun import REFERENCE, RISE_SET_TOL, LENGTH_TOL

EXPOSE = ('window.__R={get shownHour(){return shownHour},get REALTIME(){return REALTIME},'
          'sunrise,sunset,daylight,winter,lightAt,skyU,sun,fmtElection,exitInterior,get IN(){return IN},get CUT(){return CUT},get fake(){return window.StockholmLife["stockholm-time"]}};return API;')

FAKE = """(() => {
  let f = %d; try { const s = sessionStorage.getItem('slTestFakeNow'); if (s) f = +s } catch (e) {}
  globalThis.StockholmLife = new Proxy({}, { set(t, k, v) { t[k] = v; if (k === 'stockholm-time' && v && v.setFakeNow) v.setFakeNow(f); return true } });
})();"""

FRAMES = "async (n) => { for (let i = 0; i < n; i++) await new Promise(r => requestAnimationFrame(() => r())); return true }"
STATE = """() => { const S = window.__TS.S, R = window.__R; return {day: S.day, hour: S.hour, weather: S.weather, temp: S.temp, next: S.civ && S.civ.next,
  election: S.civ ? R.fmtElection() : '', date: document.getElementById('date').textContent, season: document.getElementById('season').textContent,
  shown: R.shownHour, night: R.lightAt(R.shownHour), sunLight: R.sun.intensity, rise: R.sunrise(), set: R.sunset(), length: R.daylight(), winter: !!R.winter(),
  realtime: R.REALTIME} }"""


def ms(*a):
    return int(datetime(*a, tzinfo=timezone.utc).timestamp() * 1000)


def open_game(browser, fake, realtime=True):
    body = game.hooked_html().replace('return API;', EXPOSE)
    ctx = game.new_context(browser, realtime=realtime, viewport={'width': 1366, 'height': 768})
    ctx.add_init_script(FAKE % fake)
    ctx.route('**/index.html', lambda route: route.fulfill(status=200, content_type='text/html; charset=utf-8', body=body))
    ctx.route('**/api.open-meteo.com/**', lambda route: route.abort())  # offline weather only
    page = ctx.new_page()
    err = game.Errors(page)
    game.boot(page, timeout=240)
    return ctx, page, err


def ready(page, arrival=True):
    assert game.wait_for(page, "() => window.__TS && window.__TS.S && window.__TS.S.name && window.__R", 90), 'no life started by itself'
    if arrival:
        # a new life lands at Arlanda (a cutscene, then the arrivals hall); neither draws the city sky, so skip the landing and step out into the city
        assert game.wait_for(page, "() => window.__R.CUT.on || window.__R.IN.on", 60), 'the arrival did not start'
        page.evaluate("() => { const b = document.querySelector('.cutcap button'); if (b) b.click() }")
        assert game.wait_for(page, "() => !window.__R.CUT.on && window.__R.IN.on", 60), 'the landing did not end in the arrivals hall'
        page.evaluate("() => { window.__TS.S.flags.arlanda = 0; window.__R.exitInterior(true) }")
    assert game.wait_for(page, "() => !window.__R.CUT.on && !window.__R.IN.on", 20), 'not in the city'
    game.clear_overlays(page)
    page.evaluate(FRAMES, 2)
    g = page.evaluate(STATE)
    # rain and snow are very slow to draw under software WebGL (a snowy frame blocked the page for 27 s), so the tests go on in clear weather
    page.evaluate("() => { window.__TS.S.weather = 'clear'; window.__T.render() }")
    return g


def set_fake(page, t):
    page.evaluate(f"() => window.__R.fake.setFakeNow({t})")


def reload_at(page, t):
    page.evaluate(f"() => {{ window.__TS.save(); sessionStorage.setItem('slTestFakeNow', '{t}') }}")
    page.reload(wait_until='load', timeout=120000)
    page.wait_for_function("() => !document.getElementById('loading')", timeout=240000)
    return ready(page, arrival=False)


def ref(date):
    return next(r for r in REFERENCE if r[0] == date)


CASES = {
    # 12:00 CEST on Sunday 21 June 2026 (the June solstice); the first election 56 days on is Sunday 16 August (life day 57)
    'midsummer-noon': dict(fake=ms(2026, 6, 21, 10, 0, 0), ref='2026-06-21', hour=12.0, date='sön 21 jun', season='Light nights', winter=False,
                           night=0.0, sun=True, next=57, election='sön 16 aug'),
    # 20:00 CET on Monday 21 December 2026; 56 days on is Monday 15 February 2027, so the election is Sunday 21 February (day 63)
    'midwinter-evening': dict(fake=ms(2026, 12, 21, 19, 0, 0), ref='2026-12-21', hour=20.0, date='mån 21 dec', season='Dark season', winter=True,
                              night=1.0, sun=False, next=63, election='sön 21 feb'),
}


@pytest.mark.parametrize('case', CASES, ids=list(CASES))
def test_date_sun_season_and_sky_follow_the_fake_real_time(browser, server, case):
    c = CASES[case]
    ctx, page, err = open_game(browser, c['fake'])
    try:
        g = ready(page)
        assert g['day'] == 1 and g['hour'] == pytest.approx(c['hour'], abs=1e-6), g
        assert g['date'].startswith(c['date']), g['date']
        _, rise, sset, length = ref(c['ref'])
        assert g['rise'] == pytest.approx(rise, abs=RISE_SET_TOL) and g['set'] == pytest.approx(sset, abs=RISE_SET_TOL), g
        assert g['length'] == pytest.approx(length, abs=LENGTH_TOL), g
        assert g['season'].startswith(c['season']) and g['winter'] is c['winter'], g
        # the sky shows the real hour from the first frames (on main it starts at the new life's 08:00 and eases over)
        assert g['shown'] == pytest.approx(g['hour'], abs=1e-9), g
        assert g['night'] == pytest.approx(c['night'], abs=1e-6) and (g['sunLight'] > 0) is c['sun'], g
        assert g['next'] == c['next'] and g['election'] == c['election'], g
        assert err.uncaught == []
    finally:
        ctx.close()


def test_no_daylight_across_midnight(browser, server):
    """23:59:50 to 00:00:10 on a midsummer night: the sky stays night in every frame (on main the eased hour sweeps back through the day)."""
    t = ms(2026, 6, 21, 21, 59, 50)  # 23:59:50 CEST
    ctx, page, err = open_game(browser, t)
    try:
        g = ready(page)
        assert g['day'] == 1 and g['night'] == 1 and g['sunLight'] == 0, g
        set_fake(page, t + 20000)
        assert game.wait_for(page, "() => window.__TS.S.day === 2", 90), 'the day did not change at midnight'
        frames = page.evaluate("""async () => { const out = [];
          for (let i = 0; i < 12; i++) { await new Promise(r => requestAnimationFrame(() => r())); out.push([window.__R.shownHour, window.__TS.S.hour, window.__R.sun.intensity]) }
          return out }""")
        assert all(s == 0 for _, _, s in frames), frames
        assert all(abs(h - real) < 1e-9 for h, real, _ in frames), frames
        assert page.evaluate("() => document.getElementById('date').textContent").startswith('mån 22 jun')
        assert err.uncaught == []
    finally:
        ctx.close()


def test_offline_weather_follows_the_real_day(browser, server):
    """A new Stockholm day and a reload 41 days later each roll the offline weather for the real month (rollWeather: June
    17 ± 3 °C, August 19 ± 3 °C, +2 when clear; no snow outside winter). A new life is rolled for the real month as on main.
    The weather before each change is marked with -30 °C, which no roll in June or August can give."""
    t = ms(2026, 6, 21, 21, 59, 50)
    ctx, page, err = open_game(browser, t)
    try:
        g = ready(page)
        assert g['weather'] in ('clear', 'cloud', 'rain') and 14 <= g['temp'] <= 22, g
        page.evaluate("() => { window.__TS.S.temp = -30 }")
        set_fake(page, t + 20000)
        assert game.wait_for(page, "() => window.__TS.S.day === 2", 90), 'the day did not change at midnight'
        g = page.evaluate(STATE)
        assert g['weather'] in ('clear', 'cloud', 'rain') and 14 <= g['temp'] <= 22, g
        page.evaluate("() => { const S = window.__TS.S; S.weather = 'clear'; S.temp = -30 }")
        g = reload_at(page, ms(2026, 8, 1, 10, 0, 0))  # 12:00 CEST on Saturday 1 August: life day 42
        assert g['day'] == 42 and g['date'].startswith('lör 1 aug'), g
        assert g['weather'] in ('clear', 'cloud', 'rain') and 16 <= g['temp'] <= 24, g
        assert err.uncaught == []
    finally:
        ctx.close()


def test_old_clock_unchanged(browser, server):
    """With real time off (the old game clock) nothing of R2 applies: the old calendar (day 1 = Saturday 24 October 2026), the
    intro, the election on the game's own calendar (day 58, Sunday 20 December 2026), and the sky still eases towards a new hour
    instead of jumping to it."""
    ctx, page, err = open_game(browser, ms(2026, 6, 21, 10, 0, 0), realtime=False)
    try:
        assert game.intro_shown(page), 'the intro is not showing'
        game.start_life(page)
        g = page.evaluate(STATE)
        assert not g['realtime'], g
        assert g['day'] == 1 and g['date'].startswith('lör 24 okt'), g
        assert g['next'] == 58 and g['election'] == 'sön 20 dec', g
        game.clear_overlays(page)
        eased = page.evaluate("""async () => { const S = window.__TS.S, R = window.__R; const from = R.shownHour; S.hour = (from + 6) % 24;
          for (let i = 0; i < 2; i++) await new Promise(r => requestAnimationFrame(() => r()));
          return [from, R.shownHour, S.hour] }""")
        assert eased[1] != pytest.approx(eased[2], abs=1e-6), f'the old clock no longer eases the sky: {eased}'
        assert err.uncaught == []
    finally:
        ctx.close()
