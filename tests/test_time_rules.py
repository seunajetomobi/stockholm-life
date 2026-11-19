"""Pins how game time passes and what it triggers today (M2 preparation; docs/M2_SPEC.md §2). They test the game as it is and change nothing in it.

Everything runs the production functions (`spendTime`, `sleep`, `needsTick`, `processBills`, `garnish`, `addBill`, `dateOf`) on a life set to fixed values, with
`Math.random` fixed so that no event, illness or weather roll can happen. Game time is the state itself (`S.day`, `S.hour`), so nothing waits on the clock.
The names come from `window.__V`, added with the test hook as in test_transit_rides.py; index.html is not changed.
Run alone with: python3 -m pytest tests/test_time_rules.py"""
import json
import pytest
import game

EXPOSE = ('window.__V={get spendTime(){return spendTime},get sleep(){return sleep},needsTick,processBills,garnish,addBill,dateOf,HOMES,TAX,BILLSTAGE,'
          'billTotal,clamp,MONTHS,START,QUEUE_FEE,csnResident,courseAct,get BARNBIDRAG(){return BARNBIDRAG},get CSN4W(){return CSN4W}};return API;')


@pytest.fixture(scope='module')
def city(browser):
    body = game.hooked_html().replace('return API;', EXPOSE)
    ctx = browser.new_context(viewport={'width': 1366, 'height': 768})
    ctx.route('**/index.html', lambda route: route.fulfill(status=200, content_type='text/html; charset=utf-8', body=body))
    page = ctx.new_page()
    err = game.Errors(page)
    game.boot(page, timeout=240)
    game.start_life(page)
    game.clear_overlays(page)
    yield page
    ctx.close()
    assert err.uncaught == []


# a life at fixed values, at home, with no job, bank account, bills, kids or sickness; Math.random fixed so that nothing is rolled
SETUP = """(over) => { const S = window.__TS.S, V = window.__V; Math.random = () => 0.999;
  Object.assign(S, {money: 50000, day: 3, hour: 12, hunger: 80, hygiene: 80, fun: 70, mood: 50, energy: 70, social: 50, sick: 0, job: null, jobDays: 0, pay: 0, bills: [],
    home: 'soderRoom', addr: {x: 10, z: 10}, pos: {x: 10, z: 10}, weather: 'clear', sunToday: false, coat: 0, kids: [], preg: null, course: null, car: null, applied: {}});
  S.log = []; S.csnLoan = 0; S.docs.bank = 1; S.docs.queue = 0; S.docs.pn = 1; S.docs.permit = 1; S.flags.sambo = 0; S.flags.karens = 0; S.flags.csn = 0; S.vitD = 1e9; S.flags.jourDay = 0;
  Object.assign(S, over || {}); return true }"""
SNAP = "() => { const S = window.__TS.S; return {money: S.money, day: S.day, hour: S.hour, hunger: S.hunger, hygiene: S.hygiene, fun: S.fun, mood: S.mood, energy: S.energy, social: S.social, pay: S.pay, home: S.home, bills: JSON.parse(JSON.stringify(S.bills || [])), log: S.log.slice(0, 6).map(l => l.t)} }"


def run(page, over, call):
    """Set the life, run `call` (JS), return the state after."""
    page.evaluate(SETUP, over)
    page.evaluate(f"() => {{ {call} }}")
    return page.evaluate(SNAP)


def approx(**kw):
    return {k: pytest.approx(v, abs=1e-6) for k, v in kw.items()}


def check(got, **want):
    for k, v in want.items():
        assert got[k] == pytest.approx(v, abs=1e-6), f'{k}: {got[k]} != {v} in {got}'


def logged(got, text):
    assert any(text in l for l in got['log']), (text, got['log'])


def not_logged(got, text):
    assert not any(text in l for l in got['log']), (text, got['log'])


