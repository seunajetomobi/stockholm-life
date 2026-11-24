# Interface v2: design notes

Built 2026-11-24 on the owner's request (the first mock-up was rejected as clumsy; this is the second design).

- **One navigation bar** at the top: time, date and weather, the place you are at, your six needs (energy, mood, food, hygiene, fun, social) as small rings with icons, and your money. On a phone the same bar is taller: time and money, the place, then the needs.
- **Goal line** under the bar (the old "Next up"), **places** as a vertical column of round buttons on the left edge, the **one action** near you at the bottom centre, a **dock** with five tabs.
- **Look:** Swedish blue (#006aa7) with a fine diamond pattern, white bold icons, Swedish yellow (#fecc02) for what is active or important, Jost for all type.
- **Icons:** [Lucide](https://lucide.dev), version 0.460.0, ISC licence (copyright Lucide Contributors and Cole Bemis, Feather, MIT). Embedded as an inline SVG sprite at the top of `index.html`; no network request. Needs: bolt, smile, fork and knife, water drops, confetti, speech bubble. Places: house, briefcase, people, speech bubbles, trending line, railway track. Dock: map pin, phone, person, landmark, notebook.
- **Fonts:** Jost, from Google Fonts (SIL Open Font Licence).
- Tests: `tests/test_ui_v2.py` (no two parts of the playing screen overlap at five screen sizes).
