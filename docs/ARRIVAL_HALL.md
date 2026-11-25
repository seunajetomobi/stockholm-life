# Arlanda arrivals hall: design and research notes

Status: **in progress on branch `feat/arrival-hall`** (requested by the owner 2026-11-23). Facts below were checked on 2026-11-23.

## What the owner asked for
A wider, rebuilt arrivals hall with a longer baggage belt and other passengers waiting for their bags; customs officers in customs uniform; immigration officers where you show your passport (outside the Schengen area); a luggage trolley the character can take; buses, cars and taxis at the entrance, waiting for or picking up passengers; the character carrying a backpack and hand luggage; and information pop-ups that never overlap on a computer, laptop, tablet or phone.

## Layout (north to south; 1 unit = 50 m, the hall is about 58 m by 50 m)
1. Gate corridor with the welcome sign.
2. Passport control: eight booths, four for EU/EEA/CH passports and four for all passports, a gate in the middle, queues behind tape. Only after a flight from outside the Schengen area (this is the existing rule, `S.schengen`).
3. Baggage hall: belt 4 (your flight) as a long racetrack, belts 3 and 5 along the walls, passengers waiting (some with trolleys), trolley racks on both sides.
4. Customs: green, red and (after an EU flight) blue lane, with uniformed officers and an inspection table at the red lane.
5. Arrivals hall: people waiting with name signs, Pressbyrån, an information desk, glass doors.
6. The kerb: taxis, Flygbussarna coaches and private cars that arrive, wait and leave.

## Sources
| Fact | Source | Checked |
| --- | --- | --- |
| You go through customs in Terminal 5 and leave through its arrivals hall | [Swedavia: For those arriving at Arlanda](https://www.swedavia.com/arlanda/arriving-at-arlanda/) | 2026-11-23 |
| Swedavia's contracted taxis wait outside the Terminal 5 arrivals hall; taxi rank officers help; taxis run 24 hours at Terminals 2 and 5 | [Swedavia: Taxi services to/from Arlanda](https://swedavia.com/arlanda/taxi) | 2026-11-23 |
| Flygbussarna, bus4you and FlixBus use a stop outside Terminal 5; drivers collecting someone wait outside the arrivals hall or use the pick-up car park | [Swedavia: Pick-up at Terminal 5](https://www.swedavia.com/arlanda/pick-up-at-terminal-5/) | 2026-11-23 |
| Arlanda Express stops at Arlanda North, under Terminal 5 | [Swedavia: transport](https://www.swedavia.com/arlanda/transport/) | 2026-11-23 |
| Customs officers wear uniform when they deal directly with the public at clearance and control | [Tullverket regulation (PDF)](https://www.tullverket.se/download/18.e0158eb140f9d5442d3240/1393594689517/2012018.pdf) | 2026-11-23 |

## Not verified, so stylised or left out
- **Uniforms.** Drawn from a reference photo supplied by the owner on 2026-11-23: a dark navy jacket and cap; customs add a yellow hi-vis vest with blue panels and a blue-and-white check trim, a radio and a "TULL Customs" sleeve badge with the state arms. Passport-control officers wear the same police-style navy uniform and differ only in the sleeve badge (Polisen or Migrationsverket), as the owner described. The badges are stylised drawings, not copies of the real insignia.
- **Which authority runs passport control at Arlanda.** The game keeps its existing wording (Gränspolisen, the border police). Check with Polisen before treating it as final.
- **Luggage trolleys are free**: stated by the owner on 2026-11-23; no Swedavia page confirming it was found. The rack signs say "free".
- **Coach colours and the exact Terminal 5 floor plan.** The hall is a readable game layout, not a survey. The colours of the Flygbussarna coaches are guesses.
- **The "other flights" on the arrivals board are simulated** and labelled so.

## Tests
`tests/test_arrival_hall.py`: the hall renders at laptop, tablet and phone sizes without errors, and no two HUD elements overlap at six screen sizes at five points along the route, with the guide open and closed.