# ---------- the calendar: day 1 is Saturday 24 October 2026; `sleep` moves to the next day and reads the date of the new day ----------
def test_calendar_days(city):
    d = city.evaluate("() => { const V = window.__V, f = n => { const x = V.dateOf(n); return [x.getFullYear(), x.getMonth() + 1, x.getDate(), x.getDay()] };"
                      " return [1, 2, 8, 9, 33, 39, 70, 71].map(f) }")
    assert d == [[2026, 10, 24, 6], [2026, 10, 25, 0], [2026, 10, 31, 6], [2026, 11, 1, 0], [2026, 11, 25, 3], [2026, 12, 1, 2], [2027, 1, 1, 5], [2027, 1, 2, 6]], d


# ---------- needs ----------
def test_needs_per_hour(city):
    """`spendTime(h)` (and `needsTick(h)`, which it calls): hunger -6, hygiene -2.8, fun -2.4 an hour, the clock moves by h, energy and mood are untouched above the thresholds."""
    g = run(city, {}, 'window.__V.spendTime(2)')
    check(g, hunger=68, hygiene=74.4, fun=65.2, hour=14, mood=50, energy=70, day=3)
    g = run(city, {}, 'window.__V.spendTime(0.25)')
    check(g, hunger=78.5, hygiene=79.3, fun=69.4, hour=12.25)
    # nothing for zero or negative time
    for h in (0, -1):
        g = run(city, {}, f'window.__V.needsTick({h}); window.__V.spendTime({h})')
        check(g, hunger=80, hygiene=80, fun=70, hour=12 + (h if h < 0 else 0))   # spendTime(-1) still moves the clock back; needsTick ignores it


def test_needs_mood_and_energy_thresholds(city):
    """Below 20 hunger costs 1.5 mood an hour, below 20 hygiene 0.6, below 15 fun 0.8; hunger below 8 costs 2 energy an hour. The test is on the value after the drop."""
    g = run(city, {'hunger': 26}, 'window.__V.spendTime(1)')       # 20: not below 20
    check(g, hunger=20, mood=50)
    g = run(city, {'hunger': 25}, 'window.__V.spendTime(1)')       # 19: below
    check(g, hunger=19, mood=48.5, energy=70)
    g = run(city, {'hygiene': 22.9}, 'window.__V.spendTime(1)')    # 20.1: not below 20 (values away from the exact edge, which floating point decides)
    check(g, hygiene=20.1, mood=50)
    g = run(city, {'hygiene': 22.6}, 'window.__V.spendTime(1)')
    check(g, hygiene=19.8, mood=49.4)
    g = run(city, {'fun': 17.5}, 'window.__V.spendTime(1)')        # 15.1: not below 15
    check(g, fun=15.1, mood=50)
    g = run(city, {'fun': 17.2}, 'window.__V.spendTime(1)')
    check(g, fun=14.8, mood=49.2)
    g = run(city, {'hunger': 13.9}, 'window.__V.spendTime(1)')     # 7.9: hungry, and weak
    check(g, hunger=7.9, mood=48.5, energy=68)
    g = run(city, {'hunger': 3, 'hygiene': 3, 'fun': 3, 'mood': 3}, 'window.__V.spendTime(1)')   # everything floors at 0
    check(g, hunger=0, hygiene=0.2, fun=0.6, mood=0.1, energy=68)   # mood 3 - 1.5 - 0.6 - 0.8


def test_clock_runs_past_midnight_into_sleep(city):
    """`spendTime` that reaches 24:00 does the whole needs drop first, then `sleep(true)`: the player nods off on the night bus, the next day starts at 08:00."""
    g = run(city, {'hour': 23.5}, 'window.__V.spendTime(1)')
    check(g, day=4, hour=8, hunger=80 - 6 - 18, hygiene=80 - 2.8 - 8, energy=100, mood=44, social=48)
    logged(g, 'nodded off on the night bus')
    g = run(city, {'hour': 23}, 'window.__V.spendTime(0.99)')      # 23.99 is still today
    check(g, day=3, hour=23.99)


