/* Stockholm Life: game data tables.
   JOBS (the employers: name, district, hourly rate, requirements, certificate), COUNTRIES (nationality, flag,
   region code, flight-origin city and a flag, for the start screen and customs), OPEN (default opening hours by kind of place),
   COURSES (Komvux and other courses) and ITEMS (what the shops sell and the bag holds). Plain data with no functions and
   no reference to the game state; the original declarations, moved unchanged (docs/MODULES.md). The game reads
   them at the lines where they were declared and never changes them.
   A classic script: index.html loads it before the game script, which reads window.StockholmLife.tables.
   Node can require() it (tests/test_tables.py). */
(function(root){
'use strict';
const JOBS={
  foodora:{name:'Food courier (gig)',where:'any',rate:135,req:{},gig:1},
  barista:{name:'Barista, Södermalm',where:'sodermalm',rate:168,req:{svenska:15}},
  guide:{name:'Tour guide, Gamla stan',where:'gamlastan',rate:190,req:{social:40}},
  usk:{name:'Care assistant, S:t Göran',where:'kungsholmen',rate:205,req:{svenska:50}},
  dev:{name:'Developer, Kista',where:'kista',rate:340,req:{skill:60}},
  consult:{name:'Consultant, Östermalm',where:'ostermalm',rate:420,req:{skill:70,svenska:60,social:50}},
  cleaner:{name:'Cleaner (lokalvårdare), City',where:'tc',rate:158,req:{}},
  kitchen:{name:'Kitchen assistant, Södermalm',where:'sodermalm',rate:165,req:{svenska:10}},
  cook:{name:'Cook (kock), Östermalm',where:'ostermalm',rate:198,req:{svenska:25},cert:'kock'},
  warehouse:{name:'Warehouse worker, Kista',where:'kista',rate:178,req:{},cert:'truck'},
  barnsk:{name:'Barnskötare, preschool on Södermalm',where:'sodermalm',rate:186,req:{svenska:50},cert:'barn',rec:1},
  uskcert:{name:'Undersköterska, S:t Göran',where:'kungsholmen',rate:218,req:{svenska:50},cert:'usk'},
  itsup:{name:'IT support, Kista',where:'kista',rate:232,req:{skill:40},cert:'it'},
  taxidrv:{name:'Taxi driver',where:'any',rate:192,req:{svenska:40},cert:'taxi',lic:1,rec:1},
};
const COUNTRIES=[['Sweden','🇸🇪','se',1,100,'',0],['Nigeria','🇳🇬','noneu',0,0,'Lagos',0],['Ghana','🇬🇭','noneu',0,0,'Accra',0],['Kenya','🇰🇪','noneu',0,0,'Nairobi',0],['Ethiopia','🇪🇹','noneu',0,0,'Addis Ababa',0],['Eritrea','🇪🇷','noneu',0,0,'Asmara',0],
  ['Somalia','🇸🇴','noneu',0,0,'Mogadishu',0],['Egypt','🇪🇬','noneu',0,0,'Cairo',0],['Morocco','🇲🇦','noneu',0,0,'Casablanca',0],['South Africa','🇿🇦','noneu',0,0,'Johannesburg',0],['Syria','🇸🇾','noneu',0,0,'Damascus',0],['Iraq','🇮🇶','noneu',0,0,'Erbil',0],
  ['Iran','🇮🇷','noneu',0,0,'Tehran',0],['Afghanistan','🇦🇫','noneu',0,0,'Kabul',0],['Turkey','🇹🇷','noneu',0,0,'Istanbul',1],['Ukraine','🇺🇦','noneu',0,0,'Kyiv',0],['India','🇮🇳','noneu',0,0,'Delhi',0],['Pakistan','🇵🇰','noneu',0,0,'Karachi',0],
  ['Bangladesh','🇧🇩','noneu',0,0,'Dhaka',0],['Sri Lanka','🇱🇰','noneu',0,0,'Colombo',0],['China','🇨🇳','noneu',0,0,'Beijing',1],['Japan','🇯🇵','noneu',0,0,'Tokyo',0],['South Korea','🇰🇷','noneu',0,0,'Seoul',0],['Vietnam','🇻🇳','noneu',0,0,'Hanoi',0],
  ['Thailand','🇹🇭','noneu',0,0,'Bangkok',1],['Philippines','🇵🇭','noneu',0,0,'Manila',0],['Indonesia','🇮🇩','noneu',0,0,'Jakarta',0],['United States','🇺🇸','noneu',0,0,'New York',1],['Canada','🇨🇦','noneu',0,0,'Toronto',0],['Mexico','🇲🇽','noneu',0,0,'Mexico City',0],
  ['Brazil','🇧🇷','noneu',0,0,'São Paulo',0],['Colombia','🇨🇴','noneu',0,0,'Bogotá',0],['Chile','🇨🇱','noneu',0,0,'Santiago',0],['Australia','🇦🇺','noneu',0,0,'Sydney',0],['United Kingdom','🇬🇧','noneu',0,0,'London',1],
  ['Germany','🇩🇪','eu',1,0,'Frankfurt',1],['France','🇫🇷','eu',1,0,'Paris',1],['Spain','🇪🇸','eu',1,0,'Madrid',1],['Italy','🇮🇹','eu',1,0,'Rome',1],['Poland','🇵🇱','eu',1,0,'Warsaw',1],['Romania','🇷🇴','eu',1,0,'Bucharest',1],['Greece','🇬🇷','eu',1,0,'Athens',1],
  ['Netherlands','🇳🇱','eu',1,0,'Amsterdam',1],['Portugal','🇵🇹','eu',1,0,'Lisbon',1],['Estonia','🇪🇪','eu',1,0,'Tallinn',1],['Lithuania','🇱🇹','eu',1,0,'Vilnius',1],['Ireland','🇮🇪','eu',0,0,'Dublin',1],
  ['Finland','🇫🇮','nordic',1,30,'Helsinki',1],['Norway','🇳🇴','nordic',1,55,'Oslo',1],['Denmark','🇩🇰','nordic',1,50,'Copenhagen',1],['Iceland','🇮🇸','nordic',1,10,'Reykjavík',1]];

const OPEN={
  service:{wd:[9,16],label:'Mon–Fri 09–16'},bank:{wd:[10,15],label:'Mon–Fri 10–15'},
  sys:{wd:[10,19],sat:[10,15],label:'Mon–Fri 10–19, Sat 10–15'},vc:{wd:[8,17],label:'Mon–Fri 08–17'},
  sfi:{wd:[8,17],label:'Mon–Fri 08–17'},lib:{wd:[10,18],we:[11,16],label:'Mon–Fri 10–18'},
  sal:{wd:[9.5,19],sat:[9.5,16],label:'Mon–Sat'},skansen:{all:[10,16],label:'Daily 10–16'},vasa:{all:[10,17],label:'Daily 10–17'},
  apotek:{all:[8,21],label:'Daily 08–21'},galleria:{all:[10,20],label:'Daily 10–20'},migr:{wd:[9,15],label:'Mon–Fri 09–15'},
};
const COURSES={
  sva:{name:'Svenska som andraspråk (Komvux)',where:'kungsholmen',n:8,h:3,req:{svenska:40},gain:{svenska:4},cert:'sva',csn:1},
  usk:{name:'Undersköterska (Komvux vocational)',where:'kungsholmen',n:12,h:4,req:{svenska:45},gain:{skill:2},cert:'usk',csn:1},
  kock:{name:'Restaurant and cooking (Komvux)',where:'sodermalm',n:8,h:4,req:{svenska:20},gain:{skill:1},cert:'kock',csn:1},
  barn:{name:'Barnskötare (Komvux)',where:'sodermalm',n:10,h:4,req:{svenska:50},gain:{skill:1},cert:'barn',csn:1},
  truck:{name:'Warehouse and forklift licence (Arbetsförmedlingen)',where:'kista',n:5,h:4,req:{},gain:{skill:1},cert:'truck',af:1},
  stad:{name:'Professional cleaning (Arbetsförmedlingen)',where:'kista',n:3,h:4,req:{},gain:{},cert:'stad',af:1},
  it:{name:'IT support technician (YH)',where:'kista',n:12,h:4,req:{skill:40,svenska:30},gain:{skill:3},cert:'it',csn:1},
  taxi:{name:'Taxi driver ID (taxiförarlegitimation)',where:'tc',n:4,h:4,req:{svenska:40},gain:{},cert:'taxi',lic:1}};
const ITEMS={
  matlada:{n:'Ready meal (matlåda)',c:65,use:'eat',e:{hunger:40},at:['supermarket','convenience','kiosk','deli']},smorgas:{n:'Sandwich',c:49,use:'eat',e:{hunger:22},at:['cafe','convenience','kiosk','bakery','supermarket']},
  bulle:{n:'Kanelbulle',c:35,use:'eat',e:{hunger:12,fun:4,mood:2},at:['cafe','bakery','supermarket','convenience']},banan:{n:'Banana',c:6,use:'eat',e:{hunger:8},at:['supermarket','greengrocer','convenience']},
  godis:{n:'Lösgodis (pick-and-mix)',c:39,use:'eat',e:{hunger:5,fun:8,mood:2},at:['supermarket','convenience','kiosk']},kaffe:{n:'Coffee to go',c:38,use:'eat',e:{energy:12,mood:2},at:['cafe','convenience','kiosk','bakery']},
  vatten:{n:'Bottle of water',c:22,use:'eat',e:{energy:2,hunger:2},at:['supermarket','convenience','kiosk']},energy:{n:'Energy drink',c:25,use:'eat',e:{energy:16,mood:-1},at:['supermarket','convenience','kiosk']},
  paraply:{n:'Umbrella',c:179,use:'keep',s:'No mood loss from rain while you carry it',at:['supermarket','convenience','department_store','variety_store']},
  alvedon:{n:'Paracetamol (Alvedon)',c:45,use:'med',e:{mood:4,energy:6},s:'Eases a cold or a fever',at:['pharmacy','supermarket']},tval:{n:'Soap and shampoo',c:69,use:'keep',s:'+10 hygiene every time you shower at home',at:['supermarket','pharmacy','chemist','convenience']},
  blommor:{n:'Flowers',c:199,use:'gift',s:'Give to your partner or a date: +romance',at:['florist','supermarket']},vin:{n:'Bottle of wine',c:119,use:'eat',e:{fun:10,mood:3,energy:-6},s:'Systembolaget only · you must be 20+',at:['alcohol']},
  hemmat:{n:'Food from home',c:0,use:'eat',e:{hunger:25,mood:4},at:[]},sim:{n:'Prepaid SIM card',c:99,use:'keep',s:'Swedish phone number: mobile data and calls',at:['convenience','kiosk','mobile_phone','electronics']},laddare:{n:'Phone charger',c:199,use:'keep',at:['electronics','mobile_phone','department_store']}};

const tables={JOBS,COUNTRIES,OPEN,COURSES,ITEMS};
if(typeof module==='object'&&module&&module.exports)module.exports=tables;
else (root.StockholmLife=root.StockholmLife||{}).tables=tables;
})(globalThis);
