/* Stockholm Life: real Stockholm time (docs/REALTIME_SPEC.md, R1).
   The one place that answers "what time and date is it in Stockholm": the zone Europe/Stockholm, daylight saving included.
   Pure: no game state, no DOM, no three.js. Not used by the game yet (R1 adds it with tests; R2 onward switch the game to it).
   nowMs() is Date.now() plus the device clock's error (setOffset, learned from a server's Date header, so a wrong device clock does not matter), unless a fake time is set with setFakeNow(ms) (for tests; setFakeNow(null) clears it), so no test has
   to wait for real time. partsAt(ms) gives the Stockholm wall-clock parts; hourAt(ms) the hour of day as a fraction (0 to <24);
   dayNumber(ms) the Stockholm calendar day as a whole number (days since 1970-01-01); lifeDay(startMs, ms) the day count of a
   life that began at startMs (1 on the day it began); startOfDay(ms) and dayLengthHours(ms) the real length of that Stockholm
   day (23 h when the clocks go forward, 25 h when they go back); weekday(ms) 0 (Sunday) to 6.
   A classic script; Node can require() it (tests/test_stockholm_time.py). */
(function(root){
'use strict';
const TZ='Europe/Stockholm';
const fmt=new Intl.DateTimeFormat('en-GB',{timeZone:TZ,hourCycle:'h23',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit'});
let fake=null,offset=0;
// offset: how far the device clock is from the true time, learned from a server's Date header (setOffset); nowMs() is the true time
const nowMs=()=>fake===null?Date.now()+offset:fake;
const setOffset=ms=>{if(!Number.isFinite(+ms))throw new RangeError('setOffset needs a number of milliseconds');offset=+ms};
const getOffset=()=>offset;
const setFakeNow=ms=>{if(ms===null||ms===undefined){fake=null;return}if(!Number.isFinite(+ms))throw new RangeError('setFakeNow needs a number of milliseconds or null');fake=+ms};
function partsAt(ms){const o={};for(const p of fmt.formatToParts(new Date(ms)))if(p.type!=='literal')o[p.type]=+p.value;return {year:o.year,month:o.month,day:o.day,hour:o.hour,minute:o.minute,second:o.second}}
const hourAt=ms=>{const p=partsAt(ms);return p.hour+p.minute/60+p.second/3600};
const dayNumber=ms=>{const p=partsAt(ms);return Math.floor(Date.UTC(p.year,p.month-1,p.day)/86400000)};
const lifeDay=(startMs,ms)=>dayNumber(ms)-dayNumber(startMs)+1;
const weekday=ms=>{const p=partsAt(ms);return new Date(Date.UTC(p.year,p.month-1,p.day)).getUTCDay()};
// the first instant of the Stockholm day that contains ms: search back over at most 26 hours
function startOfDay(ms){const d=dayNumber(ms);let lo=ms-26*3600000,hi=ms;while(hi-lo>1000){const mid=Math.floor((lo+hi)/2);if(dayNumber(mid)<d)lo=mid;else hi=mid}return hi}
const dayLengthHours=ms=>{const s=startOfDay(ms);return Math.round((startOfDay(s+26*3600000)-s)/60000)/60};
const api={TZ,nowMs,setFakeNow,setOffset,getOffset,partsAt,hourAt,dayNumber,lifeDay,weekday,startOfDay,dayLengthHours};
if(typeof module==='object'&&module&&module.exports)module.exports=api;
else (root.StockholmLife=root.StockholmLife||{})['stockholm-time']=api;
})(globalThis);
