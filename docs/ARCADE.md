# Jev Arcade front page

```bash
.venv/bin/python -m playjev.arcade --open
```

Open `http://127.0.0.1:8765/`. It shows reviewed scores and evidence links, including
unranked live attempts. The same evidence/hash verifier serves the static scoreboard
and the front page. Games, challenge IDs and playback modes stay distinct.

Loading the page makes no inference call. Choose **Ollaya CLI · local** (default) or
**Jev · hosted** with the score-page selector, then explicitly request a recommendation.
The selected model classifies readiness from intent, adapters and active session.
Switching makes no inference call and applies to the next recommendation/attempt;
active attempts retain their provider/model for auditable score attribution.
It does not launch without the visitor's
Start click. The game opens in a separate visible browser window, with continuous
emulation. Front-page **Stop & save** ends it cooperatively and finalizes video/HUD
review; the game window also has its own controls. No default test duration or batch
loop is introduced. The HTTP server permits one owned attempt at a time, not a
machine-wide lock against separately launched command-line sessions.

## Reuse boundaries

- `runtime.py`: registration of observation, tracking, overlays, latest-state control
  preparation, terminal candidate, policy and score collector. New games do not add
  branching to `live.py`.
- `scoreboard.py`: shared score-support and ranking checks. A reviewed HUD can be
  shown without being eligible for a fixed-budget ranking.
- `transports.py`: Ollaya CLI and cancellable hosted Jev adapters. The same policies
  use either; no hidden hosted fallback. Failed local inference is visible.
- `execution.py` / `live-controls.js`: capture frame intervals, conservative
  deadlines, execution-time freshness checks, frame-based input expiry and release.
- `timing.py`: a frame clock measured in code. The selected model chooses 6/18/30/60 frames
  before the next decision cycle. This restarts a decision cycle, **not the game**.
- `spatial.py`: source pixels → normalized fractions → rendered-content projection.
  Two diagnostic Nouls check usable perception and consistent mapping. They share
  the gameplay/timing request and are not substitutes for pixel or arithmetic tests.
- `metrics.py`: measured calls/applied actions/vetoes/stale results/usage and inferred
  ASCII objects. Both the game-side panel and front page consume it.

The initial observation now also uses the raw core screenshot, processed through
one recorded setup frame. Live browser contexts allow the viewport to resize rather
than fixing it to 640×520. Benchmark contexts retain their old fixed dimensions.
Overlay coordinates use WebGL's actual viewport inside the canvas, excluding internal
letterboxing. In the 640×480 reproduction, the game occupied a 503-pixel viewport
starting at canvas x=69; stretching boxes across all 640 pixels caused the mismatch.
Unsupported/missing renderer transforms suppress the overlay instead of guessing.

## Recorded checks for this iteration

- 47 offline regression tests passed, including exact HUD lookup, duplicate-final
  exclusion and independent/overlapping capture-interval scoring checks.
- Eight paused restored-frame rendered-pixel checks at four sizes and 1×/2× DPR:
  maximum gardener-box error 0.85 CSS pixels. This does not certify all live sprites.
- Score-page provider toggles/layouts verified with no inference on load or switch;
  early-stop integration preserved an Ollaya attempt when the page selected Jev.
- Front page: reviewed 690/1,640 scores visible; real hosted Jev recommended Crackpots.
- Layout checks: 390×844, 768×1024, 1440×900 and 3440×1440.
- At 390×844, 1440×900 and 3440×1440 the restored core PNG was identically 160×210
  with SHA256 `a130530e7c4db34f23f9aa696204e73b2657e5e25d7baff7e0f53a6b3ae9b8cf`
  and player box `[30,24,36,40]`. These are source-geometry checks, not proof of
  touchscreen or overlay-image alignment on every device.
- `runs/arcade-spatial-clock-smoke-v1`: 487 game frames, 13 hosted calls, 13 applied
  decisions, no observed stale/vetoed decisions; score 10 recovered from 47/47 frames.
  The recorded request has lane, drop, cycle, perception and projection questions.
  This short smoke test does not establish improved high-score performance.
- Front-page launch/stop integration saved the video, stopped by user request and
  made no game-completion claim. An immediate-stop directory-creation race was found
  and fixed: stop markers now live outside the child-created run directory.

Raw browser/resize evidence and navigation requests are local under
`runs/arcade-processes/`; generated artifacts are ignored by Git.

## Security and unfinished work

Loopback only. Mutations need matching Host/Origin and an ephemeral session token.
Game launch accepts catalog IDs, not arbitrary paths/commands. Only PNG/video/replay
artifacts inside `runs/` are served, not ROMs, `.env`, savestates or arbitrary files.
The hosted API key stays in Python. The page is not ready for public deployment.

Crackpots game-over detection, validated full-attempt ranking, Ollaya alternating
turns, the next game adapters and vision-model cookbook research remain pending.
See [the task list](ATARI-TASKS.md).
The planned [vision fallback and jev-router-inspired routing](VISION-ROUTING.md)
documents automatic/free-LLM model selection, which is not implemented yet. Manual
Ollaya/Jev selection is implemented. Fullscreen/touchscreen and actual compositor
tiling interactions remain pending; rendered quarter-size projection is now tested.
See [local testing findings](TESTING-ATARI.md) for Kev latency/allocation limitations.

## Jev-assisted check-in

Stage only the intended source/docs/tests, then:

```bash
.venv/bin/python -m playjev.review_checkin --authorized --provider ollaya
```

Use `--authorized` only when the user has actually requested the push. The helper
runs tests and staged whitespace/artifact/credential checks, gathers branch/remote
and browser/smoke evidence, and submits a bounded release-readiness judgment through
the selected provider (local CLI by default). `--provider jev` is an explicit hosted
switch, not an automatic fallback. Local allocation failure records a hold result.
It saves exact request/response to `runs/arcade-processes/checkin-review.json`.
It does **not** run commit or push. Deterministic checks and user authorization
cannot be overruled by a model's confidence. This reviews the packet, not every
line of source code, and is not a correctness certificate or universal best practice.

After a supported review, run explicit Git commands, verify the remote SHA, and
record those actual results in the release evidence. Do not claim the model itself
operated Git. Keep incomplete features disclosed in the commit and task list.
