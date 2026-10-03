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

## Current measured result

- Two six-probe traces were repeatable; 16 candidate objects retained.
- Miner candidate starts at `[76,87,82,97]`, palette `[189,146,255]`.
- In these 30-frame samples its joystick response reached 4 horizontal/8 vertical
  pixels. Peach Pooka/green Fygar are separate bootstrap palette estimates.
- Kev labelled every candidate enemy at low confidence (~0.15–0.18), including the
  joystick-responsive miner. The larger strategy context also exhausted GPU memory.
  These are recorded failures, not accepted labels. Safety now retains unknown roles
  and an **observation-only** result; no controller profile is activated.
- A 600-frame continuous local continuation rejected both completed decisions as
  stale (258/215 frames old), applied zero actions and preserved its recording.
- Four-direction/pump input traces replayed identically from a checkpoint across
  seven paired image/state checks. That is control/restore calibration, not successful
  LLM gameplay or proof of effective pumping.
- The bottom-right glyph decoder and terminal signal are uncalibrated. Scores stay
  unknown, never zero by default. There is no supported Dig Dug high score yet.

Local evidence: `runs/arcade-processes/dig-dug-discovery-v1/`,
`runs/arcade-processes/dig-dug-resume-check-v2/`, and `runs/dig-dug-local-trial-v1/`.
See [research prompts](REFACTOR-PROMPTS.md) and [ordered tasks](ATARI-TASKS.md).

## Safety fallback

Allocation limits, timeouts, unsupported question types and invalid inference
responses produce a structured **release-inputs / stop / save** report. Failed
attempts remain incomplete/unranked, with native endpoints and recordings retained.
Unusable classification instead remains observation-only and does not activate a
controller. These paths do not silently substitute hosted inference.

To retry classification with hosted Jev, explicitly choose `--provider jev` on a
new discovery directory; this consumes quota. The score page's provider selector
controls the next gameplay attempt. It never changes a running attempt's provider.

## Next acceptance criteria

- Calibrate player/enemy/rock/ghost/HUD roles against labeled native recordings.
- Simplify and test typed questions/local model capability, then independently verify
  any accepted discovered profile and implement fresh-frame bounded profile execution.
- Calibrate pump range/facing and glyphs; verify terminal handling prevents fire restart.
- Run repeated fresh-start attempts with supported HUD scores. Resume practice stays
  unranked and separate; no high-score/completion claim before that evidence exists.
