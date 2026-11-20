"""src/rules/clock.js, the fourth rules module (docs/MODULES.md, docs/M2_SPEC.md; M2 stage 2): START, dateOf, CLOCK_RATE and reachesMidnight.

It runs the module in Node (seconds, no browser). It checks that the module is the original calendar code moved unchanged
(the same dates as the formula that was in index.html), that the station's rate has one name with the value it always had (4),
and the midnight test every writer of the hour makes. A source check shows index.html takes these from the module and no
longer defines them. Nothing here changes how game time passes. Run alone with: python3 -m pytest tests/test_clock.py"""
import json
import re
import subprocess
import pytest
import game

MODULE = game.ROOT / 'src' / 'rules' / 'clock.js'


def node(js):
    r = subprocess.run(['node', '-e', js], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_interface():
    got = node(f"const c=require({json.dumps(str(MODULE))});console.log(JSON.stringify(Object.keys(c).sort()))")
    assert got == ['CLOCK_RATE', 'START', 'dateOf', 'reachesMidnight']


def test_dateof_is_the_original_formula():
    """Day 1 is Saturday 24 October 2026; every date over 1,500 days equals the formula that was in index.html (`new Date(START)` plus d-1 days)."""
    got = node(f"""const c=require({json.dumps(str(MODULE))});
      const S0=new Date(2026,9,24),orig=d=>{{const x=new Date(S0);x.setDate(x.getDate()+d-1);return x}};
      let bad=0;for(let d=-5;d<=1500;d++)if(c.dateOf(d).getTime()!==orig(d).getTime())bad++;
      console.log(JSON.stringify({{bad,start:c.START.getTime()===S0.getTime(),d1:c.dateOf(1).toDateString(),d8:c.dateOf(8).toDateString(),
        d8day:c.dateOf(8).getDay(),leap:c.dateOf(494).toDateString(),newyear:c.dateOf(70).toDateString()}}))""")
    assert got['bad'] == 0 and got['start']
    assert got['d1'] == 'Sat Oct 24 2026' and got['d8'] == 'Sat Oct 31 2026' and got['d8day'] == 6
    assert got['newyear'] == 'Fri Jan 01 2027'
    assert got['leap'] == 'Tue Feb 29 2028'


def test_dateof_does_not_change_its_start():
    got = node(f"const c=require({json.dumps(str(MODULE))});const t=c.START.getTime();c.dateOf(100).setFullYear(1999);console.log(JSON.stringify(c.START.getTime()===t))")
    assert got is True


def test_clock_rate_is_the_stations_rate():
    """The station and the train have always run 4 times faster than real time (one game minute per 15 real seconds). The number now has one name."""
    assert node(f"console.log(require({json.dumps(str(MODULE))}).CLOCK_RATE)") == 4


@pytest.mark.parametrize('hour,h,want', [(23.99, 0.0099, False), (23.99, 0.01, True), (23, 1, True), (23, 0.99, False), (0, 23.99, False), (12, 12, True),
                                         (20, 10, True), (23.98, 0.02, True), (0, 0, False), (24, 0, True)])
def test_reaches_midnight_is_the_test_the_writers_make(hour, h, want):
    """`S.hour+h>=24`: exactly 24:00 counts as midnight, 23.99 does not."""
    assert node(f"console.log(JSON.stringify(require({json.dumps(str(MODULE))}).reachesMidnight({hour},{h})))") is want


def test_index_takes_the_calendar_from_the_module():
    html = (game.ROOT / 'index.html').read_text(encoding='utf-8')
    assert '<script src="src/rules/clock.js"></script>' in html
    assert re.search(r"const \{START,dateOf,CLOCK_RATE\}=useModule\('clock','rules/clock\.js'\)", html)
    assert 'new Date(2026,9,24)' not in html, 'START is defined in the module only'
    assert 'const dateOf=' not in html
    assert 'CRATE=CLOCK_RATE' in html and 'CRATE=4' not in html
