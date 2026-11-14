/* Stockholm Life: geography.
   The map projection (P), the districts (AREAS), the T-bana and tram stations (ST, STP), the lines (LINES) and
   route finding over them (transitRoute, nearestStation). Data and pure functions only: no DOM, no game state,
   no three.js, no network.
   A classic script: index.html loads it before the game script, which reads window.StockholmLife.geography.
   Node can require() it (tests/test_geography.py). How modules work here: docs/MODULES.md. */
(function(root){
'use strict';
// 1 world unit = 50 m. Origin at T-Centralen. Same projection as the OpenStreetMap export.
const O_LAT=59.3313,O_LON=18.0603;
const P=(lat,lon)=>[(lon-O_LON)*56817/50,-(lat-O_LAT)*111320/50];
const PP=arr=>arr.map(([a,b])=>P(a,b));
// Rough water outlines, used only until the real shoreline data is present.
const WATER_FALLBACK=[
  [[59.3285,18.0050],[59.3268,18.0300],[59.3266,18.0480],[59.3268,18.0560],[59.3262,18.0625],[59.3240,18.0640],[59.3218,18.0690],[59.3205,18.0665],[59.3212,18.0560],[59.3188,18.0400],[59.3160,18.0220],[59.3120,18.0050],[59.3050,17.9850],[59.2950,17.9500],[59.2950,17.8500],[59.3250,17.8500],[59.3270,17.9900]],
  [[59.3400,17.9930],[59.3400,17.9990],[59.3285,18.0010],[59.3275,17.9930]],
  [[59.3400,17.9990],[59.3395,18.0200],[59.3372,18.0350],[59.3355,18.0480],[59.3345,18.0560],[59.3335,18.0560],[59.3345,18.0450],[59.3360,18.0330],[59.3378,18.0180],[59.3385,17.9990]],
  [[59.3342,18.0552],[59.3342,18.0574],[59.3290,18.0600],[59.3266,18.0600],[59.3266,18.0560],[59.3283,18.0560]],
  [[59.3298,18.0580],[59.3302,18.0640],[59.3294,18.0700],[59.3284,18.0700],[59.3283,18.0620],[59.3284,18.0565]],
  [[59.3294,18.0620],[59.3302,18.0745],[59.3322,18.0775],[59.3308,18.0860],[59.3275,18.0880],[59.3255,18.0950],[59.3240,18.1100],[59.3260,18.1300],[59.3330,18.1400],[59.3330,18.2200],[59.2850,18.2200],[59.2950,18.1400],[59.3050,18.1250],[59.3150,18.0950],[59.3185,18.0800],[59.3205,18.0740],[59.3220,18.0702],[59.3240,18.0722],[59.3270,18.0748],[59.3285,18.0702]],
  [[59.3322,18.0775],[59.3336,18.0850],[59.3332,18.1000],[59.3345,18.1150],[59.3340,18.1350],[59.3330,18.1420],[59.3318,18.1420],[59.3316,18.1100],[59.3318,18.0950],[59.3308,18.0860]],
  [[59.3110,17.9950],[59.3090,18.0400],[59.3060,18.0600],[59.3045,18.0800],[59.3045,18.1100],[59.3050,18.1250],[59.3020,18.1250],[59.3015,18.1100],[59.3015,18.0800],[59.3030,18.0600],[59.3060,18.0400],[59.3080,17.9950]],
  [[59.3400,18.1400],[59.3500,18.1150],[59.3750,18.1150],[59.3750,18.2200],[59.3330,18.2200],[59.3330,18.1400]],
].map(PP);

const AREAS={
  kista:{name:'Kista',ll:[59.4032,17.9443],st:'Kista',blurb:'Glass towers, Ericsson and the Science City. The government service centre on Isafjordsgatan houses Skatteverket, Försäkringskassan and Arbetsförmedlingen.'},
  sundbyberg:{name:'Sundbyberg',ll:[59.3609,17.9716],st:'Sundbybergs centrum',blurb:'Sweden\'s smallest municipality. Migrationsverket and a Skatteverket service office face each other on Sturegatan.'},
  rinkeby:{name:'Rinkeby',ll:[59.3880,17.9285],st:'Rinkeby',blurb:'A lively torg, the best sambusa in town and a tight community. Rents are lower out here.'},
  vasastan:{name:'Vasastan',ll:[59.3429,18.0497],st:'Odenplan',blurb:'Odenplan cafés, stone courtyards and Asplund\'s library rotunda, closed for renovation until 2027.'},
  kungsholmen:{name:'Kungsholmen',ll:[59.3326,18.0290],st:'Fridhemsplan',blurb:'Fridhemsplan, a vårdcentral, the SFI school and summer swims at Rålambshovsparken.'},
  tc:{name:'T-Centralen',ll:[59.3324,18.0645],st:'T-Centralen',blurb:'Sergels torg, where all three T-bana lines meet. Banks, Systembolaget and Kulturhuset.'},
  ostermalm:{name:'Östermalm',ll:[59.3350,18.0760],st:'Östermalmstorg',blurb:'Stureplan, Östermalmshallen and old money. KTH is up on Valhallavägen.'},
  gamlastan:{name:'Gamla stan',ll:[59.3251,18.0707],st:'Gamla stan',blurb:'Stortorget, the Royal Palace and ochre houses on cobbled lanes.'},
  sodermalm:{name:'Södermalm',ll:[59.3143,18.0735],st:'Medborgarplatsen',blurb:'Medborgarplatsen, Götgatan\'s shops and bars, and the view from Monteliusvägen.'},
  djurgarden:{name:'Djurgården',ll:[59.3270,18.1035],st:'Skansen',tram:1,blurb:'Royal parkland, Skansen and the Vasa ship. The best cure for a dark day.'},
};
for(const k in AREAS){const [x,z]=P(...AREAS[k].ll);AREAS[k].x=x;AREAS[k].z=z}
const HUB_R=9; // units (450 m): within this you're "in" a neighbourhood

/* ---------- T-bana ---------- */
const ST={
  'Kungsträdgården':[59.3307,18.0730],'T-Centralen':[59.3313,18.0603],'Rådhuset':[59.3302,18.0418],'Fridhemsplan':[59.3326,18.0290],'Stadshagen':[59.3373,18.0174],
  'Västra skogen':[59.3477,18.0039],'Solna centrum':[59.3588,17.9989],'Näckrosen':[59.3667,17.9833],'Hallonbergen':[59.3754,17.9692],'Kista':[59.4030,17.9444],'Husby':[59.4103,17.9256],
  'Huvudsta':[59.3496,17.9856],'Solna strand':[59.3542,17.9742],'Sundbybergs centrum':[59.3608,17.9721],'Duvbo':[59.3678,17.9644],'Rissne':[59.3758,17.9399],'Rinkeby':[59.3881,17.9286],'Tensta':[59.3946,17.9010],
  'Alvik':[59.3336,17.9802],'Kristineberg':[59.3326,18.0034],'Thorildsplan':[59.3317,18.0153],'S:t Eriksplan':[59.3396,18.0371],'Odenplan':[59.3429,18.0497],'Rådmansgatan':[59.3404,18.0587],'Hötorget':[59.3355,18.0634],
  'Gamla stan':[59.3233,18.0675],'Slussen':[59.3195,18.0721],'Medborgarplatsen':[59.3143,18.0735],'Skanstull':[59.3077,18.0763],'Gullmarsplan':[59.2991,18.0809],
  'Liljeholmen':[59.3105,18.0230],'Hornstull':[59.3157,18.0340],'Zinkensdamm':[59.3177,18.0500],'Mariatorget':[59.3170,18.0632],
  'Östermalmstorg':[59.3350,18.0740],'Karlaplan':[59.3389,18.0906],'Gärdet':[59.3466,18.0999],'Ropsten':[59.3573,18.1022],'Stadion':[59.3428,18.0815],'Tekniska högskolan':[59.3456,18.0716],'Universitetet':[59.3655,18.0549],
  'Nybroplan':[59.3329,18.0778],'Djurgårdsbron':[59.3312,18.0905],'Nordiska museet':[59.3290,18.0940],'Skansen':[59.3265,18.1030],
};
const STP={};for(const k in ST)STP[k]=P(...ST[k]);
const LINES=[
  {id:'B11',name:'Blå linjen 11',short:'Blå',col:'#0089CA',seq:['Kungsträdgården','T-Centralen','Rådhuset','Fridhemsplan','Stadshagen','Västra skogen','Solna centrum','Näckrosen','Hallonbergen','Kista','Husby']},
  {id:'B10',name:'Blå linjen 10',short:'Blå',col:'#0089CA',seq:['Västra skogen','Huvudsta','Solna strand','Sundbybergs centrum','Duvbo','Rissne','Rinkeby','Tensta']},
  {id:'G',name:'Gröna linjen',short:'Gröna',col:'#179D4D',seq:['Alvik','Kristineberg','Thorildsplan','Fridhemsplan','S:t Eriksplan','Odenplan','Rådmansgatan','Hötorget','T-Centralen','Gamla stan','Slussen','Medborgarplatsen','Skanstull','Gullmarsplan']},
  {id:'R13',name:'Röda linjen 13',short:'Röda',col:'#D71D24',seq:['Liljeholmen','Hornstull','Zinkensdamm','Mariatorget','Slussen','Gamla stan','T-Centralen','Östermalmstorg','Karlaplan','Gärdet','Ropsten']},
  {id:'R14',name:'Röda linjen 14',short:'Röda',col:'#D71D24',seq:['Östermalmstorg','Stadion','Tekniska högskolan','Universitetet']},
  {id:'T7',name:'Spårväg City 7',short:'Tram 7',col:'#878787',seq:['T-Centralen','Kungsträdgården','Nybroplan','Djurgårdsbron','Nordiska museet','Skansen'],tram:1},
];
function transitRoute(a,b){
  const adj={};LINES.forEach(L=>{for(let i=1;i<L.seq.length;i++){const u=L.seq[i-1],v=L.seq[i];(adj[u]=adj[u]||[]).push({v,L});(adj[v]=adj[v]||[]).push({v:u,L})}});
  const dist={},prev={},seen={},key=(s,l)=>s+'|'+l;const q=[];
  LINES.forEach(L=>{if(L.seq.includes(a)){dist[key(a,L.id)]=0;q.push([a,L.id])}});
  while(q.length){q.sort((x,y)=>dist[key(...x)]-dist[key(...y)]);const [s,l]=q.shift(),k0=key(s,l);if(seen[k0])continue;seen[k0]=1;
    const ls=LINES.find(x=>x.id===l).short;
    for(const {v,L} of adj[s]||[]){const c=dist[k0]+(L.tram?3:2)+(L.short===ls?0:4),k1=key(v,L.id);if(dist[k1]===undefined||c<dist[k1]){dist[k1]=c;prev[k1]=[s,l];q.push([v,L.id])}}}
  let best=null;LINES.forEach(L=>{const k=key(b,L.id);if(dist[k]!==undefined&&(best===null||dist[k]<dist[best]))best=k});
  if(!best)return null;
  const chain=[];let k=best;while(k){const [s,l]=k.split('|');chain.unshift({s,l});const p=prev[k];k=p?key(...p):null}
  const legs=[];chain.forEach((c,i)=>{const L=LINES.find(x=>x.id===c.l);const last=legs[legs.length-1];if(!last)legs.push({line:L,short:L.short,stops:[c.s]});else if(last.short!==L.short)legs.push({line:L,short:L.short,stops:[chain[i-1].s,c.s]});else last.stops.push(c.s)});
  return {min:dist[best],legs:legs.filter(l=>l.stops.length>1),stations:chain.map(c=>c.s)};
}
function nearestStation(x,z){let best=null,bd=1e9;for(const k in STP){const d=Math.hypot(STP[k][0]-x,STP[k][1]-z);if(d<bd){bd=d;best=k}}return {name:best,d:bd}}

const geography={O_LAT,O_LON,P,PP,WATER_FALLBACK,AREAS,HUB_R,ST,STP,LINES,transitRoute,nearestStation};
if(typeof module==='object'&&module&&module.exports)module.exports=geography;
else (root.StockholmLife=root.StockholmLife||{}).geography=geography;
})(globalThis);
