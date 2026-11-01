# Product vision

**STOCKHOLM LIFE — Live your own story.**

A single-player-first, realistic Stockholm life simulation where the player builds a life through exploration, housing, employment, finances, relationships, transportation, education, personal progression and interaction with a living city: arriving, finding a home and work, building relationships and choosing where their life goes.

This document states the agreed direction. What exists today is in [FEATURE_INVENTORY.md](FEATURE_INVENTORY.md); the order of work is in [MASTER_ROADMAP.md](MASTER_ROADMAP.md).

## Direction

- **Single-player first.** Every system is designed and finished for one player. Multiplayer is a future possibility, prepared for in the architecture (see below) but not built until the single-player game is complete.
- **A realistic, recognisable Stockholm.** Real streets, buildings, transit lines, places and Swedish everyday rules (papers, banking, rent, taxes, healthcare), grounded in open data and checked facts.
- **Simulation-driven, not menu-driven.** Things happen in the world: you travel there, enter the building, meet the person, do the work. Menus and the phone support the simulation; they do not replace it.
- **Freedom with meaningful choices.** Several life paths, real trade-offs (time, money, energy, relationships) and consequences that persist.
- **A balanced mix:** exploration, life simulation, social life, careers, economy, transport and personal progression, each connected to the others rather than built as an isolated feature.

## What the finished game includes

| Pillar | Ambition |
| --- | --- |
| The city | A detailed, explorable Stockholm with day and night, weather, seasons and visible city activity |
| Buildings | Enterable buildings with functional interiors: homes, workplaces, shops, authorities, venues |
| Work and study | Employment with salaries and careers, playable work, education and qualifications |
| Home | Renting, the housing queue, buying, and furnishing and customising a home |
| Money | Personal finances, bills, taxes, shopping and an inventory |
| People | NPCs with homes, schedules, personalities, memories and relationships with the player and each other |
| Getting around | Walking, public transport, driving and taxis on the real network |
| Progression | Goals, missions and multiple life paths with lasting consequences |
| Later | A multiplayer expansion built on the same simulation |

## The first complete experience: "Your first week in Stockholm"

The first milestone that delivers the vision end to end is one complete week for a newcomer in a compact area (Norrmalm and Vasastan, around Stockholm Central and Odenplan):

1. Arrive at Stockholm Central and walk to a sublet viewing; sign it and move in.
2. Get a personnummer at Skatteverket, open a bank account, buy groceries and cook at home.
3. Apply for a café job and attend the interview at its set time.
4. Commute by T-bana and work playable shifts; meet a coworker and a neighbour who follow their own schedules.
5. Pay rent and bills; finish the week with a summary of money, papers and relationships, and the next goals.

Its systems, acceptance criteria and tests are defined in MASTER_ROADMAP.md (M4). Everything outside the area keeps working as it does today.

## Principles for development

1. **Connected over isolated.** A feature is done when it works with the systems around it (time, money, saving, places, people), not when its screen exists.
2. **Evolve, don't rewrite.** The existing code and data are kept and improved step by step, guarded by automated tests.
3. **Honest status.** A system counts as functional only when its behaviour works and is tested; buttons and visuals alone do not count.
4. **Facts are checked and dated.** Prices, fees and rules come from real sources and are reviewed regularly.
5. **Nothing reaches players untested.** Every release goes through the tested, approval-gated deployment pipeline; merging alone never publishes.
6. **District by district.** Stockholm becomes playable area by area, each with meaningful activities and interiors, rather than thinly everywhere at once.
7. **Living people, not records.** NPCs are simulated with homes, schedules and behaviour; economy, employment, housing and transport stay connected to them and to each other.
8. **Measure before optimising.** Performance claims rest on measurements on real devices.

## Multiplayer: a future possibility

Multiplayer is not planned for the near term. To keep it possible later, new systems should: keep the game state separate from rendering; change state through explicit, recordable actions; use seeded randomness; and keep time on an explicit game clock. These preparations are milestone M8 in the roadmap and do not include a server.

## Not goals for now

- Multiplayer, accounts or cloud saves.
- A city-wide set of interiors or NPC behaviours before the first-week slice works.
- Visual overhauls before performance has been measured.
- New menu-only features that widen the gap between the phone and the world.
