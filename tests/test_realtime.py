"""src/rules/realtime.js: the real-time flag, the derived clock and the developer-only fake clock.

Node only. Run alone with: python3 -m pytest tests/test_realtime.py"""
import json
import subprocess
import pytest
import game

SRC = game.ROOT / 'src' / 'rules'


def node(js, tz='UTC'):
    code = f"const R=require({json.dumps(str(SRC / 'realtime.js'))}),T=require({json.dumps(str(SRC / 'stockholm-time.js'))});const st=o=>({{getItem:k=>k in o?o[k]:null}});{js}"
    r = subprocess.run(['node', '-e', code], capture_output=True, text=True, timeout=60, env={'PATH': '/usr/bin:/bin:/usr/local/bin', 'TZ': tz})
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_interface():
    assert node("console.log(JSON.stringify(Object.keys(R).sort()))") == ['deriveClock', 'enabled', 'fakeNow']


@pytest.mark.parametrize('search,store,want', [
    ('', '{}', False), ('?realtime=1', '{}', True), ('?realtime=0', '{"stockholmsliv-realtime":"1"}', False),
    ('', '{"stockholmsliv-realtime":"1"}', True), ('?realtime=yes', '{}', False), ('?x=1&realtime=1', '{}', True)])
def test_flag(search, store, want):
    assert node(f"console.log(R.enabled({json.dumps(search)},st({store})))") is want


def test_flag_survives_missing_or_broken_storage():
    r = node("console.log(JSON.stringify([R.enabled('',null),R.enabled('',undefined),R.enabled('',{getItem(){throw new Error('x')}}),R.enabled('?realtime=1',null)]))")
    assert r == [False, False, False, True]


@pytest.mark.parametrize('tz', ['UTC', 'Asia/Tokyo', 'America/Los_Angeles'])
def test_derived_clock_is_stockholm_time_whatever_the_machine_zone(tz):
    # life began 2026-11-20 00:00 Stockholm (= 2026-11-19 23:00 UTC); now 2026-11-21 13:30 UTC = 14:30 Stockholm, day 2
    r = node("const t0=Date.UTC(2026,10,19,23,0,0),n=Date.UTC(2026,10,21,13,30,0);console.log(JSON.stringify(R.deriveClock(t0,n)))", tz)
    assert r == {'day': 2, 'hour': 14.5}


def test_derived_clock_across_the_clock_change():
    # 2026-10-25 has 25 hours: 02:30 happens twice (00:30Z and 01:30Z). Life began 2026-10-24 00:00 Stockholm: both are day 2, hour 2.5;
    # the next Stockholm midnight is 2026-10-25 23:00Z, so 23:30Z is day 3, hour 0.5 and 22:59Z is still day 2.
    r = node("const t0=T.startOfDay(Date.UTC(2026,9,24,12)),f=m=>R.deriveClock(t0,m);console.log(JSON.stringify([f(Date.UTC(2026,9,25,0,30)),f(Date.UTC(2026,9,25,1,30)),f(Date.UTC(2026,9,25,22,59)).day,f(Date.UTC(2026,9,25,23,30))]))")
    assert r == [{'day': 2, 'hour': 2.5}, {'day': 2, 'hour': 2.5}, 2, {'day': 3, 'hour': 0.5}]


def test_derived_clock_midnight_is_day_change():
    r = node("const t0=Date.UTC(2026,10,19,23,0,0);console.log(JSON.stringify([R.deriveClock(t0,Date.UTC(2026,10,20,22,59,59)),R.deriveClock(t0,Date.UTC(2026,10,20,23,0,0))]))")
    assert r[0]['day'] == 1 and r[0]['hour'] > 23.99 and r[1] == {'day': 2, 'hour': 0}


@pytest.mark.parametrize('bad', ['NaN', 'null', 'undefined', 'Infinity'])
def test_derived_clock_rejects_bad_times(bad):
    r = subprocess.run(['node', '-e', f"require({json.dumps(str(SRC / 'realtime.js'))}).deriveClock({bad},Date.now())"], capture_output=True, text=True)
    assert r.returncode != 0 and 'RangeError' in r.stderr


def test_fake_clock_needs_the_developer_flag():
    q = "'?fakeclock=2026-12-24T12:00:00Z'"
    r = node(f"console.log(JSON.stringify([R.fakeNow({q},st({{}})),R.fakeNow({q},st({{'stockholmsliv-dev':'1'}})),R.fakeNow('?fakeclock=junk',st({{'stockholmsliv-dev':'1'}})),R.fakeNow('',st({{'stockholmsliv-dev':'1'}}))]))")
    assert r == [None, 1798113600000, None, None]
