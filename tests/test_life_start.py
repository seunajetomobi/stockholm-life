"""src/rules/life-start.js: the real start of a life, so that game day N is a real Stockholm calendar day (docs/REALTIME_SPEC.md R1b).

Node only (seconds, no browser). Run alone with: python3 -m pytest tests/test_life_start.py"""
import json
import subprocess
import pytest
import game

SRC = game.ROOT / 'src' / 'rules'


def node(js, tz='UTC'):
    code = f"const L=require({json.dumps(str(SRC / 'life-start.js'))}),T=require({json.dumps(str(SRC / 'stockholm-time.js'))});{js}"
    r = subprocess.run(['node', '-e', code], capture_output=True, text=True, timeout=60, env={'PATH': '/usr/bin:/bin:/usr/local/bin', 'TZ': tz})
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_interface():
    assert node("console.log(JSON.stringify(Object.keys(L).sort()))") == ['ensureLifeStart', 'lifeStartFor']


@pytest.mark.parametrize('tz', ['UTC', 'America/Los_Angeles', 'Asia/Tokyo', 'Europe/Stockholm'])
def test_day_one_starts_at_todays_stockholm_midnight(tz):
    # 2026-11-21 10:00 UTC = 11:00 in Stockholm (winter time, UTC+1); midnight began at 2026-11-20 23:00 UTC.
    now = "Date.UTC(2026,10,21,10,0,0)"
    assert node(f"console.log(L.lifeStartFor(1,{now}))", tz) == node("console.log(Date.UTC(2026,10,20,23,0,0))", tz)


@pytest.mark.parametrize('day', [1, 2, 7, 30, 200])
def test_the_life_day_of_now_is_the_saved_day(day):
    r = node(f"const n=Date.UTC(2026,10,21,10,0,0),t=L.lifeStartFor({day},n);console.log(T.lifeDay(t,n))")
    assert r == day


def test_across_the_october_clock_change():
    # 2026-10-25 is 25 hours long. Day 8 now (2026-11-01 at 12:00 UTC) began on 2026-10-25: the life day count must still be 8.
    r = node("const n=Date.UTC(2026,10,1,12,0,0),t=L.lifeStartFor(8,n);console.log([T.lifeDay(t,n),T.hourAt(t),T.partsAt(t).day,T.partsAt(t).month])")
    assert r == [8, 0, 25, 10]


def test_across_the_march_clock_change():
    r = node("const n=Date.UTC(2027,2,29,12,0,0),t=L.lifeStartFor(3,n);console.log([T.lifeDay(t,n),T.hourAt(t),T.partsAt(t).day,T.partsAt(t).month])")
    assert r == [3, 0, 27, 3]


def test_ensure_sets_a_missing_start_and_keeps_a_good_one():
    r = node("const n=Date.UTC(2026,10,21,10,0,0),a=L.ensureLifeStart({day:5},n),b=L.ensureLifeStart({day:5,t0:a.t0},n+1000);console.log([a.t0===L.lifeStartFor(5,n),b.t0===a.t0])")
    assert r == [True, True]


@pytest.mark.parametrize('bad', ['null', 'undefined', '"x"', 'NaN', '0', '-5', 'Date.UTC(2099,0,1)'])
def test_ensure_repairs_an_unusable_start(bad):
    r = node(f"const n=Date.UTC(2026,10,21,10,0,0),s=L.ensureLifeStart({{day:2,t0:{bad}}},n);console.log(s.t0===L.lifeStartFor(2,n))")
    assert r is True


def test_ensure_is_idempotent_and_handles_odd_input():
    r = node("const n=Date.UTC(2026,10,21,10,0,0),s=L.ensureLifeStart({},n),t=s.t0;L.ensureLifeStart(s,n);console.log([s.t0===t,s.t0===L.lifeStartFor(1,n),L.ensureLifeStart(null,n)])")
    assert r == [True, True, None]


@pytest.mark.parametrize('day', [0, -1, 'NaN'])
def test_start_for_rejects_a_day_below_one(day):
    r = subprocess.run(['node', '-e', f"require({json.dumps(str(SRC / 'life-start.js'))}).lifeStartFor({day},Date.now())"], capture_output=True, text=True)
    assert r.returncode != 0 and 'RangeError' in r.stderr
