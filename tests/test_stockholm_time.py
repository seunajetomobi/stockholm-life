"""src/rules/stockholm-time.js (docs/REALTIME_SPEC.md, R1): real Stockholm time, daylight saving included, with a fake clock for tests.

It runs the module in Node (seconds, no browser). The game does not use the module yet. Run alone with:
python3 -m pytest tests/test_stockholm_time.py"""
import json
import subprocess
import pytest
import game

MODULE = game.ROOT / 'src' / 'rules' / 'stockholm-time.js'


def node(js, tz=None):
    env = None
    if tz:
        import os
        env = dict(os.environ, TZ=tz)
    r = subprocess.run(['node', '-e', f"const t=require({json.dumps(str(MODULE))});{js}"], capture_output=True, text=True, timeout=60, env=env)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_interface():
    got = node("console.log(JSON.stringify(Object.keys(t).sort()))")
    assert got == ['TZ', 'dayLengthHours', 'dayNumber', 'getOffset', 'hourAt', 'lifeDay', 'nowMs', 'partsAt', 'setFakeNow', 'setOffset', 'startOfDay', 'weekday']


@pytest.mark.parametrize('utc,expect', [
    ((2026, 11, 21, 12, 0, 0), (2026, 11, 21, 13, 0, 0)),     # winter: UTC+1
    ((2026, 7, 1, 12, 0, 0), (2026, 7, 1, 14, 0, 0)),         # summer: UTC+2
    ((2026, 12, 31, 23, 30, 0), (2027, 1, 1, 0, 30, 0)),      # the new year arrives in Stockholm first
    ((2026, 3, 29, 0, 59, 59), (2026, 3, 29, 1, 59, 59)),     # the last second before the clocks go forward
    ((2026, 3, 29, 1, 0, 0), (2026, 3, 29, 3, 0, 0)),         # 02:00 does not exist
    ((2026, 10, 25, 0, 59, 59), (2026, 10, 25, 2, 59, 59)),   # 02:59 the first time
    ((2026, 10, 25, 1, 0, 0), (2026, 10, 25, 2, 0, 0)),       # 02:00 again after the clocks go back
])
def test_wall_clock_parts_follow_the_zone_whatever_the_machine_zone(utc, expect):
    for tz in ('UTC', 'America/Los_Angeles', 'Asia/Tokyo'):
        p = node(f"console.log(JSON.stringify(t.partsAt(Date.UTC({','.join(str(x) for x in (utc[0], utc[1] - 1) + utc[2:])}))))", tz)
        assert (p['year'], p['month'], p['day'], p['hour'], p['minute'], p['second']) == expect, (tz, p)


def test_hour_is_a_fraction_of_the_day_and_midnight_is_zero_not_24():
    got = node("const m=(h,mi)=>Date.UTC(2026,10,21,h-1,mi,0);console.log(JSON.stringify([t.hourAt(m(0,0)),t.hourAt(m(8,30)),t.hourAt(m(23,45))]))")
    assert got == [0, 8.5, 23.75]


@pytest.mark.parametrize('y,m,d,hours', [(2026, 3, 29, 23), (2026, 10, 25, 25), (2026, 11, 21, 24), (2026, 7, 1, 24), (2027, 3, 28, 23), (2027, 10, 31, 25)])
def test_day_length_is_23_hours_when_clocks_go_forward_25_when_they_go_back(y, m, d, hours):
    assert node(f"console.log(t.dayLengthHours(Date.UTC({y},{m - 1},{d},12,0,0)))") == hours


def test_start_of_day_is_local_midnight():
    got = node("""const ms=Date.UTC(2026,10,21,15,0,0);const s=t.startOfDay(ms);const p=t.partsAt(s),q=t.partsAt(s-1000);
      console.log(JSON.stringify([p.hour,p.minute,p.second,p.day,q.day,q.hour]))""")
    assert got == [0, 0, 0, 21, 20, 23]


def test_life_day_counts_calendar_days_in_stockholm_not_24_hour_blocks():
    got = node("""const A=Date.UTC(2026,9,24,21,30,0);   // 23:30 Stockholm on 24 Oct
      console.log(JSON.stringify([t.lifeDay(A,A),t.lifeDay(A,A+31*60000),t.lifeDay(A,A+24*3600000),t.lifeDay(A,Date.UTC(2026,10,21,12,0,0))]))""")
    assert got == [1, 2, 2, 29]


def test_life_day_across_the_clock_change_still_changes_at_stockholm_midnight():
    got = node("""const A=Date.UTC(2026,9,24,12,0,0),B=Date.UTC(2026,9,25,21,59,0),C=Date.UTC(2026,9,25,23,0,0);
      console.log(JSON.stringify([t.lifeDay(A,B),t.lifeDay(A,C)]))""")
    assert got == [2, 3]


def test_weekday_is_stockholms():
    got = node("console.log(JSON.stringify([t.weekday(Date.UTC(2026,9,24,12)),t.weekday(Date.UTC(2026,9,24,23,30)),t.weekday(Date.UTC(2026,10,21,12))]))")
    assert got == [6, 0, 6]   # 24 Oct 2026 Saturday; 23:30 UTC is already Sunday in Stockholm (UTC+2); 21 Nov Saturday


def test_fake_clock_replaces_now_and_can_be_cleared_and_rejects_garbage():
    got = node("""const real=t.nowMs();t.setFakeNow(1234);const f=t.nowMs();t.setFakeNow(null);const back=t.nowMs();let err='';
      try{t.setFakeNow('later')}catch(e){err=e.name}
      console.log(JSON.stringify({near:Math.abs(real-Date.now())<2000,f,back_real:Math.abs(back-Date.now())<2000,err,still:t.nowMs()>1e12}))""")
    assert got == {'near': True, 'f': 1234, 'back_real': True, 'err': 'RangeError', 'still': True}


def test_in_the_page_it_registers_under_its_own_name_and_node_exports_the_same_object():
    got = node("""globalThis.StockholmLife=undefined;delete require.cache[require.resolve(%s)];console.log(JSON.stringify(typeof t.nowMs))""" % json.dumps(str(MODULE)))
    assert got == 'function'
    src = MODULE.read_text(encoding='utf-8')
    assert "(root.StockholmLife=root.StockholmLife||{})['stockholm-time']=api" in src


def test_offset_corrects_a_wrong_device_clock():
    """setOffset(ms): nowMs() is the device time plus the learned error; a fake time still wins; bad input is refused."""
    got = node("""const dev=Date.now();t.setOffset(-3*3600000);const a=t.nowMs()-dev;t.setFakeNow(1234);const f=t.nowMs();t.setFakeNow(null);
      let err='';try{t.setOffset('x')}catch(e){err=e.name}
      console.log(JSON.stringify({near:Math.abs(a+3*3600000)<1500,off:t.getOffset(),f,err}))""")
    assert got == {'near': True, 'off': -10800000, 'f': 1234, 'err': 'RangeError'}, got
