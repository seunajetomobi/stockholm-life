# Interface rebuild: audit and plan

Status: **proposed 2026-11-21 on the owner's request ("rebuild the interface"); nothing built.** Direction chosen by default: phone first, desktop second (the owner has not said otherwise). The owner approves the mock-up before stage U1 starts, because it changes what players see.

## What the interface is today (read in `index.html`, 2026-11-21)
| Part | Element | Notes |
| --- | --- | --- |
| Top board | `header#board`: brand, clock `#time`/`#date`, `#where`, `#money`/`#jobline`, `#needs`, daylight bar, sky meta | One dense strip; the clock shows a game time that real time (docs/REALTIME_SPEC.md) replaces |
| World overlays | `#places` (places bar), `#next`, `#ride`, `#hint`, `.ctrls` (find, zoom, centre), `#inhud`, `#csPrompt`/`#csHud`, `#drivehud`, `#joy`, `#runbtn` | Many absolutely placed overlays; each phone breakpoint moves several by hand (`bottom: calc(196px + …)`) |
| Bottom dock | `nav#dock`: Here, Phone, Me, Society, Diary | Five tabs, opens the drawer |
| Drawer | `aside#drawer` with panes `here`, `phone`, `me`, `civic`, `diary` | Bottom sheet on phones, 400 px side panel from 900 px |
| Modals | `#modalRoot` (40 uses in tests) | Used by almost every menu |
| Breakpoints | 520, 600, 640, 899, 900, 1000, 1100 px | Seven, scattered through the CSS |

## Findings (to confirm with a screenshot pass before U1)
1. Overlay positions are hard-coded against each other (`196px`, `250px`), so adding one chip, such as the real-time status chip, means retuning several breakpoints.
2. The top board carries game-clock assumptions that stop being true under real time (date, "day N", season progress).
3. Nothing shows the things real time adds: live Stockholm time and weather source, an open/closed state, a timed activity in progress, offline catch-up.
4. Only 4 of 28 test files touch the shell (`#dock`, `#board`, `#places`, `#joy`/`#runbtn`, `data-tab`); `#modalRoot` is used everywhere. So the shell can change if those ids and `data-*` hooks stay.

## Approach: evolve, do not rewrite
AGENTS.md rule 3 forbids a rewrite without an approved reason, and the tests do not need one. Keep element ids and `data-*` hooks, change layout and CSS, add elements, move one panel at a time.

| Stage | What | Test evidence |
| --- | --- | --- |
| U0 | Screenshot pass at 390, 768, 1280 px (an agent-written Playwright script, kept in `tests/`, no new dependency); the owner approves the mock-up | screenshots attached to the PR |
| U1 | Layout tokens: one set of CSS variables for board height, dock height and gutters, replacing the hard-coded offsets; one breakpoint set (phone below 640, desktop from 900) | the 4 shell test files plus full suite |
| U2 | Status strip: live Stockholm clock and date, weather with source and age, open/closed hint (needs R2 of the real-time plan) | new test per element |
| U3 | Timed-activity card: what you are doing, when it ends, cancel (needs R3) | with R3 |
| U4 | Panels one by one: Here, Phone, Me, Society, Diary; touch targets 44 px or more, reachable with one thumb | per panel |
| U5 | Accessibility and polish: focus order, contrast in light and dark, reduced motion, text size | checks in `tests/` |

## Not decided
- Whether the dock stays at five tabs.
- Visual identity (colours, typography); today's are kept until the mock-up is approved.
