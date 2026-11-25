"""src/data/world.js: every country (the 193 UN member states, Vatican City, Palestine, Kosovo, Taiwan) with its home towns, from GeoNames (CC BY 4.0).

Runs the module in Node (seconds, no browser). Run alone with: python3 -m pytest tests/test_world.py"""
import json
import subprocess
import game

MODULE = game.ROOT / 'src' / 'data' / 'world.js'


def node(js):
    r = subprocess.run(['node', '-e', f"const w=require({json.dumps(str(MODULE))});{js}"], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_every_country_once():
    got = node("const c=w.countries;console.log(JSON.stringify({n:c.length,u:new Set(c.map(x=>x[0])).size,names:new Set(c.map(x=>x[1])).size,keys:Object.keys(w).sort()}))")
    assert got == {'n': 197, 'u': 197, 'names': 197, 'keys': ['countries', 'source', 'towns']}, got


def test_shape_groups_and_known_countries():
    got = node("""const g={};for(const c of w.countries)g[c[3]]=(g[c[3]]||0)+1;
      const by=Object.fromEntries(w.countries.map(c=>[c[0],c]));
      console.log(JSON.stringify({g,se:by.SE,ng:by.NG,de:by.DE,no:by.NO,us:by.US,sch:w.countries.filter(c=>c[4]).length,
        bad:w.countries.filter(c=>c[0].length!==2||!c[1]||!['se','nordic','eu','noneu'].includes(c[3])||![0,1].includes(c[4])).length}))""")
    assert got['bad'] == 0, got
    assert got['g'] == {'se': 1, 'nordic': 4, 'eu': 26, 'noneu': 166}, got
    assert got['se'][1] == 'Sweden' and got['se'][2] == 'Stockholm' and got['se'][3] == 'se'
    assert got['ng'][1] == 'Nigeria' and got['ng'][3] == 'noneu' and got['ng'][4] == 0
    assert got['de'][3] == 'eu' and got['de'][4] == 1 and got['no'][3] == 'nordic' and got['us'][3] == 'noneu'
    assert got['sch'] == 29, got['sch']  # the Schengen area on 2026-11-23: 29 states


def test_every_country_has_home_towns():
    got = node("""const bad=w.countries.filter(c=>!Array.isArray(w.towns[c[0]])||w.towns[c[0]].length<1||w.towns[c[0]].length>10||new Set(w.towns[c[0]]).size!==w.towns[c[0]].length).map(c=>c[0]);
      console.log(JSON.stringify({bad,ng:w.towns.NG.slice(0,3),se:w.towns.SE.slice(0,2),va:w.towns.VA,de:w.towns.DE.slice(0,2)}))""")
    assert got['bad'] == [], got
    assert got['ng'] == ['Abuja', 'Lagos', 'Kano'] and got['se'] == ['Stockholm', 'Gothenburg'] and got['va'] == ['Vatican City']


def test_source_is_named_and_dated():
    got = node("console.log(JSON.stringify(w.source))")
    assert 'GeoNames' in got and 'CC BY 4.0' in got and '2026-11-23' in got
