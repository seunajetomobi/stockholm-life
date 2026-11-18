/* Stockholm Life: loading the city data and reading opening hours.
   gunzipFetch (fetch a JSON file, unpacking gzip when the bytes start with the gzip magic number) and parseHours
   (OpenStreetMap opening_hours text to a map of weekday to [open, close] hour ranges, or null when it cannot be
   read). The bodies are the original ones, moved unchanged. They use the browser's own fetch, Blob,
   DecompressionStream, Response and TextDecoder, looked up when called, so a test can stub them.
   A classic script: index.html loads it before the game script, which reads window.StockholmLife['city-data'].
   Node can require() it (tests/test_city_data.py). */
(function(root){
'use strict';
async function gunzipFetch(url){
  const r=await fetch(url);if(!r.ok)throw new Error(url+' '+r.status);
  const buf=await r.arrayBuffer();const u8=new Uint8Array(buf);
  if(u8[0]===0x1f&&u8[1]===0x8b){
    if(typeof DecompressionStream==='undefined')throw new Error('This browser cannot unpack the map data');
    const s=new Blob([buf]).stream().pipeThrough(new DecompressionStream('gzip'));return JSON.parse(await new Response(s).text())}
  return JSON.parse(new TextDecoder().decode(u8));
}
function parseHours(s){
  // OpenStreetMap opening_hours, common forms: "Mo-Fr 10:00-16:00; Sa 10:00-15:00", "10:00-20:00", "Mo-Su 08:30-18:00"
  if(!s||/closed|PH|week|\|\|/i.test(s))return null;
  const DAY=['Su','Mo','Tu','We','Th','Fr','Sa'],map={};
  for(const rule of s.split(';').map(x=>x.trim()).filter(Boolean)){
    const m=rule.match(/^((?:[A-Z][a-z](?:-[A-Z][a-z])?,?)+)?\s*(.*)$/);if(!m)return null;
    let days=[];if(m[1]){for(const part of m[1].split(',').filter(Boolean)){const [a,b]=part.split('-');const ia=DAY.indexOf(a),ib=DAY.indexOf(b||a);if(ia<0||ib<0)return null;let i=ia;for(let n=0;n<7;n++){days.push(i);if(i===ib)break;i=(i+1)%7}}}else days=[0,1,2,3,4,5,6];
    const t=m[2].trim();
    if(/^(off|closed)$/i.test(t)){days.forEach(d=>map[d]=[]);continue}
    const ranges=[];for(const tr of t.split(',')){const mm=tr.trim().match(/^(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})/);if(!mm)return null;ranges.push([+mm[1]+mm[2]/60,+mm[3]+mm[4]/60])}
    days.forEach(d=>map[d]=ranges);
  }
  return map;
}

const cityData={gunzipFetch,parseHours};
if(typeof module==='object'&&module&&module.exports)module.exports=cityData;
else (root.StockholmLife=root.StockholmLife||{})['city-data']=cityData;
})(globalThis);
