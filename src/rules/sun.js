/* Stockholm Life: the sun and the weather-code tables.
   sunInfo (day length, solar noon and the highest sun for a date), daylight, sunrise, sunset and isLight (is an hour of
   that date in daylight), and the WMO weather-code tables WMO, wmo and WXICON. Pure functions of their arguments: the
   date is passed in (the game script passes its current game date), so there is no game state, no DOM, no three.js and
   no network here. The latitude is fixed (Stockholm), the sun is the original approximation, and the bodies are the
   original ones moved unchanged (docs/MODULES.md): only `today()` became the argument `d`.
   A classic script: index.html loads it after src/util/format.js (it needs clamp) and before the game script, which reads
   window.StockholmLife.sun. Node can require() it (tests/test_sun.py). */
(function(root){
'use strict';
const fmt=(typeof module==='object'&&module&&module.exports)?require('../util/format.js'):(root.StockholmLife&&root.StockholmLife.format);
if(!fmt)throw new Error('src/rules/sun.js needs src/util/format.js loaded first');
const {clamp}=fmt;
const RAD=Math.PI/180,LAT=59.33;
function lastSun(y,m){const d=new Date(y,m+1,0);d.setDate(d.getDate()-d.getDay());return d}
function sunInfo(d){const y=d.getFullYear(),N=Math.round((d-new Date(y,0,0))/864e5);
  const dec=23.44*Math.sin(2*Math.PI*(284+N)/365)*RAD;const cosH=(Math.sin(-0.833*RAD)-Math.sin(LAT*RAD)*Math.sin(dec))/(Math.cos(LAT*RAD)*Math.cos(dec));
  const H=Math.acos(clamp(cosH,-1,1))/RAD;const B=2*Math.PI*(N-81)/364,eot=9.87*Math.sin(2*B)-7.53*Math.cos(B)-1.5*Math.sin(B);
  const dst=d>=lastSun(y,2)&&d<lastSun(y,9);const noon=12-(18.06-15)*4/60-eot/60+(dst?1:0);
  return {dl:2*H/15,noon,maxEl:90-LAT+dec/RAD}}
const daylight=d=>sunInfo(d).dl;
const sunrise=d=>{const s=sunInfo(d);return s.noon-s.dl/2},sunset=d=>{const s=sunInfo(d);return s.noon+s.dl/2};
const isLight=(h,d)=>h>=sunrise(d)&&h<=sunset(d);
const WMO={0:['Clear sky','clear'],1:['Mainly clear','clear'],2:['Partly cloudy','cloud'],3:['Overcast','cloud'],45:['Fog','cloud'],48:['Freezing fog','cloud'],51:['Light drizzle','rain'],53:['Drizzle','rain'],55:['Heavy drizzle','rain'],56:['Freezing drizzle','rain'],57:['Freezing drizzle','rain'],
  61:['Light rain','rain'],63:['Rain','rain'],65:['Heavy rain','rain'],66:['Freezing rain','rain'],67:['Freezing rain','rain'],71:['Light snow','snow'],73:['Snow','snow'],75:['Heavy snow','snow'],77:['Snow grains','snow'],
  80:['Rain showers','rain'],81:['Rain showers','rain'],82:['Violent rain showers','rain'],85:['Snow showers','snow'],86:['Heavy snow showers','snow'],95:['Thunderstorm','rain'],96:['Thunderstorm with hail','rain'],99:['Thunderstorm with hail','rain']};
const wmo=c=>WMO[c]||['Unknown','cloud'];
const WXICON=c=>c<=1?'☀':c===2?'⛅':c<=3?'☁':c<=48?'🌫':c>=95?'⛈':wmo(c)[1]==='snow'?'❄':'🌧';
const sun={RAD,LAT,lastSun,sunInfo,daylight,sunrise,sunset,isLight,WMO,wmo,WXICON};
if(typeof module==='object'&&module&&module.exports)module.exports=sun;
else (root.StockholmLife=root.StockholmLife||{}).sun=sun;
})(globalThis);
