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

## Progressive practice

The score page shows the last captured endpoint and stop cause.
`progress.json` binds the native player box/target count to `final.png` and a capture
frame interval. This is not necessarily the exact point of death: a browser stop can
occur after the last observation. Waves/world distance and terminal proof stay unknown.

Set **Increment X**, then **Preview best score + X goal**. For example, Crackpots'
supported 690 and X=100 preview a 790-point practice goal. The baseline is drawn only
from unchanged score evidence for the selected challenge. Unknown scores stay unknown,
and failed attempts do not automatically ratchet the goal upward. Preview requests
are logged locally, make no inference call and do not launch/resume or change budgets.
Choose **Practice metric**, **Segment cap (frames)** and **Start state**, then click
**Start next practice segment**. Score mode stops at two independent exact HUD
observations meeting the target, or the frame cap. Unknown baselines refuse score
practice. Frame mode extends a measured continuation/budget target by X; it is not
survival, cleared terrain, wave progress or completion evidence. A cap can prevent
reaching the goal; this is reported as not achieved, not silently treated as success.

Each click launches one segment, not an automatic batch. Fresh and resumed practice
have separate playback modes and are always unranked. Resumed cumulative scores do
not seed fresh-start score goals. Providers remain pinned for an active attempt.

Compatible stopped attempts save `checkpoint.state`, `checkpoint-ready.state`,
`checkpoint.png` and a hash-bound manifest. The checkpoint is taken after model inputs
are released/paused, then canonicalized with four disclosed setup callbacks; it can
be later than the last captured endpoint. Resuming verifies game/challenge/ROM/assets,
all checkpoint hashes and the exact restored canonical state before Start. Failed or
suspected-terminal sources cannot resume. Unknown terminal state is still unknown;
no resume is permission to reset. The resumed initial observation adds one disclosed
setup frame, separate from the segment budget. Checkpoint continuation counts include
normalization/setup frame-counter changes; do not confuse them with completed play.

See [Dig Dug discovery and classification](DIG-DUG.md) for the new experimental game.

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
- `progress.py`: evidence-bound endpoints and practice goal previews. It has no
  controller/reset/resume authority and does not alter leaderboard eligibility.
- `practice.py` / `checkpoints.py`: explicit bounded practice plans, independent HUD
  goal checks and canonical local checkpoint verification.
- `native.py`: one timeout-bounded native capture contract for live play, checkpoint
  images and paused diagnostics, eliminating duplicated screenshot-Promise handling.
- `discovery.py`: repeatable initial-load pixel probes and typed object-role hypotheses.
  Discovery does not train model weights or automatically activate a controller.

The initial observation uses the raw core screenshot, processed through
one recorded setup frame. Live browser contexts allow the viewport to resize rather
than fixing it to 640×520. Benchmark contexts retain their old fixed dimensions.
Overlay coordinates use WebGL's actual viewport inside the canvas, excluding internal
letterboxing; do not stretch native boxes across unused canvas margins.
Unsupported/missing renderer transforms suppress the overlay instead of guessing.

## Security and unfinished work

Loopback only. Mutations need matching Host/Origin and an ephemeral session token.
Game launch accepts catalog IDs, not arbitrary paths/commands. Only PNG/video/replay
artifacts inside `runs/` are served, not ROMs, `.env`, savestates or arbitrary files.
The hosted API key stays in Python. The page is not ready for public deployment.

Crackpots game-over detection, validated full-attempt ranking, Ollaya alternating
turns, Dig Dug scoring/terminal/discovered-controller calibration, other game adapters
and vision-model cookbook research remain pending.
See [the task list](ATARI-TASKS.md).
The planned [vision fallback and jev-router-inspired routing](VISION-ROUTING.md)
documents automatic/free-LLM model selection, which is not implemented yet. Manual
Ollaya/Jev selection is implemented. Fullscreen/touchscreen and actual compositor
tiling interactions remain pending. Prefer [local text/vision models](OLLAYA-MODELS.md);
hosted use requires a measured bottleneck and explicit approval.
See [testing instructions](TESTING-ATARI.md) for safe validation contracts.

## Jev-assisted check-in

For an authorized incremental source save point:

```bash
./scripts/check-in "Describe the source progress"
```

See [operating instructions and agent handoff](CHECK-IN.md). Invoking the script
authorizes its bounded source commit/push to `fork/atari-continuous-jev`; local Jev
reviews security/message wording without granting broader permissions. No merges.
Keep current limitations in docs and unresolved tasks in the open checklist;
Git maintains change history, not a parallel release/work log.
