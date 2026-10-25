// Stockholm Life flights relay: a Cloudflare Worker that passes live aircraft positions around Stockholm to the game.
//
// Browsers only let a page read data from another site if that site allows it (CORS). The free ADS-B feeds
// don't, so this relay fetches them, keeps only what the game needs, caches it for 8 seconds and adds the header.
//
// Set it up (free, about 5 minutes):
//   1. Sign in at https://dash.cloudflare.com (create a free account if needed).
//   2. Workers & Pages -> Create -> Create Worker -> name it "stockholm-flights" -> Deploy.
//   3. Edit code -> replace everything with this file -> Deploy.
//   4. Open https://stockholm-flights.<your-subdomain>.workers.dev/flights : you should see JSON with "ac": [...].
//   5. Put that address (without /flights) in FLIGHT_RELAY_DEFAULT in index.html, or open the game once with
//      ?flights=https://stockholm-flights.<your-subdomain>.workers.dev
//
// Sources, tried in order: adsb.lol, adsb.fi, OpenSky Network. All are community ADS-B feeds with fair-use limits;
// the 8-second cache means one request upstream per 8 seconds however many people play.

const CENTER = { lat: 59.47, lon: 17.95, nm: 45 };   // covers Arlanda, Bromma and the city, ~80 km across
const ALLOW = ['https://seunajetomobi.github.io', 'http://localhost:8000', 'http://127.0.0.1:8000'];
const UA = { 'User-Agent': 'Mozilla/5.0 (compatible; stockholm-life-flights-relay; +https://github.com/seunajetomobi/stockholm-life)', 'Accept': 'application/json' };
const LOG = [];   // what each source answered, shown with /flights?debug=1
async function get(url) {
  try { const r = await fetch(url, { headers: UA, cf: { cacheTtl: 5 } }); LOG.push(`${url.split('/')[2]} ${r.status}`); return r.ok ? await r.json() : null; }
  catch (e) { LOG.push(`${url.split('/')[2]} ${e.message}`); return null; }
}

const num = v => (typeof v === 'number' && isFinite(v) ? v : null);
const trimReadsb = (list, now, src) => ({
  now, src,
  ac: (list || []).filter(a => num(a.lat) !== null && num(a.lon) !== null).map(a => ({
    hex: a.hex, cs: (a.flight || '').trim(), reg: a.r || '', type: a.t || '', desc: a.desc || '',
    lat: a.lat, lon: a.lon, gnd: a.alt_baro === 'ground',
    alt: a.alt_baro === 'ground' ? 0 : (num(a.alt_geom) ?? num(a.alt_baro) ?? 0),          // feet
    gs: num(a.gs) ?? 0, trk: num(a.track) ?? num(a.true_heading) ?? 0,                     // knots, degrees
    vr: num(a.baro_rate) ?? num(a.geom_rate) ?? 0, cat: a.category || '', sq: a.squawk || '' // feet/min
  }))
});

const SOURCES = [
  async () => {
    const j = await get(`https://api.adsb.lol/v2/point/${CENTER.lat}/${CENTER.lon}/${CENTER.nm}`) || await get(`https://api.adsb.lol/v2/lat/${CENTER.lat}/lon/${CENTER.lon}/dist/${CENTER.nm}`);
    if (!j) return null;
    return trimReadsb(j.ac, j.now > 1e11 ? j.now : (j.now || Date.now() / 1000) * 1000, 'adsb.lol');
  },
  async () => {
    const j = await get(`https://opendata.adsb.fi/api/v2/lat/${CENTER.lat}/lon/${CENTER.lon}/dist/${CENTER.nm}`) || await get(`https://opendata.adsb.fi/api/v3/lat/${CENTER.lat}/lon/${CENTER.lon}/dist/${CENTER.nm}`);
    if (!j) return null;
    return trimReadsb(j.aircraft || j.ac, (j.now || Date.now() / 1000) * 1000, 'adsb.fi');
  },
  async () => {
    const d = CENTER.nm / 60, e = d / Math.cos(CENTER.lat * Math.PI / 180);
    const j = await get(`https://opensky-network.org/api/states/all?lamin=${CENTER.lat - d}&lomin=${CENTER.lon - e}&lamax=${CENTER.lat + d}&lomax=${CENTER.lon + e}`);
    if (!j) return null;
    // state vector: [icao24, callsign, country, t_pos, t_contact, lon, lat, baro_alt m, on_ground, velocity m/s, track, vrate m/s, sensors, geo_alt m, squawk, spi, source, category]
    return { now: (j.time || Date.now() / 1000) * 1000, src: 'OpenSky Network', ac: (j.states || []).filter(s => s[5] !== null && s[6] !== null).map(s => ({
      hex: s[0], cs: (s[1] || '').trim(), reg: '', type: '', desc: '', lat: s[6], lon: s[5], gnd: !!s[8],
      alt: Math.round(((s[13] ?? s[7]) || 0) / 0.3048), gs: Math.round((s[9] || 0) * 1.944), trk: s[10] || 0,
      vr: Math.round((s[11] || 0) * 196.85), cat: s[17] === 8 ? 'A7' : s[17] === 6 ? 'A5' : s[17] === 2 ? 'A1' : '', sq: s[14] || ''
    })) };
  }
];

export default {
  async fetch(req, env, ctx) {
    const origin = req.headers.get('Origin') || '';
    const cors = { 'Access-Control-Allow-Origin': ALLOW.includes(origin) ? origin : ALLOW[0], 'Access-Control-Allow-Methods': 'GET', 'Vary': 'Origin' };
    if (req.method === 'OPTIONS') return new Response(null, { headers: cors });
    const url = new URL(req.url), debug = url.searchParams.has('debug');
    if (url.pathname !== '/flights') return new Response('Stockholm Life flights relay. GET /flights', { headers: cors });
    LOG.length = 0;
    const cache = typeof caches !== 'undefined' ? caches.default : null, key = new Request('https://relay.cache/flights');
    let res = !debug && cache && await cache.match(key);
    if (!res) {
      let data = null;
      for (const src of SOURCES) { try { data = await src(); if (data && data.ac) break; } catch (e) { data = null; } }
      if (!data || debug) return new Response(JSON.stringify({ error: data ? undefined : 'no ADS-B source answered', tried: LOG, aircraft: data ? data.ac.length : 0, src: data && data.src }), { status: data ? 200 : 502, headers: { ...cors, 'Content-Type': 'application/json' } });
      res = new Response(JSON.stringify(data), { headers: { 'Content-Type': 'application/json', 'Cache-Control': 'public, max-age=8' } });
      if (cache && ctx) ctx.waitUntil(cache.put(key, res.clone()));
    }
    const out = new Response(res.body, res);
    for (const [k, v] of Object.entries(cors)) out.headers.set(k, v);
    return out;
  }
};
