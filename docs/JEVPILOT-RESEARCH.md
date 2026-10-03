# JevPilot: source review and Atari adaptation

Reviewed upstream commit `e1beeb13b9a928fb76f167f86af584f4ce9cf180` at
https://github.com/standardagents/jevpilot . This is a source review, not a claim
that its hosted demo was exercised end to end in this session.

## What actually makes the driving demo work

- `src/main.js:944–1027`: `requestAnimationFrame(animate)` advances simulation and
  renders continuously. `setInterval(decide,25)` checks whether a decision is due;
  it does **not** make an API request every 25 ms. Manual controls work independently.
- `src/background-planner.js`: a Worker receives player, traffic, pedestrians,
  perception and route snapshots. Physics/rendering never await the worker.
- `src/traffic-safety.js:201–346`: `otherPose` and `createObstaclePrediction` predict
  moving obstacles. `predictTrafficConflict` rolls out the ego vehicle at 0.1-second
  intervals over 3–5 seconds, with footprint/motion buffers and braking behavior.
- `src/driving-plan.js`: samples candidate maneuvers using local physics and swept
  collision checks. It attaches collision object/time, lane error, progress and
  road clearance. This is calculation over known game objects, not image detection.
- `src/jev-request.js`: compacts that evidence without model-memory dependencies;
  Jev selects motion, a candidate vector and sometimes route. Single eligible
  alternatives are handled explicitly in code. Decisions are due at 250 ms near
  hazards/turns or 650 ms otherwise.
- `src/main.js:648–764`: only one decision request is pending. Generation/context
  checks reject changed worlds/lights. Answers older than 1,800 ms expire.
  `src/main.js:963` also stops the target speed when decisions go stale.
- `src/road-vectors.js`: renders candidate path ribbons and collision colors,
  including the selected plan. These overlays visualize predictions; they do not
  feed modified pixels back into the model.

## What transfers to Atari—and what does not

Continuous rendering, asynchronous decisions, freshness checks, geometric path
prediction and overlays transfer. Direct object state and the car physics model
do not: the ROM supplies a raster, not JavaScript vehicle objects. Atari tracking
therefore uses screenshot colors, boxes, frame differences and estimated velocities.
No ROM RAM inspection, savestate lookahead or fabricated offscreen state is used.

`playjev/live.py` is a separate continuous Space Invaders prototype. It restores once,
waits for **Start Jev**, plays normally, tracks sprites and lasers, draws boxes and
30-frame laser projections, and allows **Stop & save**. One hosted request can be
pending while emulation continues. Answers older than 60 frames are rejected;
collision/edge checks use the latest observed geometry before applying controls.
Controls expire locally. Predictions and vetoes remain logged. Observation PNGs
come from EmulatorJS's read-only framebuffer screenshot API, not the composited
browser page; display overlays cannot become fake enemies or HUD digits.

```bash
.venv/bin/python -m playjev.live runs/first-wave-120s --out runs/live-invaders-next
```

No default duration, test-count loop, automatic reset or terminal padding. An optional
`--seconds` plus `--autostart` exists only for explicit smoke tests. Closing the
browser is not the save workflow; use **Stop & save**. Game-over color changes are
still candidates, not validated terminal events. Live scores are not ranked as
equivalent to paused fixed-budget benchmarks.

## High-score extraction without a vision LLM

`playjev/hud.py` uses Pillow to isolate player-one green HUD pixels. It samples
native pixels with per-digit vertical alignment and produces tiny 3×5 text glyphs. Code provides literal
template mismatch counts; hosted Jev makes digit/blank/unknown Choice judgments.
Distinct glyphs across the entire recording are batched into **one API request**,
not one request per saved screenshot. The same judgment is reused for repeated
glyphs. Code checks exact template agreement and requires repeated score evidence.

```bash
.venv/bin/python -m playjev.hud runs/first-wave-laser-gates-v3
.venv/bin/python -m playjev.challenge leaderboard
```

`hud-jev.json` retains pixels-as-text, request, response, usage, accepted/rejected
readings and screenshot hashes. Unknown glyphs remain rejected; temporarily blank
HUDs are not fabricated zeros. Missing visible-digit coverage
must not overwrite an existing reviewed score. This extractor is ROM/layout-specific,
not a universal OCR claim. Template coverage and temporal scoring need further tests.

The current TypeSafe API (`https://docs.typesafe.ai/api.md`) accepts string/object/
array state, not an image field. Jev can judge image-derived evidence in an application;
Pillow captures/transforms the raster here. No extra vision model is needed for this
fixed HUD. A vision fallback would be an explicit, separately measured stage, not
an undocumented assumption about Jev. Usage is recorded; dollar costs are not claimed
without the applicable pricing and measured billing data.
