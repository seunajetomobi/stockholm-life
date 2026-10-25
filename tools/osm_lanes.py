#!/usr/bin/env python3
"""Build data/o.json: one-way directions and lane counts for the street graph in data/r.json.

r.json has no oneway or lanes tags, so traffic would drive both ways on every street. This script
reads an Overpass export of OpenStreetMap ways that carry oneway / junction / lanes tags and matches
each way to the r.json edges it runs along (through the graph nodes that sit on its vertices).

Usage:
  1. Download the tags (Overpass query in OVERPASS_QUERY below) to a file, e.g. with
     curl --data-urlencode data@query.txt https://overpass-api.de/api/interpreter -o osm_lanes.json
  2. python3 tools/osm_lanes.py osm_lanes.json   (writes data/o.json)

o.json:  ow = flat [edge, dir, busBoth, ...]   dir 1: only a->b, -1: only b->a; busBoth 1 if buses may use both ways
         ln = flat [edge, lanes a->b, lanes b->a, ...]   (0: not tagged, or that direction is not allowed)
"""
import json, math, sys, os

OVERPASS_QUERY = """[out:json][timeout:180];
way["highway"~"^(primary|primary_link|secondary|secondary_link|tertiary|tertiary_link|unclassified|residential|living_street)$"]
   [~"^(oneway|junction|lanes|lanes:forward|lanes:backward)$"~"."]
   (59.2617,17.8275,59.4299,18.1875);
out tags geom qt;"""

O_LAT, O_LON = 59.3313, 18.0603
def P(lat, lon):  # same projection as index.html, in r.json integer units (world units x 100)
    return ((lon - O_LON) * 56817 / 50 * 100, -(lat - O_LAT) * 111320 / 50 * 100)

def num(v):
    try: return max(0, int(float(str(v).split(';')[0])))
    except (TypeError, ValueError): return 0

def main(src):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    r = json.load(open(os.path.join(root, 'data', 'r.json')))
    osm = json.load(open(src))
    N, E = r['nodes'], r['edges']
    TOL = 150  # 1.5 units*100 = 0.75 m: graph nodes are rounded copies of OSM vertices
    grid = {}
    for i in range(len(N) // 2):
        grid.setdefault((N[2*i] // 200, N[2*i+1] // 200), []).append(i)
    adj = {}
    for ei, e in enumerate(E):
        if 4 <= e[2] <= 10:
            adj.setdefault(e[0], []).append(ei); adj.setdefault(e[1], []).append(ei)

    def node_at(x, z):
        best, bd = -1, TOL
        gx, gz = int(x // 200), int(z // 200)
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                for n in grid.get((gx+i, gz+j), ()):
                    d = math.hypot(N[2*n] - x, N[2*n+1] - z)
                    if d < bd: best, bd = n, d
        return best

    ow, ln, seen = {}, {}, 0
    for w in osm['elements']:
        if w.get('type') != 'way' or 'geometry' not in w: continue
        t = w.get('tags', {})
        o = t.get('oneway', '')
        rb = t.get('junction') in ('roundabout', 'circular')
        d = 1 if o in ('yes', 'true', '1') or (rb and o not in ('no', '-1')) else -1 if o in ('-1', 'reverse') else 0
        bus_both = t.get('oneway:bus') == 'no' or t.get('oneway:psv') == 'no' or t.get('busway') == 'opposite_lane'
        lanes = num(t.get('lanes')); lf = num(t.get('lanes:forward')); lb = num(t.get('lanes:backward'))
        if d == 0 and not (lanes or lf or lb): continue
        if d:  # one way: every lane runs with the traffic (0 = not tagged, the game picks a default)
            fwd, bwd = (lanes, 0) if d == 1 else (0, lanes)
        else:
            fwd = lf or (lanes // 2 if lanes >= 2 else 0); bwd = lb or (lanes - fwd if lanes > fwd else fwd)
        seen += 1
        seq = []
        for g in w['geometry']:
            n = node_at(*P(g['lat'], g['lon']))
            if n >= 0 and (not seq or seq[-1] != n): seq.append(n)
        # walk the matched nodes in way order and claim the edge joining each consecutive pair
        for a, b in zip(seq, seq[1:]):
            for ei in adj.get(a, ()):
                e = E[ei]
                if {e[0], e[1]} != {a, b}: continue
                along = e[0] == a  # the OSM way runs a->b along this edge
                if d: ow[ei] = (d if along else -d, 1 if bus_both else 0)
                ln[ei] = (fwd, bwd) if along else (bwd, fwd)
    flat_ow = [v for ei in sorted(ow) for v in (ei, *ow[ei])]
    flat_ln = [v for ei in sorted(ln) for v in (ei, *ln[ei])]
    out = {'ts': osm.get('osm3s', {}).get('timestamp_osm_base', ''), 'ow': flat_ow, 'ln': flat_ln,
           'attribution': '© OpenStreetMap contributors (ODbL)'}
    json.dump(out, open(os.path.join(root, 'data', 'o.json'), 'w'), separators=(',', ':'))
    print(f'{seen} tagged ways -> {len(ow)} one-way edges, {len(ln)} edges with lanes')

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'osm_lanes.json')
