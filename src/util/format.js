/* Stockholm Life: number, money and time formatting.
   clamp, kr (Swedish kronor with a space as thousands separator and a real minus sign), hhmm (a clock time from
   hours, wrapping at 24) and fmtDur (a duration from minutes). Pure functions: no DOM, no game state, no three.js,
   no network. The bodies are the original ones, moved unchanged, with their rounding quirks (docs/MODULES.md).
   A classic script: index.html loads it before the game script, which reads window.StockholmLife.format.
   Node can require() it (tests/test_format.py). */
(function(root){
'use strict';
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
const kr=n=>(n<0?'−':'')+Math.abs(Math.round(n)).toString().replace(/\B(?=(\d{3})+(?!\d))/g,' ')+' kr';
const hhmm=h=>{h=((h%24)+24)%24;let hh=Math.floor(h),mm=Math.round((h-hh)*60);if(mm===60){hh=(hh+1)%24;mm=0}return String(hh).padStart(2,'0')+':'+String(mm).padStart(2,'0')};
const fmtDur=min=>min<60?Math.max(1,Math.round(min))+' min':Math.floor(min/60)+' h '+String(Math.round(min%60)).padStart(2,'0')+' min';

const format={clamp,kr,hhmm,fmtDur};
if(typeof module==='object'&&module&&module.exports)module.exports=format;
else (root.StockholmLife=root.StockholmLife||{}).format=format;
})(globalThis);
