# Dig Dug: initial-load discovery and classification

The adapter is **experimental**, not a completed high-score challenge. Use your
local `Dig Dug (NA).a26`; no ROM/state/image/video is distributed in Git.

## Create the challenge

```bash
.venv/bin/python -m playjev.challenge create dig-dug runs/dig-dug-tunnel-v1 --seconds 60
```

Creation resets for nine frames, then explicitly allows 510 released-input intro
frames before saving the challenge. This ROM walks the miner from the surface into
the maze before normal control. `start_script` records those setup inputs. Reset is
not a controller action. Score is at bottom right; extra-life blocks are at bottom
left. The [manual](https://www.digitpress.com/library/manuals/atari2600/dig_dug.txt)
documents four-direction digging and holding/repeatedly pressing fire to pump.
It also says fire can restart after game over, so the experimental controller
suppresses fire without current active-play/player evidence.

## Repeatable initial-load workflow

```bash
.venv/bin/python -m playjev.discovery probe runs/dig-dug-tunnel-v1 \
  --out runs/my-dig-dug-discovery --visible
.venv/bin/python -m playjev.discovery classify runs/my-dig-dug-discovery --provider ollaya
```

1. **Measure:** two repeats of noop/left/right/up/down/pump, each explicitly restored
   to the same canonical challenge. Each probe has 30 input frames plus two disclosed
   capture callbacks. Save native starting/ending PNGs, hashes and pixel changes.
2. **Discover candidates:** compact same-palette components, merged only within
   sprite-scale bounds. Retain starting boxes, sprite masks and observed displacement
   relative to noop. Match ambiguity/animation can invalidate identity estimates.
3. **Classify:** typed Choice over player/enemy/rock/terrain/HUD/unknown. Code records
   exact requests, answers/probabilities and abstention decisions. A 0.6 minimum
   confidence is an experimental hold threshold, not proof of correctness.
4. **Verify before use:** require repeat hashes and unchanged PNGs; a prospective
   profile is bound to discovery/challenge/ROM/assets. A player hypothesis needs
   measured directional responses and agreement with the native bootstrap detector.
   Confidence alone cannot enable it. Runtime profile consumption is still pending
   because the actual local classification did not pass.

This is **discovery and classification**, not model-weight training. It does not
upload raw images to Jev, magically identify every object or certify game rules.
Python measures pixels; Jev/Ollaya receives bounded structured evidence. Large
terrain, unseen monsters, ghosts, rocks, fire and occlusion remain coverage gaps.

## Current limitations

Native palette/component estimates are bootstrap observations, not verified sprite
roles. Local role/action calibration is insufficient to activate a discovered
controller. The live action path uses one compact action Choice; clocks and geometry
checks remain in code rather than adding model questions. Low latency alone does
not establish accurate judgments; allocation
failures and stale replies must still stop/release safely.

Paused deterministic input calibration is separate from continuous Jev gameplay.
Effective pumping and rock/ghost coverage remain uncalibrated. The partial native
HUD font recognizes labeled digits 0–3; unreadable/unseen glyphs stay unknown.
Matching independent captures support observed scores, not a final/true peak score.
Three captures without the known playfield stop safely without claiming game over;
extra-life blocks are not a prerequisite for controlling the last life. No
verified Dig Dug stage-clear or completed-game claim is available.

Keep recordings, snapshots, exact requests and failures locally under `runs/`.
Use [the open task list](ATARI-TASKS.md) as the single source of remaining work;
do not duplicate completed-run summaries here.

## Safety fallback

Allocation limits, timeouts, unsupported question types and invalid inference
responses produce a structured **release-inputs / stop / save** report. Failed
attempts remain incomplete/unranked, with native endpoints and recordings retained.
Unusable classification instead remains observation-only and does not activate a
controller. These paths do not silently substitute hosted inference.

To retry classification with hosted Jev, explicitly choose `--provider jev` on a
new discovery directory; this consumes quota. The score page's provider selector
controls the next gameplay attempt. It never changes a running attempt's provider.

## What qualifies as playable and reusable

1. **Reliable controls:** independently verified roles and fresh-frame gates produce
   observable, timely movement in continuous play. Logs bind proposals, execution,
   expiry and released inputs; manual/deterministic calibration is labeled separately.
2. **Calibrated pumping:** recordings connect facing, alignment, distance and bounded
   fire timing to inflation and enemy defeat, with independently supported score
   changes. Wrong-facing/out-of-range/respawn cases must not pump or restart blindly.
3. **Supported score/terminal evidence:** independent native observations support HUD
   scores and distinguish respawn/round transition from game over. Fire cannot restart
   after a terminal outcome; ambiguous observations remain unknown.
4. **Repeatable runs:** at least three equivalent fresh-start attempts retain failures
   and support repeated movement and enemy defeat/progression. A reusable procedure
   states evidence requirements, typed questions, code gates, bounded actions and
   failure/outcome checks, and is replayed on Dig Dug before reuse in the next game.

This is an acceptance bar, not a claim that these milestones have been reached.
Fresh/resumed practice, calibration, capped smoke runs and ranked evaluation remain
separate. A frame target is a budget, not survival, an enemy defeat or game completion.
