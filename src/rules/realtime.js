/* Stockholmsliv: the real-time switch and the derived game clock (real-time stages R2 and R3, docs/REALTIME_SPEC.md).
   enabled(search, storage): is real time on? Off unless the caller passes dflt=true (the game does: real time is the product decision). On when the address has ?realtime=1, or when the developer flag
   `stockholmsliv-realtime` is "1" in localStorage; "0" there or `?realtime=0` turns it off; a missing or unreadable storage gives dflt.
   deriveClock(t0, nowMs): {day, hour} for a life that began at t0: day is the Stockholm calendar day count of the life (day 1 on the
   day it began) and hour the Stockholm time of day as a decimal (14.5 is 14:30), so that with real time on nothing writes the hour.
   fakeNow(search, storage): the milliseconds from a `?fakeclock=<ISO date-time>` address, only when the developer flag
   `stockholmsliv-dev` is "1"; otherwise null, so the live game has no skip.
   Pure: no game state, no DOM. Not used by the game yet. A classic script; Node can require() it (tests/test_realtime.py). */
(function(root){
'use strict';
const T=typeof module==='object'&&module&&module.exports?require('./stockholm-time.js'):root.StockholmLife['stockholm-time'];
const flag=(storage,k)=>{try{return !!storage&&storage.getItem(k)==='1'}catch(e){return false}};
const stored=(storage,k)=>{try{return storage?storage.getItem(k):null}catch(e){return null}};
const param=(search,k)=>{try{const v=new URLSearchParams(search||'').get(k);return v===null?null:v}catch(e){return null}};
const enabled=(search,storage,dflt)=>{const p=param(search,'realtime');if(p==='1')return true;if(p==='0')return false;const v=stored(storage,'stockholmsliv-realtime');if(v==='1')return true;if(v==='0')return false;return !!dflt};
const deriveClock=(t0,nowMs)=>{
  if(!Number.isFinite(t0)||!Number.isFinite(nowMs))throw new RangeError('deriveClock needs two times in milliseconds');
  const p=T.partsAt(nowMs);return{day:T.lifeDay(t0,nowMs),hour:p.hour+p.minute/60+p.second/3600}};
const fakeNow=(search,storage)=>{if(!flag(storage,'stockholmsliv-dev'))return null;const v=param(search,'fakeclock');if(!v)return null;const ms=Date.parse(v);return Number.isFinite(ms)?ms:null};
const api={enabled,deriveClock,fakeNow};
if(typeof module==='object'&&module&&module.exports)module.exports=api;
else (root.StockholmLife=root.StockholmLife||{}).realtime=api;
})(globalThis);
