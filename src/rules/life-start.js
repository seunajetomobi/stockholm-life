/* Stockholm Life: where a life starts on the real calendar (real-time stage R1b, docs/REALTIME_SPEC.md).
   Under real time, game day N is the Stockholm calendar day that is N-1 days after the day the life began, so a save needs
   `t0`: the real moment (ms since 1970) of the Stockholm midnight that began day 1 of that life.
   lifeStartFor(day, nowMs): the t0 that makes "today" in Stockholm equal `day`; used to migrate a save that has none.
   ensureLifeStart(s, nowMs): sets s.t0 on a save that lacks a usable one and leaves a good one alone; safe to run again.
   Pure: no game state, no DOM. Not used by the game yet (the save does not carry t0 until the stage that bumps its version).
   A classic script; Node can require() it (tests/test_life_start.py). Depends on src/rules/stockholm-time.js. */
(function(root){
'use strict';
const T=typeof module==='object'&&module&&module.exports?require('./stockholm-time.js'):root.StockholmLife['stockholm-time'];
const lifeStartFor=(day,nowMs)=>{
  if(!Number.isFinite(day)||day<1)throw new RangeError('day must be 1 or more');
  /* The UTC noon of the target calendar date is 13:00 or 14:00 in Stockholm, so it is inside that date whatever the clock change. */
  return T.startOfDay((T.dayNumber(nowMs)-(Math.floor(day)-1))*86400000+12*3600000)};
const ensureLifeStart=(s,nowMs)=>{
  if(!s)return s;
  if(!Number.isFinite(s.t0)||s.t0<=0||s.t0>nowMs)s.t0=lifeStartFor(Number.isFinite(s.day)?s.day:1,nowMs);
  return s};
const api={lifeStartFor,ensureLifeStart};
if(typeof module==='object'&&module&&module.exports)module.exports=api;
else (root.StockholmLife=root.StockholmLife||{})['life-start']=api;
})(globalThis);
