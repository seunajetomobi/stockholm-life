# Graphics: image effects (GFX-1, first slice)

Status: in progress on branch `feat/gfx-lighting` (approved by the owner 2026-11-24). Not merged, not deployed.

## What the first slice does
- **High preset only.** When the player uses High (`sl-quality` = `high`) and the browser has WebGL 2, the city is
  drawn through three.js r128's `EffectComposer`: the scene, then a bloom (`UnrealBloomPass`), then SMAA
  anti-aliasing (`SMAAPass`). Low, and every phone that starts on Low, draws exactly as before and downloads nothing.
- **Bloom only at night.** Its strength follows the game's night factor from `lightAt()` (0 by day, 0.55 at full
  night), so lamps, lit windows and signs glow after dark and the bright daytime sky does not.
- **Loaded on demand** from the same jsDelivr version as the other three.js add-ons (`three@0.128.0/examples/js/`,
  MIT licence), about 90 KB. If any file fails, the game logs one console warning and keeps the plain look.
- **Off switch:** localStorage `sl-gfx` = `0`. The Settings screen (quality slider) is separate and does not control it yet; a toggle is a later slice.
- **Only the outdoor city.** Interiors, the train ride and the arrival cutscene render as before.

## Checked facts behind the design
- r128 applies tone mapping in each material's shader whatever the render target
  (`src/renderers/webgl/WebGLPrograms.js`, `toneMapping: material.toneMapped ? renderer.toneMapping : NoToneMapping`),
  so rendering into the composer keeps today's ACES colours. Checked 2026-11-24.
- The renderer asks for `antialias:true`, which does not apply inside the composer's render targets; SMAA replaces it there.
- The game already has its own sky shader (sun, dusk, stars), so r128's `Sky.js` is not used.

## Open decision (not in this slice)
`fixMaterials()` converts the models' physically based materials to Lambert on purpose (cost on integrated GPUs).
Environment lighting (an HDRI through `PMREMGenerator`) only changes physically based materials, so it needs that
decision revisited for High. To be measured and reviewed before it is built.

## Tests
`tests/test_gfx.py`: High builds the effects and the glow follows the night; Low loads nothing; `sl-gfx` = `0` turns
them off; a failed download keeps the game drawing. Other tests run with the effects off (`tests/game.py`,
`new_page(gfx=False)`), because they cost much time in the test browser's software renderer and change no layout.
