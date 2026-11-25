# Accounts, events and game rooms: proposal

Status: **proposed 2026-11-23 on the owner's request; nothing built; every item below needs the owner's decision before work starts.** These features need a server, which the game does not have today (it is a static site plus a flights relay). That is an architectural change and a product decision (AGENTS.md, approval boundaries).

## What the owner asked for (2026-11-23)
1. A **login or sign-up** entry on the title menu. Only logged-in people can **save**. Sign-in through Facebook, Google and other suitable platforms.
2. People can **see and read about events happening around them**.
3. A **chat room** where people join to play games: billiards or snooker, chess, card games, puzzle games, word games and others.

## Today
- No server and no accounts. A life is saved in the browser (`localStorage`, five slots, export and import of a file; `docs/TECHNICAL_ARCHITECTURE.md`).
- Hosting: Cloudflare Workers static assets (`stockholmsliv.app`). A separate Cloudflare Worker is the flights, news and queue relay.

## 1. Accounts and cloud saves

### Decisions for the owner
| # | Question | Recommendation |
| --- | --- | --- |
| A1 | Must a player be logged in to save? | **No: keep local saves for guests, add cloud saves for accounts.** "Only accounts can save" would make every guest lose progress when they close the tab, and it breaks the five local slots people already use. If you still want it, say so and guests will play without any save. |
| A2 | Which providers? | Google, Facebook, Apple, Microsoft, GitHub, Discord and e-mail (a one-time link). Google and Facebook cover most people; Apple is needed if there is ever an iOS app; the rest are cheap to add once the first two work. |
| A3 | Who runs the accounts? | A hosted service (Clerk, Auth0, Supabase Auth or Firebase Auth) is faster and safer than writing login ourselves. Cost and data location differ (see below). |
| A4 | Where do cloud saves live? | Cloudflare D1 (SQLite) behind a Worker, one row per save slot, versioned. |

### What the owner has to do (nobody else can)
- Create the developer apps: Google Cloud (OAuth consent screen, then **verification** by Google for a public app), Meta for Developers (app review, privacy-policy URL and a data-deletion URL are mandatory), and any other provider chosen. These are in the owner's accounts and carry the owner's name and legal responsibility.
- Approve a **privacy policy and terms**: players in the EU have GDPR rights (access, export, deletion, consent). Players under 13 cannot consent in Sweden; decide the age limit.
- Put the client secrets in Cloudflare as Worker secrets. They never enter the repository.

### Design sketch
- A Worker (`/auth/*`, `/saves/*`) on the same domain, so cookies are first-party. Session cookie: `HttpOnly`, `Secure`, `SameSite=Lax`.
- OAuth 2.0 authorisation-code flow with PKCE and a `state` check; only the provider's stable user id and a display name are stored. No friends list or other data is requested.
- Saves: the existing save envelope (`v` and slots) is uploaded as a blob with a version number. On login the game compares timestamps and asks which to keep (never overwrites silently). Existing local saves can be uploaded once.
- Deletion: one button deletes the account and its saves.

### Risks
- Provider review times (Facebook and Google can take days to weeks).
- Account takeover and abuse: rate limits, no password storage, short-lived sessions.
- Losing the account means losing the cloud save: keep export-to-file.

## 2. Events around you

"Around you" in the game means **near your avatar in Stockholm**, not the player's real location, so no location permission is needed.

| Source | Notes |
| --- | --- |
| Ticketmaster Discovery API | Free key, Stockholm venues and dates. Terms require attribution and linking to the ticket page. |
| Visit Stockholm and the City of Stockholm's open data | Free, but formats and licences vary; each source needs a read of its terms. |
| Events created inside the game | Our own list; the owner or players add them. No licence problem. |

### Decisions
- E1: which sources? Recommendation: start with one licensed API plus in-game events.
- E2: where shown? Recommendation: a phone app "Events" (list near your avatar's district, tap to read details, a link to the source), plus a pin on the map.
- A key per source is the owner's. Real facts shown in the game must carry the source and the date checked (AGENTS.md rule 8).

## 3. Game rooms with chat

Needs a **real-time server**: Cloudflare Durable Objects with WebSockets (a Workers paid plan, about 5 US dollars a month at the time of writing; check before relying on it).

### Phases
1. **Lobby and text chat**, rooms by game, display names, moderation tools: report, mute, block, a word filter, rate limits, and the owner or moderators able to remove people. Public chat with strangers is the highest-risk part (harassment, children, personal data). Players under 18 should not be put in open chat with adults without the owner's decision.
2. **Turn-based games** (easy over a socket, rules checked on the server so nobody can cheat): chess, checkers, backgammon, tic-tac-toe, connect four, Ludo, card games (Uno-style, whist, and similar), word games and puzzle races. **Play money or points only; no gambling, no real money.** Word games need word lists with clear licences.
3. **Real-time physics games**: pool and snooker. A server-authoritative physics engine (or deterministic replay), latency handling, a table model. The hardest item; build after the rest works.

### Decisions
- G1: age limit and moderation owner (who reads reports).
- G2: the first three games. Recommendation: chess, a card game and a word game.
- G3: accept the monthly cost.

## Suggested order
| Step | What | Needs from the owner |
| --- | --- | --- |
| 1 | Decisions A1 to A4, privacy policy and terms | Decisions; a legal read of the policy |
| 2 | Worker with Google sign-in only, cloud saves, upload of local saves | A Google Cloud OAuth app; Worker secrets |
| 3 | Facebook and the other providers | Meta app review |
| 4 | Events app (one source plus in-game events) | An API key |
| 5 | Lobby and chat, with moderation | G1; Workers paid plan |
| 6 | First turn-based games | G2 |
| 7 | Pool and snooker | after step 6 |

Every step is its own pull request with tests; the game keeps working for guests at every step.
