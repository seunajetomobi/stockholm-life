# Stockholm Life

A 3D life simulation set in real Stockholm, built in the browser with three.js and OpenStreetMap data.

## Run it

1. Open this folder in VS Code (File > Open Folder).
2. Open the terminal (Ctrl+`) and run `./start.sh`
   (or Terminal > Run Task > "Run Stockholm Life").
3. Play in VS Code's browser tab (Ctrl+Shift+P > "Simple Browser: Show" > http://localhost:8000),
   or in Chrome/Firefox. The Snap build of VS Code has no WebGL, so the city stays empty there:
   use the standalone VS Code (`code-gpu`) instead, or the script opens your normal browser.

The game must be served like this: opening `index.html` directly from disk will not load the city data.
It needs an internet connection the first time, to load three.js from the cdnjs/jsdelivr CDN.

## Files

| Path | What it is |
| --- | --- |
| `index.html` | The whole game: interface, game rules and the 3D world |
| `data/b.json` | Buildings (footprints, heights, types), in 500 m tiles |
| `data/r.json` | Street graph (nodes, edges, road classes, bridges, tunnels) |
| `data/m.json` | Parks, water, land, trees, rail and 15 000 places (shops, offices…) |
| `data/t.json` | Bus, tram, train, metro and ferry lines with stops |
| `data/x.json` | Traffic signals and crossings |
| `data/o.json` | One-way streets and lane counts (rebuild with `tools/osm_lanes.py`) |
| `data/people.json`, `vehicles.json`, `trees.json` | 3D models (GLB, base64) |

Map data © OpenStreetMap contributors (ODbL).