# ---------- day change ----------
def test_sleep_at_home(city):
    """`sleep` at home: day +1, 07:00, energy +60, hunger -18, hygiene -8, social -2; sick, energy stops at 60; very low energy costs 3 mood."""
    g = run(city, {}, 'window.__V.sleep(false)')
    check(g, day=4, hour=7, hunger=62, hygiene=72, fun=70, mood=50, energy=100, social=48, money=50000)
    logged(g, 'tis 27 okt. Sunrise')
    g = run(city, {'sick': 8}, 'window.__V.sleep(false)')
    check(g, day=4, energy=60)
    g = run(city, {'energy': 10}, 'window.__V.sleep(false)')
    check(g, mood=47, energy=70)


@pytest.mark.parametrize('mode,hour,energy,mood,hunger,hygiene', [
    ('hospital', 9, 70, 50, 62 + 30, 72 + 20),
    ('cell', 10, 45, 40, 62 + 15, 72 - 10),
    ('jail', 7, 75, 47, 62 + 30, 72 + 25),
    ('trip', 8, 85, 50, 62, 72 + 30),
    ('shelter', 7, 75, 46, 62 + 25, 72 + 40),
    ('friend', 8, 70, 48, 62, 72),
])
def test_sleep_modes(city, mode, hour, energy, mood, hunger, hygiene):
    """The ways a night can pass (hospital, cell, jail, a trip, the shelter, a friend's sofa) set the hour and change energy, mood, hunger and hygiene by fixed amounts."""
    g = run(city, {'energy': 30}, f"window.__V.sleep(false, '{mode}')")
    check(g, day=4, hour=hour, energy=energy, mood=mood, hunger=min(hunger, 100), hygiene=min(hygiene, 100), social=48)


def test_sleep_away_from_home_and_out(city):
    g = run(city, {'energy': 30, 'pos': {'x': 90, 'z': 90}}, 'window.__V.sleep(false)')   # not at the address
    check(g, day=4, hour=8, energy=65, mood=44)
    logged(g, "Crashed on a friend's sofa")
    g = run(city, {'energy': 30, 'home': 'none', 'addr': None}, 'window.__V.sleep(false)')   # no home: sleeps out
    check(g, day=4, hour=6.5, energy=55, mood=35, hygiene=72 - 20)
    logged(g, 'You slept outside')


# ---------- rent, salary, bills on the date of the new day ----------
def test_rent_on_the_first(city):
    """Rent is taken (HOMES[home].rent, half if sambo) when the new day is the 1st; with too little money it becomes a bill and costs 6 mood. Not on other days."""
    g = run(city, {'day': 8}, 'window.__V.sleep(false)')           # day 9 is Sunday 1 November
    check(g, day=9, money=50000 - 7900)
    logged(g, 'Rent paid for nov: −7 900 kr.')
    g = run(city, {'day': 8}, "window.__TS.S.flags.sambo = 1; window.__V.sleep(false)")
    check(g, money=50000 - 3950)
    g = run(city, {'day': 8, 'money': 5000}, 'window.__V.sleep(false)')
    check(g, money=5000, mood=44)
    assert g['bills'] == [{'what': 'rent for nov', 'amt': 7900, 'fees': 0, 'stage': 0, 'due': 19}], g['bills']
    g = run(city, {'day': 7}, 'window.__V.sleep(false)')           # the 31st: nothing
    check(g, day=8, money=50000)
    g = run(city, {'day': 8, 'car': {'kind': 'own'}}, 'window.__V.sleep(false)')
    check(g, money=50000 - 7900 - 1100)
    g = run(city, {'day': 70, 'docs_queue': 1}, "window.__TS.S.docs.queue = 1; window.__V.sleep(false)")   # 2 January: the housing-queue fee
    logged(g, 'Bostadsförmedlingen yearly queue fee')
    assert g['money'] < 50000 and g['day'] == 71


