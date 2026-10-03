# Crackpots: a new continuous Jev Atari adapter

Crackpots is not in PlayJev's existing HTML game roster. This experimental adapter
uses your own Atari 2600 ROM through EmulatorJS, with continuous rendering and
asynchronous hosted Jev lane/drop judgments. No ROM or API key is shipped.

## Play and watch

```bash
.venv/bin/python -m playjev.challenge create crackpots runs/crackpots-start --seconds 120
.venv/bin/python -m playjev.live runs/crackpots-start --out runs/crackpots-live-next
```

Click **Start Jev**. The `create --seconds` value describes the saved benchmark;
the continuous player has **no default duration**. **Stop & save** records the
attempt. Fullscreen and responsive overlays use the same UI as Space Invaders.
Gold boxes mark the gardener, yellow boxes mark inferred bugs, purple boxes mark
available pots, and dashed orange paths show measured short-term bug motion.
Perception uses raw framebuffer PNGs, never the overlay-composited browser image.

## What is different from Space Invaders

The [Activision manual](https://atariage.com/manual_html_page.php?SoftwareID=952)
describes twelve bugs per wave. Black bugs climb straight, blue bugs wiggle, red
bugs climb diagonally, and green bugs zig-zag. Six missed bugs cost a building
layer and move the roof down. Bonus bug markers contribute 200 points each.

`playjev/crackpots.py` observes the gold gardener, green pot foliage and climbing
sprite shapes. Solid black windows and red brick rectangles are excluded. Roof
position is derived from the gardener/pots, not fixed screen-bottom coordinates.
It associates bugs between frames and computes candidate pot/bug interceptions.
Initial speed estimates (0.7 gardener pixels/frame and 1.6 falling-pot pixels/frame)
are explicitly recorded; they remain estimates, not measured calibration values.

Hosted Jev independently selects a pot lane and whether an aligned interception
justifies releasing a pot. Code computes readiness and travel durations, rebases
movement against the newest gardener observation when the answer arrives, and
rejects stale or edge-blocked actions. Keeping a previously selected target is
conditional on that lane still having a predicted catch.

## Scoring and limitations

The initial three-configuration Tesseract/Jev experiment misread 0 as 11 and 690
as 630 or 90. It was not ranked. `playjev/crackpots_score.py` now has a separate
six-column/eight-row Activision font, calibrated against the visible raw recording.
The shared HUD workflow sends distinct glyph grids and literal mismatch counts to
hosted Jev in one batched request per recording. Code requires exact pixel/template
agreement and repeated score evidence before recording an automated reviewed score.
Blank or damaged glyphs are not fabricated numbers. Six score positions are supported.
The old OCR helper is retained as an experimental fallback, not the default pipeline.

`hud-jev.json` saves glyphs, Jev choices/probabilities/usage and screenshot hashes.
This is **Jev-pipeline review**, not a human-confirmed competition score. Continuous
smoke tests remain unranked and distinct from fixed-budget benchmark results.

The first two 40-second development runs scored zero. After fixing window detection,
rebasing late movement, and explicitly exposing aligned drop opportunities, v3
reached a visible **690** and blue bugs. Its replay is
`runs/crackpots-continuous-v3/replay.html`. It is not a claim of game completion.
The exact-glyph Jev workflow subsequently recovered **690** with **231/231** saved
HUD frames accepted, using one request with ten distinct nonblank glyphs. Empty
leading positions are literal all-dark pixels, resolved in code rather than sent
to Jev. The earlier two runs were recovered as zero, not the false OCR "11".

A separate 20-frame movement probe measured approximately **0.925 pixels/frame**
(33.5 → 52.0 in normalized screenshots). The played v3 policy used its recorded
0.7 estimate; future calibration should use raw frames and multiple measured
segments before silently replacing those settings. This probe is not a scored run.

Game-over detection is **not validated** for Crackpots. It does not reuse the
Space Invaders background-color rule. Use Stop & save; do not treat a timed smoke
test as completion, survival or an independently verified single-life result.
There is no automatic reset or savestate lookahead. HTML-roster integration is
also still pending; this mode presently uses the Python launcher.
