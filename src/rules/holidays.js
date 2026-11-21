/* Stockholm Life: Swedish public holidays (allmänna helgdagar), computed from the statute.
   Source: Lag (1989:253) om allmänna helgdagar, 1 and 2 §§, consolidated text on lagen.nu (https://lagen.nu/1989:253), last
   amendment shown SFS 2004:1320; read and checked on 2026-11-21. Public holidays: Sundays (Easter Day and Whit Sunday among them),
   New Year's Day (1 Jan), Epiphany (6 Jan), Good Friday, Easter Monday, 1 May, Ascension Day (sixth Thursday after Easter Day),
   the National Day (6 Jun), Midsummer Day (the Saturday 20-26 Jun), All Saints' Day (the Saturday 31 Oct-6 Nov), Christmas Day
   and Boxing Day. NOT public holidays by the statute: Whit Monday (since 2005), Midsummer Eve, Christmas Eve, New Year's Eve; they are
   returned as kind 'eve' because most workplaces and shops treat them like one (an agreement, not the law).
   Easter Day is the Sunday after the ecclesiastical full moon on or after 21 March (the Gregorian computus below, valid 1583 on).
   easterSunday(year) -> {month, day} (month 1-12); holidays(year) -> [{month, day, key, sv, en, kind:'red'|'eve'}] by date;
   holidayOn(year, month, day) -> that entry or null (Sundays are not entries); isRedDay(year, month, day) -> true for a Sunday or a
   'red' entry. Pure: no game state, no DOM, no clock. A classic script; Node can require() it (tests/test_holidays.py). */
(function(root){
'use strict';
function easterSunday(y){const a=y%19,b=Math.floor(y/100),c=y%100,d=Math.floor(b/4),e=b%4,f=Math.floor((b+8)/25),g=Math.floor((b-f+1)/3),
  h=(19*a+b-d-g+15)%30,i=Math.floor(c/4),k=c%4,l=(32+2*e+2*i-h-k)%7,m=Math.floor((a+11*h+22*l)/451),n=h+l-7*m+114;return {month:Math.floor(n/31),day:n%31+1}}
const plus=(y,m,d,n)=>{const t=new Date(Date.UTC(y,m-1,d+n));return {month:t.getUTCMonth()+1,day:t.getUTCDate()}};
const dow=(y,m,d)=>new Date(Date.UTC(y,m-1,d)).getUTCDay();
const saturdayFrom=(y,m,d)=>{let x=d;while(dow(y,m,x)!==6)x++;return x};   // the Saturday on or after m/d
function holidays(y){const E=easterSunday(y),L=[];
  const add=(md,key,sv,en,kind)=>L.push({month:md.month,day:md.day,key,sv,en,kind:kind||'red'});
  add({month:1,day:1},'newyear','Nyårsdagen',"New Year's Day");
  add({month:1,day:6},'epiphany','Trettondedag jul','Epiphany');
  add(plus(y,E.month,E.day,-2),'goodfriday','Långfredagen','Good Friday');
  add(E,'easter','Påskdagen','Easter Day');
  add(plus(y,E.month,E.day,1),'eastermonday','Annandag påsk','Easter Monday');
  add({month:5,day:1},'mayday','Första maj','May Day');
  add(plus(y,E.month,E.day,39),'ascension','Kristi himmelsfärdsdag','Ascension Day');
  add(plus(y,E.month,E.day,49),'whitsun','Pingstdagen','Whit Sunday');
  add({month:6,day:6},'national','Nationaldagen','National Day');
  add({month:6,day:saturdayFrom(y,6,20)-1},'midsummereve','Midsommarafton','Midsummer Eve','eve');
  add({month:6,day:saturdayFrom(y,6,20)},'midsummer','Midsommardagen','Midsummer Day');
  const as=saturdayFrom(y,10,31);add(as>31?{month:11,day:as-31}:{month:10,day:as},'allsaints','Alla helgons dag',"All Saints' Day");
  add({month:12,day:24},'christmaseve','Julafton','Christmas Eve','eve');
  add({month:12,day:25},'christmas','Juldagen','Christmas Day');
  add({month:12,day:26},'boxing','Annandag jul','Boxing Day');
  add({month:12,day:31},'newyeareve','Nyårsafton',"New Year's Eve",'eve');
  return L.sort((a,b)=>a.month-b.month||a.day-b.day)}
const holidayOn=(y,m,d)=>holidays(y).find(h=>h.month===m&&h.day===d)||null;
const isRedDay=(y,m,d)=>dow(y,m,d)===0||(holidayOn(y,m,d)||{}).kind==='red';
const api={easterSunday,holidays,holidayOn,isRedDay};
if(typeof module==='object'&&module&&module.exports)module.exports=api;
else (root.StockholmLife=root.StockholmLife||{}).holidays=api;
})(globalThis);
