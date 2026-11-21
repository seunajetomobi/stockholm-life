"""src/rules/holidays.js: Swedish public holidays computed from Lag (1989:253) om allmänna helgdagar (read on lagen.nu, 2026-11-21).

Node only (seconds, no browser). The Easter dates 2020 to 2030 are the published ones (not computed by the code under test);
the 2026 list is the one confirmed by Swedish sources (Good Friday 3 April, Easter Day 5 April, Easter Monday 6 April, Ascension
14 May, All Saints' Day 31 October). Run alone with: python3 -m pytest tests/test_holidays.py"""
import json
import subprocess
import pytest
import game

MODULE = game.ROOT / 'src' / 'rules' / 'holidays.js'


def node(js):
    r = subprocess.run(['node', '-e', f"const h=require({json.dumps(str(MODULE))});{js}"], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_interface():
    assert node("console.log(JSON.stringify(Object.keys(h).sort()))") == ['easterSunday', 'holidayOn', 'holidays', 'isRedDay']


@pytest.mark.parametrize('year,month,day', [(2020, 4, 12), (2021, 4, 4), (2022, 4, 17), (2023, 4, 9), (2024, 3, 31), (2025, 4, 20),
                                            (2026, 4, 5), (2027, 3, 28), (2028, 4, 16), (2029, 4, 1), (2030, 4, 21)])
def test_easter_sunday_matches_the_published_dates(year, month, day):
    assert node(f"console.log(JSON.stringify(h.easterSunday({year})))") == {'month': month, 'day': day}


def test_2026_red_days_are_the_confirmed_ones():
    got = node("console.log(JSON.stringify(h.holidays(2026).filter(x=>x.kind==='red').map(x=>[x.month,x.day,x.key])))")
    assert got == [[1, 1, 'newyear'], [1, 6, 'epiphany'], [4, 3, 'goodfriday'], [4, 5, 'easter'], [4, 6, 'eastermonday'], [5, 1, 'mayday'],
                   [5, 14, 'ascension'], [5, 24, 'whitsun'], [6, 6, 'national'], [6, 20, 'midsummer'], [10, 31, 'allsaints'],
                   [12, 25, 'christmas'], [12, 26, 'boxing']]


def test_the_statutes_not_holidays_are_only_eves():
    """Whit Monday is not a public holiday since 2005; Midsummer Eve, Christmas Eve and New Year's Eve are not by statute (kind 'eve')."""
    got = node("""const L=h.holidays(2026);console.log(JSON.stringify({eves:L.filter(x=>x.kind==='eve').map(x=>[x.month,x.day,x.key]),
      whitmonday:h.holidayOn(2026,5,25),eveRed:[h.isRedDay(2026,6,19),h.isRedDay(2026,12,24),h.isRedDay(2026,12,31)]}))""")
    assert got == {'eves': [[6, 19, 'midsummereve'], [12, 24, 'christmaseve'], [12, 31, 'newyeareve']], 'whitmonday': None, 'eveRed': [False, False, False]}


def test_every_sunday_is_a_red_day_and_an_ordinary_weekday_is_not():
    got = node("console.log(JSON.stringify([h.isRedDay(2026,11,22),h.isRedDay(2026,11,23),h.isRedDay(2026,11,21),h.isRedDay(2026,12,25),h.isRedDay(2026,5,15)]))")
    assert got == [True, False, False, True, False]   # Sun 22 Nov, Mon 23, Sat 21, Christmas Day (Friday), Fri 15 May


def test_the_floating_rules_hold_for_every_year_1990_to_2100():
    got = node("""let bad=[];const dow=(y,m,d)=>new Date(Date.UTC(y,m-1,d)).getUTCDay();
      for(let y=1990;y<=2100;y++){const L=Object.fromEntries(h.holidays(y).map(x=>[x.key,x]));const E=h.easterSunday(y);
        if(dow(y,E.month,E.day)!==0)bad.push([y,'easter not a Sunday']);
        if(dow(y,L.goodfriday.month,L.goodfriday.day)!==5)bad.push([y,'good friday']);
        if(dow(y,L.eastermonday.month,L.eastermonday.day)!==1)bad.push([y,'easter monday']);
        if(dow(y,L.ascension.month,L.ascension.day)!==4)bad.push([y,'ascension not a Thursday']);
        if(dow(y,L.whitsun.month,L.whitsun.day)!==0)bad.push([y,'whitsun not a Sunday']);
        const m=L.midsummer;if(m.month!==6||m.day<20||m.day>26||dow(y,6,m.day)!==6)bad.push([y,'midsummer']);
        const a=L.allsaints,okA=(a.month===10&&a.day===31)||(a.month===11&&a.day<=6);if(!okA||dow(y,a.month,a.day)!==6)bad.push([y,'all saints']);
        if(L.midsummereve.day!==m.day-1)bad.push([y,'midsummer eve']);
        const n=h.holidays(y).length;if(n!==16)bad.push([y,'count '+n]);}
      console.log(JSON.stringify(bad))""")
    assert got == []


def test_registers_in_the_page_under_its_own_name():
    src = MODULE.read_text(encoding='utf-8')
    assert "(root.StockholmLife=root.StockholmLife||{}).holidays=api" in src
