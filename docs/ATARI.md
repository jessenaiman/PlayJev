# Atari typed-controller adapters

EmulatorJS runs the ROM in Chromium. Controllers receive image-derived **text geometry**,
not privileged RAM. Development now defaults to **Ollaya CLI**; the arcade score page
has an explicit hosted Jev provider switch. See [testing](TESTING-ATARI.md) and
[the front page](ARCADE.md). This adapts PlayJev's observe/choose/execute loop; it is not its trained
pixel policy, and comparable game performance has not been established.

Games: **Space Invaders**, **Freeway**, **Defender**, **Crackpots**, and experimental
**[Dig Dug](DIG-DUG.md)** (player one). Use your own ROMs. Dig Dug score/terminal
calibration and usable discovered-profile control are still pending.

### Important: `playjev.challenge` is the paused-inference benchmark

That runner is **not continuous real-time play**. It resumes and pauses the
core in short observation intervals, then waits for model inference. Its `complete`
status means the frame budget was consumed, **not** that the game was completed.
First-wave evidence is a separate result; elapsed time never proves a stage clear.
New runs stop at a suspected game-over signal rather than padding the remaining
budget with no-input frames. That visual signal still requires review and terminated
runs are not automatically ranked. Historical recordings and scores remain unchanged.

### Continuous Space Invaders and Jev score recording

The separate continuous prototype fixes that playback model:

```bash
.venv/bin/python -m playjev.live runs/first-wave-120s --out runs/live-next
```

Click **Start Jev**, watch moving sprite boxes and predicted laser trajectories,
then **Stop & save**. There is no default test duration or automatic restart.
**Fullscreen** changes display size only; perception reads the native framebuffer.
Overlays track the actual WebGL game viewport inside canvas bounds on resize/fullscreen and scale their backing store for
high-DPI displays. Browser layout checks passed at 390×844, 1920×1080, 768×1024
(2× DPR), and 3440×1440. These layout checks are not a mobile touchscreen gameplay test.

After stopping, the default scorer resolves exact-known HUD glyphs without inference
and saves observations/provenance to `hud-jev.json`. Optional `playjev.hud RUN --typed`
uses the recorded provider for typed checks. Pixel/template and temporal
checks reject unsupported numbers. The prior **1,640** Space Invaders result was
recovered by this pipeline; the continuous 20-second smoke test recorded **215**.
Different playback modes remain separate on the board. See
[the source review](JEVPILOT-RESEARCH.md) for the control-loop design and limitations.

The continuous prototype is not yet integrated into the upstream browser roster;
it currently needs the Python launcher, locally staged EmulatorJS assets and your ROM.
The existing parent `.env` supplies `TYPESAFE_API_KEY`; the key stays in Python,
never browser JavaScript, logs, videos or metadata.

## Setup