def test_payday_on_the_25th(city):
    """Lönedag: with a bank account the month's pay, less 30% tax, is paid and mood +5; without one nothing is paid and the pay stays."""
    g = run(city, {'day': 32, 'pay': 10000}, 'window.__V.sleep(false)')    # day 33 is Wednesday 25 November
    check(g, day=33, money=50000 + 7000, pay=0, mood=55)
    logged(g, 'Lönedag! 10 000 kr gross, 7 000 kr after')
    not_logged(g, "can't be paid")                                          # M26: no failure warning after a successful payment
    g = run(city, {'day': 32, 'pay': 10000}, 'window.__TS.S.docs.bank = 0; window.__V.sleep(false)')
    check(g, money=50000, pay=10000, mood=50)
    logged(g, "Lönedag, but your lön can't be paid: you have no bank account.")
    not_logged(g, 'Lönedag! ')
    g = run(city, {'day': 31, 'pay': 10000}, 'window.__V.sleep(false)')    # the 24th: nothing
    check(g, money=50000, pay=10000)
    g = run(city, {'day': 32, 'pay': 0}, 'window.__V.sleep(false)')
    check(g, money=50000, mood=50)
    # no CSN flag: no CSN, and no lön with no bank account gives no warning (nothing is due)
    g = run(city, {'day': 32, 'pay': 10000, 'course': 'x'}, 'window.__V.sleep(false)')
    check(g, money=50000 + 7000)
    not_logged(g, 'CSN studiemedel')
    g = run(city, {'day': 32, 'pay': 0}, 'window.__TS.S.docs.bank = 0; window.__V.sleep(false)')
    not_logged(g, "can't be paid")


CSN = "window.__TS.S.flags.csn = 1; "


def test_csn_rules(city):
    """CSN studiemedel (13 592 kr on the 25th, 70% of it a loan): paid to a student who has permanent residence (a residence permit card and a personnummer)
    and an active bank account on the payment date, whether or not there is any lön; it stops with the course. M26 part 2."""
    # an unemployed resident student with a bank account is paid, and 70% of it becomes loan
    g = run(city, {'day': 32, 'pay': 0, 'course': {'id': 'sva', 'done': 1}}, CSN + "window.__V.sleep(false)")
    check(g, money=50000 + 13592)
    logged(g, 'CSN studiemedel paid: +13 592 kr')
    not_logged(g, "can't be paid")                                          # no lön due, so no salary warning
    assert city.evaluate("() => window.__TS.S.csnLoan") == 9514             # round(13 592 x 0.7), the balance that repayment will draw down
    # a student with lön gets both, and the salary is unchanged
    g = run(city, {'day': 32, 'pay': 10000, 'course': {'id': 'sva', 'done': 1}}, CSN + "window.__V.sleep(false)")
    check(g, money=50000 + 7000 + 13592, pay=0, mood=55)
    logged(g, 'Lönedag! 10 000 kr gross, 7 000 kr after')
    logged(g, 'CSN studiemedel paid')
    # without permanent residence (no permit card, or no personnummer): not paid
    for field in ('permit', 'pn'):
        g = run(city, {'day': 32, 'pay': 0, 'course': {'id': 'sva', 'done': 1}}, CSN + f"window.__TS.S.docs.{field} = 0; window.__V.sleep(false)")
        check(g, money=50000)
        not_logged(g, 'CSN studiemedel paid')
        assert city.evaluate("() => window.__TS.S.csnLoan || 0") == 0
    # no bank account on the payment date: not paid, and it says why (also when the account existed when CSN was approved)
    g = run(city, {'day': 32, 'pay': 0, 'course': {'id': 'sva', 'done': 1}}, CSN + "window.__TS.S.docs.bank = 0; window.__V.sleep(false)")
    check(g, money=50000)
    logged(g, 'CSN studiemedel could not be paid: you have no bank account.')
    assert city.evaluate("() => window.__TS.S.csnLoan || 0") == 0
    # with lön due and no bank account: the lön waits with its warning, and CSN is not paid either
    g = run(city, {'day': 32, 'pay': 10000, 'course': {'id': 'sva', 'done': 1}}, CSN + "window.__TS.S.docs.bank = 0; window.__V.sleep(false)")
    check(g, money=50000, pay=10000)
    logged(g, "Lönedag, but your lön can't be paid: you have no bank account.")
    # no CSN approval, or no course: no CSN
    g = run(city, {'day': 32, 'pay': 0, 'course': {'id': 'sva', 'done': 1}}, "window.__V.sleep(false)")
    check(g, money=50000)
    g = run(city, {'day': 32, 'pay': 0}, CSN + "window.__V.sleep(false)")
    check(g, money=50000)
    # one payment per 25th: the 26th and the 24th pay nothing
    g = run(city, {'day': 33, 'pay': 0, 'course': {'id': 'sva', 'done': 1}}, CSN + "window.__V.sleep(false)")
    check(g, money=50000)
    g = run(city, {'day': 31, 'pay': 0, 'course': {'id': 'sva', 'done': 1}}, CSN + "window.__V.sleep(false)")
    check(g, money=50000)


