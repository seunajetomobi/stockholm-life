#!/usr/bin/env python3
"""Build data/e.json: a sign for every T-bana entrance and rail/light-rail/tram station, with the lines that stop there.

Inputs are two Overpass exports (queries below):
  entrances.json  - railway=subway_entrance / train_station_entrance / station / halt / tram_stop nodes
  routes.json     - route relations (subway, train, light_rail, tram) with member geometry, for line refs and colours

Usage: python3 tools/osm_stations.py entrances.json routes.json

e.json:  lines = [[ref, colour, mode], ...]
         e     = [[x, z, kind, entrance name, station name, [line indexes]], ...]   x, z in world units x 100
         kind: T tunnelbana entrance, J pendeltåg/train station, L light rail (Tvärbanan, Lidingöbanan,
               Roslagsbanan, Saltsjöbanan), S tram stop (Spårväg City, Nockebybanan)
"""
import json, math, sys, os

ENTRANCES_QUERY = """[out:json][timeout:180];
( node["railway"="subway_entrance"](59.2617,17.8275,59.4299,18.1875);
  node["railway"="train_station_entrance"](59.2617,17.8275,59.4299,18.1875);
  node["railway"="station"](59.2617,17.8275,59.4299,18.1875);
  node["railway"="halt"](59.2617,17.8275,59.4299,18.1875);
  node["railway"="tram_stop"](59.2617,17.8275,59.4299,18.1875); );
out body;"""
ROUTES_QUERY = """[out:json][timeout:180];
relation["type"="route"]["route"~"^(subway|train|light_rail|tram)$"](59.2617,17.8275,59.4299,18.1875);
out body geom;"""

O_LAT, O_LON = 59.3313, 18.0603
def P(lat, lon): return ((lon - O_LON) * 56817 / 50, -(lat - O_LAT) * 111320 / 50)  # world units (50 m)

# SL's colours for the named OSM colours; OSM hex colours are kept
NAMED = {'green': '#179D4D', 'red': '#D71D24', 'blue': '#0089CA'}
LIGHT_RAIL = ('Roslagsbanan', 'Saltsjöbanan', 'Tvärbanan', 'Lidingöbanan')

def main(ent_path, rel_path):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ents = [e for e in json.load(open(ent_path))['elements'] if e['type'] == 'node' and 'tags' in e]
    rels = json.load(open(rel_path))['elements']
    lines, line_ix, stops = [], {}, []   # stops: (x, z, line index, mode)
    for r in rels:
        t = r.get('tags', {})
        col, ref, net, name = t.get('colour'), t.get('ref') or '', t.get('network', ''), t.get('name', '')
        if not col or net != 'SL' or not ref:   # SL lines only (SJ/Mälartåg have no SL colours)
            if 'Arlanda Express' not in name: continue
            ref, col = ref or '46', col or '#FFCE1D'
        mode = t['route']
        if mode == 'train' and any(k in name for k in LIGHT_RAIL): mode = 'light_rail'
        col = NAMED.get(col.lower(), col.upper() if col.startswith('#') else col)
        k = (ref, col)
        if k not in line_ix: line_ix[k] = len(lines); lines.append([ref, col, mode])
        for m in r.get('members', []):
            if m['type'] == 'node' and m.get('role', '').startswith('stop') and 'lat' in m:
                x, z = P(m['lat'], m['lon']); stops.append((x, z, line_ix[k], mode))

    def lines_near(x, z, modes, rad):
        got = {}
        for sx, sz, li, md in stops:
            if md in modes:
                d = math.hypot(sx - x, sz - z)
                if d < rad and d < got.get(li, 1e9): got[li] = d
        return sorted(got, key=lambda li: (lines[li][2], lines[li][0]))

    stations = [e for e in ents if e['tags'].get('railway') in ('station', 'halt')]
    def station_name(x, z, want):
        best, bd = '', 9e9
        for s in stations:
            sx, sz = P(s['lat'], s['lon']); d = math.hypot(sx - x, sz - z)
            if d < bd and (not want or want(s['tags'])): best, bd = s['tags'].get('name', ''), d
        return best if bd < 12 else ''

    out = []
    subway = lambda t: t.get('station') == 'subway' or t.get('subway') == 'yes'
    for e in ents:
        t, rw = e['tags'], e['tags'].get('railway'); x, z = P(e['lat'], e['lon'])
        if rw == 'subway_entrance':
            ls = lines_near(x, z, ('subway',), 10)        # 500 m: entrances can be far from the platform stop
            out.append([round(x*100), round(z*100), 'T', t.get('name', ''), station_name(x, z, subway), ls])
        elif rw == 'train_station_entrance':
            ls = lines_near(x, z, ('train', 'light_rail'), 8)
            out.append([round(x*100), round(z*100), 'J', t.get('name', ''), station_name(x, z, None), ls])
        elif rw == 'tram_stop':
            ls = lines_near(x, z, ('tram', 'light_rail'), 3)
            if ls: out.append([round(x*100), round(z*100), 'S' if all(lines[i][2] == 'tram' for i in ls) else 'L', '', t.get('name', ''), ls])
        elif rw in ('station', 'halt') and not subway(t):
            ls = lines_near(x, z, ('train', 'light_rail'), 6)
            if not ls: continue
            # stations that already have mapped entrances get their sign there instead
            if any(o[2] == 'J' and math.hypot(o[0]/100 - x, o[1]/100 - z) < 4 for o in out): continue
            kind = 'L' if all(lines[i][2] == 'light_rail' for i in ls) else 'J'
            out.append([round(x*100), round(z*100), kind, '', t.get('name', ''), ls])
    json.dump({'lines': lines, 'e': out, 'attribution': '© OpenStreetMap contributors (ODbL)'},
              open(os.path.join(root, 'data', 'e.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    kinds = {}
    for o in out: kinds[o[2]] = kinds.get(o[2], 0) + 1
    print(f'{len(lines)} lines, {len(out)} signs {kinds}, {sum(1 for o in out if not o[5])} without lines')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
