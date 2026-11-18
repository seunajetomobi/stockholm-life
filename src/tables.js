/* Stockholm Life: game data tables.
   JOBS (the employers: name, district, hourly rate, requirements, certificate) and COUNTRIES (nationality, flag,
   region code, flight-origin city and a flag, for the start screen and customs). Plain data with no functions and
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

const tables={JOBS,COUNTRIES};
if(typeof module==='object'&&module&&module.exports)module.exports=tables;
else (root.StockholmLife=root.StockholmLife||{}).tables=tables;
})(globalThis);