def test_csn_stops_when_the_course_is_finished(city):
    """Finishing the last session ends the course and the CSN approval, so the next 25th pays nothing (this part already worked; now pinned)."""
    run(city, {'day': 31, 'pay': 0, 'course': {'id': 'sva', 'done': 7}}, CSN)    # 'sva' has 8 sessions: this is the last one
    city.evaluate("() => { const a = window.__V.courseAct(); a.fn() }")
    st = city.evaluate("() => ({course: window.__TS.S.course, csn: window.__TS.S.flags.csn, cert: !!window.__TS.S.certs.sva})")
    assert st == {'course': None, 'csn': 0, 'cert': True}, st
    g = run(city, {'day': 32, 'pay': 0, 'course': None}, "window.__V.sleep(false)")
    check(g, money=50000)
    not_logged(g, 'CSN studiemedel')


def test_csn_application_needs_permanent_residence(city):
    """The Apply button refuses without a residence permit card and a personnummer (a student can no longer be approved without them)."""
    run(city, {'course': {'id': 'sva', 'done': 0}}, "window.__TS.S.docs.bankid = 1; window.__TS.S.docs.permit = 0")
    assert city.evaluate("() => window.__V.csnResident()") is False
    run(city, {'course': {'id': 'sva', 'done': 0}}, "window.__TS.S.docs.bankid = 1")
    assert city.evaluate("() => window.__V.csnResident()") is True


def test_garnishing_takes_30_percent_of_the_net_pay(city):
    """Kronofogden takes 30% of the net pay for bills at stage 4, fees first."""
    bill = {'what': 'old', 'amt': 2000, 'fees': 500, 'stage': 4, 'due': 1e9}
    g = run(city, {'day': 32, 'pay': 10000, 'bills': [bill]}, 'window.__V.sleep(false)')
    check(g, money=50000 + 7000 - 2100)
    assert g['bills'][0]['fees'] == 0 and g['bills'][0]['amt'] == 400, g['bills']
    logged(g, 'Kronofogden took 2 100 kr')


def test_bill_stages(city):
    """An unpaid bill goes invoice, reminder (+60), inkasso (+180, -4 mood), Kronofogden order (+680, -8), utslag (-12, rent: eviction in 14 days), each when the day reaches its due day."""
    g = run(city, {'day': 3}, "window.__V.addBill('test', 1000)")
    assert g['bills'] == [{'what': 'test', 'amt': 1000, 'fees': 0, 'stage': 0, 'due': 13}], g['bills']
    steps = [(12, 0, 0, 13, 50), (13, 1, 60, 23, 50), (23, 2, 240, 31, 46), (31, 3, 920, 41, 42), (41, 4, 920, 1e9, 38)]   # the mood is reset before each step: this is that step's cost
    for day, stage, fees, due, mood in steps:
        g = run(city, {'day': day}, "window.__TS.S.bills = " + json.dumps(g['bills']) + "; window.__V.processBills()")
        assert g['bills'][0]['stage'] == stage and g['bills'][0]['fees'] == fees and g['bills'][0]['due'] == due, (day, g['bills'])
        check(g, mood=mood)
    assert city.evaluate("() => window.__TS.S.remark") == 41, 'utslag marks the betalningsanmärkning on that day'