From `PlayJev/`:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-atari.txt
.venv/bin/playwright install chromium
```

Use matching EmulatorJS **4.2.3** JavaScript and bundled Atari assets. The current
setup is in sibling `EmulatorJS/node_modules/@emulatorjs/emulatorjs/data`;
the development branch uses a different save-state API. Set `create --assets PATH`
for another installation. ROM defaults are under
`~/Games/roms/Atari 2600 Champion Collection/`; override with `create --rom FILE`.

## Watch live, slower

```bash
.venv/bin/python -m playjev.challenge create space-invaders challenges/invaders-10s --seconds 10
.venv/bin/python -m playjev.challenge run challenges/invaders-10s --visible --speed 0.25 --action-frames 30
```

The browser shows live action, confidence and **game time**. Default speed is ¼ speed;
`--speed 0.1` is slower. `--watch-delay 1` holds the selected action label for another
second before execution. The emulator is paused throughout inference/watch delays.
Action durations are in **emulator frames**, unaffected by inference latency or speed.
At 60 Hz, 30 frames is half a second. The last action is clipped to the challenge budget.

10 game seconds with 30-frame actions makes 20 API calls. With 6-frame actions it
makes 100. Challenge creation and fixed/random baselines make **no API calls**.
Long challenges can cost many calls; do not mistake wall time for game time.
Ctrl+C stops and marks the run incomplete; it cannot be ranked.

## Second game: Freeway

```bash
.venv/bin/python -m playjev.challenge create freeway challenges/freeway-10s --seconds 10
.venv/bin/python -m playjev.challenge run challenges/freeway-10s --visible --speed 0.25 --action-frames 30
```

Freeway choices are `up`, `down`, `noop`. Its observation filters out the gray road
and white lane markings to retain colored cars/chickens. Space Invaders supports
`left`, `right`, `fire`, `left+fire`, `right+fire`, `noop`.
Sprite roles are hints, not verified game state. This is an experimental policy.
The runner has a fixed budget but must stop at a terminal candidate rather than
padding known game-over frames. It does not restart automatically. Reliable Freeway
terminal detection has not yet been established.

## Rewatch runs

Each new run gets its own folder printed in the terminal. Open **`replay.html`**
from that folder in a browser. It works offline and makes no new API calls.

- `replay.webm`: recorded live viewport, including slow play, pauses and status.
- `replay.html`: video controls, ¼/½/normal/double speed, previous/next decision.
- `decisions.jsonl`: exact text state/question, Jev response/probabilities,
  confidence, inference latency, requested/actual frames, wall/video timestamps.
- `start.png`, `final.png`, `frame-*.png`: visual evidence.
- `summary.json`: challenge ID, experiment settings, completeness, high-score review.

Video timestamps are wall-clock offsets from browser-page recording startup;
minor encoder/startup offsets may occur. Frame counts in logs are authoritative.

## Defender: test the shared runner with a scrolling shooter

```bash
.venv/bin/python -m playjev.challenge create defender challenges/defender-30s --seconds 30
.venv/bin/python -m playjev.challenge run challenges/defender-30s --player jev-gates --visible --speed 0.5 --action-frames 30
```

Defender reuses the same saved-state validation, frame budgets, recording, experiment
and scoring code. Its adapter observes colored sprites and the scanner, and its
policy combines an eight-direction movement judgment with an independent fire gate.
It does not claim Space Invaders' ROM-specific laser detector works unchanged here.

Defender uses normal joystick mechanics for smart bombs (fire below the city) and
hyperspace (fire above the playfield), not cheats. Pressing fire after game over can
restart the game, so the runner observes the background-color cycle every six frames
and stops the run at that candidate. Older v2 recordings instead released controls
for the rest of the fixed budget, logged as `terminal_hold`; those frames were not
active gameplay. The detector is an
experimental ROM-specific visual signal; the replay must confirm the terminal event.

The visible 30-second run `runs/defender-jev-gates-v2` scored **1,750**, reviewed by
the assistant from `frame-0053.png`. It finished the 1,800-frame budget without a
restart. The earlier v1 test is explicitly invalid because it accidentally restarted.

## High-score board

```bash
.venv/bin/python -m playjev.challenge leaderboard
```

Open `runs/scoreboard/index.html`. `scores.json` accompanies the HTML for other
tools. Scores are ranked **only within one game AND challenge ID**. Different ROMs,
starting states or duration budgets stay separate. Each entry links to its replay
and selected score screenshot. Evidence hashes are rechecked when building the board;
incomplete, invalid, unreviewed or changed-evidence runs stay unranked.

The initial reviewed scores are **Space Invaders 1,640 / 120 game seconds**, with
the first-wave clear, and **Defender 1,750 / 30 game seconds**. These are not comparable
against each other. Reviewer identity is shown: assistant visual review is not a
human sign-off. Use `score --reviewer human` after your own review, or
`--reviewer assistant` for assistant-reviewed evidence.

## Unified score challenges

Challenge identity pins **game, ROM bytes, library/core asset bytes, saved state,
starting image, frame budget, 60 Hz convention and scoring rule**. The exact
saved state is loaded for every run. Three neutral render frames after restoration
are common setup, excluded from the gameplay budget. Because loadState queues a
core command, restoration advances one callback at a time until the canonical
serialized emulator state matches exactly (or rejects the run). Screenshots are evidence, not state identity: Atari's
multiplexed sprites/renderer can make a single screenshot differ despite equal state.
Frame overshoot, changed assets or mismatched starts reject a run, not silently
weaken comparability. Fast/¼-speed fixed-policy runs were tested to produce identical
post-action images. Scores are compared only within an identical challenge ID—never
Space Invaders points against Freeway crossings.

**The metric is player-one high score during the run. Scoring is visually reviewed
for now.** Tesseract, if available, supplies untrusted per-decision OCR candidates
and their maximum. An unreadable HUD is `null`, not zero. Review the replay and
saved frames and enter the **highest observed player-one HUD score**, not a guess.
Use `--frame` to select its screenshot (default `final.png`):

```bash
.venv/bin/python -m playjev.challenge score runs/my-run 120 --frame frame-0019.png --note "Verified highest player-one HUD score while watching replay"
.venv/bin/python -m playjev.challenge compare runs/my-run runs/another-run
```

Only completed runs with the entire frame budget and confirmed scores are ranked.
The score review includes reviewer identity and the selected screenshot hash. This is a local evidence-based
leaderboard, not a tamper-proof competition. Keep it visually reviewed until automatic
HUD/RAM score adapters are independently validated for each ROM.

No cheats, RAM writes, savestate lookahead or extra-life modifications are used.
Restoring the challenge state is only allowed **before** the run begins. Reset is
only used during challenge creation. During a scored run the runner executes only
the selected controller buttons. `fixed`/`random` are explicitly labeled baselines,
never presented as Jev. Future player plugins are trusted code, not sandboxed; review
their implementation before accepting their scores.

## Experiments

The `jev-gates` Space Invaders player combines threat, dodge, firing-lane and fire
questions with read-only six-frame laser tracking, collision-vetoed paths and timed
alignment. It uses 12-frame decisions near low projectiles, otherwise the chosen
action budget. The [first-wave checkpoint](ATARI-CHECKPOINT.md) documents a visible
successful run and its exact source hashes.

Space Invaders also supports `--player jev-composed`: one API call asks separate
movement (`left/right/stay`) and trigger (`fire/release`) questions. Code combines
the answers into ordinary controller buttons. Both judgments and their confidence
are shown live and logged; displayed aggregate confidence is the minimum component,
not a probability of success. This variant is an experiment, not a proven improvement.
Run it on the same challenge as `jev` to compare high scores fairly:

```bash
.venv/bin/python -m playjev.challenge run challenges/invaders-10s --player jev-composed --visible --speed 0.25 --action-frames 30
```

```bash
.venv/bin/python -m playjev.challenge experiment challenges/invaders-10s experiments/atari-example.json --out runs/invaders-experiment --visible
```

The JSON list varies `player` (`jev`, `jev-gates`, `jev-composed`, `fixed`, `random`), `observation` (`regions`,
`compact`, `single`), `action_frames`, `model`, `seed`, and `question` (a text-file
path relative to the experiment JSON). The example makes 120 API calls for a 10s
challenge. All variants use the same initial state and frame budget. Confirm their
scores, then `compare` their folders. Different action durations intentionally
change policy opportunity/call budgets; recorded settings make that tradeoff visible.

## Add more players/games

In `playjev/challenge.py`:

- Subclass `Player`, implementing async `decide(state, game)` returning
  `choice`, `confidence` and optional evidence. Supply the instance to `run(args, player)`.
  Do not advance the emulator inside a policy.
- Subclass `GameAdapter`, define ROM, goal, actions, observation and HUD crop,
  then register it in `GAMES`. State creation, validation, recording, slow watching,
  budgets, experiment orchestration and comparison remain shared.

Use the same challenge files for future players (including a future Ollaya player).
No Ollaya/local model is installed or used by this implementation.
