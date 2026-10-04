# Jev Arcade front page

```bash
.venv/bin/python -m playjev.arcade --open
```

Open `http://127.0.0.1:8765/`. It shows reviewed scores and evidence links, including
unranked live attempts. The same evidence/hash verifier serves the static scoreboard
and the front page. Games, challenge IDs and playback modes stay distinct.

## Local arcade records and token costs

The high-score cards show model handles such as `KEV-0.8B` with their supported HUD
score and input/output/total tokens. The expandable attempt table retains full
provider/model, playback mode, challenge and replay/HUD links. Records live in each
local run's `summary.json`, `hud-jev.json` and recordings; no run evidence enters Git.
The live token panel follows request logs, not only applied actions: stale/vetoed
replies and HUD inference count too. Startup, gameplay, completion and improvement
review have separate logs and phase totals; all count in the attempt total.
Missing/cancelled usage is unknown or a marked
`≥` lower bound, never a free zero. Legacy records remain explicitly incomplete.
This first cost scope excludes development, discovery and game-selection calls;
tokenizers differ and local tokens are not billed dollars or free machine resources.
Score alone does not establish a competition winner. Human controls/handles and
matching human-vs-model/model-vs-model challenges are open work, not enabled features.
For equal observed scores, the featured card prefers complete token accounting,
then the smaller recorded token total; this is not a cross-contract competition rank.

`events.jsonl` is the shared live-run stream: judgment requests/replies/failures,
native HUD observations and bounded action outcomes carry frame/request context and
code-owned classifications (move/pump/drop/shoot/abstain, accepted/rejected reasons).
No second model classifies already-known event types on the control path.
`inference.jsonl` and `decisions.jsonl` remain compatibility/evidence views; do not
sum all three and double-count their duplicate logical replies.

## Separate lifecycle recipes and improvement handoffs

`playjev/recipes/startup.json` asks only whether verified native input-effect probes
show a started, controllable game. Setup branches restore the same state and their
callbacks are disclosed; their moves/scores are not LLM gameplay. Unknown or failed
startup stops before action inference. A sprite, HUD or issued command is insufficient.
Crackpots legacy records without this proof are withheld from player high scores;
their observations, tokens and recordings remain local calibration evidence.

`playjev/recipes/completion.json` independently audits startup and supported score
increase after saving the run. Missing control proof, no score gain or an inconsistent
classification flags evaluation failure. A natural-end candidate is not verified loss,
and a passed progress audit is not a stage clear or completed game.

`loss_review.py` then runs a bounded improvement-only recipe and writes `improvement.md`
plus `loss-review.json`. It supplies measured native movement/noop proportions,
unused controls, the last moves and a recorded missed-intercept estimate. Most-of-game
stationarity is reported as a fact about sampled active intervals; equal control use
is not the objective. The template proposes at most two known-file changes. Small
rubric/value edits target `playjev/policies/crackpots.json`; lifecycle/perception/
execution refactors, source mismatches and uncertain judgments return to the parent.
No automatic patch, retraining or directory-scanning worker is enabled. Validate the
report against native frames before accepting it; alternative outcomes are hypotheses.
An explicit `python -m playjev.loss_review RUN --rereview` preserves earlier reports
and counts the extra review tokens. Startup/completion questions never join the action
request. Demo loops can seed role/motion calibration, never a player high score.

The read-only ASCII joystick animates sampled held inputs with a red fire button.
Proposals/rejection reasons are separate; the display cannot apply inputs and does
not establish that a sprite responded. The emulator view updates faster than the
front-page telemetry, which may miss brief button holds.

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
- `timing.py`: code owns the frame clock. Compact Dig Dug/Crackpots use an 18-frame cycle;
  other policies can ask a 6/18/30/60-frame cycle Choice. Neither restarts the game.
- `spatial.py`: source pixels → normalized fractions → rendered-content projection.
  Optional diagnostic Nouls check usable perception/mapping on noncompact policies.
  Compact policies omit them from per-action requests; they never replace pixel/arithmetic checks.
- `metrics.py`: measured calls/applied actions/vetoes/stale results/usage and inferred
  ASCII objects. Both the game-side panel and front page consume it.
- `progress.py`: evidence-bound endpoints and practice goal previews. It has no
  controller/reset/resume authority and does not alter leaderboard eligibility.
- `practice.py` / `checkpoints.py`: explicit bounded practice plans, independent HUD
  goal checks and canonical local checkpoint verification.
- `usage.py` / `events.py`: evidence-derived attempt tokens, model handles and one
  classified judgment/observation/action stream; neither grants controller authority.
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