def test_bill_stages_by_sleeping(city):
    """The same, driven by the day change: `sleep` calls `processBills` after the new day starts."""
    bill = {'what': 'test', 'amt': 1000, 'fees': 0, 'stage': 0, 'due': 13}
    g = run(city, {'day': 11, 'bills': [dict(bill)]}, 'window.__V.sleep(false)')   # day 12: not due
    assert g['bills'][0]['stage'] == 0
    g = run(city, {'day': 12, 'bills': [dict(bill)]}, 'window.__V.sleep(false)')   # day 13: reminder
    assert (g['bills'][0]['stage'], g['bills'][0]['fees'], g['bills'][0]['due']) == (1, 60, 23)
    logged(g, 'Påminnelse: test is overdue. +60 kr reminder fee.')
    g = run(city, {'day': 22, 'bills': [{**bill, 'stage': 1, 'fees': 60, 'due': 23}]}, 'window.__V.sleep(false)')
    assert (g['bills'][0]['stage'], g['bills'][0]['fees'], g['bills'][0]['due']) == (2, 240, 31)
    check(g, mood=46)


def test_unpaid_rent_ends_in_eviction(city):
    """A rent bill at utslag gets an eviction day 14 days on; when the day comes the player loses the home."""
    g = run(city, {'day': 40, 'bills': [{'what': 'rent for nov', 'amt': 7900, 'fees': 920, 'stage': 3, 'due': 41}]}, 'window.__V.sleep(false)')
    assert g['bills'][0]['stage'] == 4 and g['bills'][0]['evict'] == 41 + 14, g['bills']
    check(g, mood=38)
    g = run(city, {'day': 54, 'bills': [{'what': 'rent for nov', 'amt': 7900, 'fees': 920, 'stage': 4, 'due': 1e9, 'evict': 55}]}, 'window.__V.sleep(false)')
    assert g['home'] == 'none'
    check(g, mood=25)
    logged(g, 'Kronofogden carried out an eviction')


def test_child_benefit_on_the_20th(city):
    # the day that is the 20th
    day = city.evaluate("() => { for (let d = 3; d < 60; d++) if (window.__V.dateOf(d).getDate() === 20) return d }")
    g = run(city, {'day': day - 1, 'kids': [{'n': 'A', 'born': 1}]}, 'window.__V.sleep(false)')
    check(g, money=50000 + 1250)
    logged(g, 'Barnbidrag from Försäkringskassan: +1 250 kr.')


# ---------- the other ways the clock moves ----------
def test_walking_and_driving_advance_the_clock(city):
    """A walk committed with `__slCommit(dist, run, x, z)` advances S.hour by (walked * 50 / 80 + ran * 50 / 160) / 60 hours and drops the needs by that; a drive by dist * 50 / 450 minutes."""
    g = run(city, {}, 'window.__slCommit(8, 0, 12, 12)')            # 8 units walked: 5 minutes
    check(g, hour=12 + 5 / 60, hunger=80 - 6 * 5 / 60)
    g = run(city, {}, 'window.__slCommit(8, 8, 12, 12)')            # 8 units run: 2.5 minutes
    check(g, hour=12 + 2.5 / 60)
    g = run(city, {}, 'window.__slDrive(9, 12, 12)')                # 9 units driven: 1 minute
    check(g, hour=12 + 1 / 60, hunger=80 - 6 / 60)


def test_time_does_not_pass_while_standing_still(city):
    """Today game time moves only when something spends it (an action, a walk, a drive, a ride, sleep): standing still for several frames changes neither the hour nor the needs.
    M2 is meant to change this (docs/M2_SPEC.md §5); update this test then, on purpose."""
    run(city, {}, '')
    before = city.evaluate(SNAP)
    city.evaluate("() => new Promise(r => { let n = 0; const f = () => ++n >= 4 ? r() : requestAnimationFrame(f); requestAnimationFrame(f) })")
    after = city.evaluate(SNAP)
    assert (before['hour'], before['day'], before['hunger'], before['hygiene'], before['fun'], before['energy']) == (after['hour'], after['day'], after['hunger'], after['hygiene'], after['fun'], after['energy']), (before, after)
