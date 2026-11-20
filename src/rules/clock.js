/* Stockholm Life: the game calendar and the one clock constant.
   START (day 1 of the game, Saturday 24 October 2026), dateOf (the calendar date of a game day), CLOCK_RATE (how many times
   faster than real time game time runs where it runs by itself: the station and the train today) and reachesMidnight (does
   adding hours to a time of day reach 24:00). Pure: no game state, no DOM, no three.js. The first two are the original code
   moved unchanged out of index.html (docs/MODULES.md, docs/M2_SPEC.md); CLOCK_RATE is the station's rate (CRATE, 4) given a
   name so that one number is used everywhere, and reachesMidnight is the test every writer of the hour already makes
   (`S.hour>=24`). Nothing here changes how game time passes (M2 stage 2).
   A classic script: index.html loads it after src/rules/sun.js and before the game script, which reads window.StockholmLife.clock.
   Node can require() it (tests/test_clock.py). */
(function(root){
'use strict';
const START=new Date(2026,9,24);
const dateOf=d=>{const x=new Date(START);x.setDate(x.getDate()+d-1);return x};
const CLOCK_RATE=4;
const reachesMidnight=(hour,h)=>hour+h>=24;
const clock={START,dateOf,CLOCK_RATE,reachesMidnight};
if(typeof module==='object'&&module&&module.exports)module.exports=clock;
else (root.StockholmLife=root.StockholmLife||{}).clock=clock;
})(globalThis);
