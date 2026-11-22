"""src/rules/namnsdag.js: Swedish name days (source and date in the file header).

Node only (seconds, no browser). Run alone with: python3 -m pytest tests/test_namnsdag.py"""
import json
import subprocess
import pytest
import game

MODULE = game.ROOT / 'src' / 'rules' / 'namnsdag.js'


def node(js):
    r = subprocess.run(['node', '-e', f"const n=require({json.dumps(str(MODULE))});{js}"], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_interface():
    assert node("console.log(JSON.stringify(Object.keys(n).sort()))") == ['namnsdagFor', 'namnsdagOn']


def test_every_date_of_a_leap_year_is_covered_and_only_those():
    r = node("""const dim=[31,29,31,30,31,30,31,31,30,31,30,31];let ok=0,bad=[];
      for(let m=1;m<=12;m++)for(let d=1;d<=dim[m-1];d++){const a=n.namnsdagOn(m,d);if(Array.isArray(a))ok++;else bad.push([m,d])}
      console.log(JSON.stringify([ok,bad,n.namnsdagOn(2,30),n.namnsdagOn(13,1),n.namnsdagOn(4,31)]))""")
    assert r == [366, [], [], [], []]


def test_there_are_627_distinct_names_as_in_the_2022_list():
    r = node("""const s=new Set();let t=0;for(let m=1;m<=12;m++)for(let d=1;d<=31;d++)for(const x of n.namnsdagOn(m,d)){s.add(x);t++}console.log(JSON.stringify([t,s.size]))""")
    assert r == [627, 627]


def test_the_seven_dates_without_a_name_day():
    r = node("console.log(JSON.stringify([[1,1],[2,2],[2,29],[3,25],[6,24],[11,1],[12,25]].map(([m,d])=>n.namnsdagOn(m,d).length)))")
    assert r == [0] * 7


@pytest.mark.parametrize('m,d,names', [(1, 2, ['Svea']), (1, 6, ['Kasper', 'Melker', 'Baltsar']), (4, 30, ['Mariana']), (5, 1, ['Valborg']),
                                       (6, 6, ['Gustav', 'Gösta']), (12, 24, ['Eva']), (12, 26, ['Stefan', 'Staffan']), (12, 28, ['Benjamin']),
                                       (11, 6, ['Gustav Adolf'])])
def test_known_dates(m, d, names):
    assert node(f"console.log(JSON.stringify(n.namnsdagOn({m},{d})))") == names


def test_lookup_by_name_is_case_insensitive_and_exact():
    r = node("console.log(JSON.stringify([n.namnsdagFor('SVEA'),n.namnsdagFor(' gösta '),n.namnsdagFor('Sve'),n.namnsdagFor(''),n.namnsdagFor('Nobody')]))")
    assert r == [[{'month': 1, 'day': 2}], [{'month': 6, 'day': 6}], [], [], []]


def test_result_is_a_copy():
    assert node("const a=n.namnsdagOn(1,2);a.push('X');console.log(JSON.stringify(n.namnsdagOn(1,2)))") == ['Svea']


def test_names_are_clean_text():
    r = node("""const bad=[];for(let m=1;m<=12;m++)for(let d=1;d<=31;d++)for(const x of n.namnsdagOn(m,d))if(!/^[A-ZÅÄÖÉÜ][A-Za-zÅÄÖåäöéèüÜ' -]+$/.test(x))bad.push(x);console.log(JSON.stringify(bad))""")
    assert r == []
