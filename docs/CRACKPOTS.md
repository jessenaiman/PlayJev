# Crackpots: a new continuous Jev Atari adapter

Crackpots is not in PlayJev's existing HTML game roster. This experimental adapter
uses your own Atari 2600 ROM through EmulatorJS, with continuous rendering and
asynchronous typed lane/drop judgments through Ollaya CLI by default. No ROM or API key is shipped.

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

The selected local model independently selects a pot lane and whether an aligned interception
justifies releasing a pot. Code computes readiness and travel durations, rebases
movement against the newest gardener observation when the answer arrives, and
rejects stale or edge-blocked actions. Keeping a previously selected target is
conditional on that lane still having a predicted catch.

## Scoring and limitations

`playjev/crackpots_score.py` supplies a six-column/eight-row Activision font.
The shared HUD workflow uses exact template/repetition checks by default, without
inference. Optional typed glyph judgments use the explicitly selected provider;
they cannot override exact pixel/template agreement and repeated score evidence.
Blank or damaged glyphs are not fabricated numbers. Six score positions are supported.
The old OCR helper is retained as an experimental fallback, not the default pipeline.

`hud-jev.json` saves glyphs, Jev choices/probabilities/usage and screenshot hashes.
This is **Jev-pipeline review**, not a human-confirmed competition score. Continuous
smoke tests remain unranked and distinct from fixed-budget benchmark results.

Empty leading positions are literal all-dark pixels, resolved in code. OCR is
untrusted; do not substitute its guesses for exact glyph evidence. Calibrate motion
on multiple native-frame segments before changing recorded speed settings; a paused
movement probe is not a scored gameplay run. Read reviewed scores from the generated
[evidence-linked board](ATARI-RESULTS.md), not a manually maintained trial history.

Game-over detection is **not validated** for Crackpots. It does not reuse the
Space Invaders background-color rule. Use Stop & save; do not treat a timed smoke
test as completion, survival or an independently verified single-life result.
There is no automatic reset or savestate lookahead. HTML-roster integration is
also still pending; this mode presently uses the Python launcher.
