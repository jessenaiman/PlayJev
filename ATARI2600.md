# Atari 2600 arcade runbook
Run commands from `PlayJev/`; use new output names, never overwrite evidence.
## Status and rules
- EmulatorJS + local ROMs; continuous gameplay is separate from paused benchmarks.
- Default: Ollaya CLI (`kev:0.8b`). Never call its HTTP API or silently use hosted Jev.
- Hosted Jev requires explicit selection; running attempts keep their original provider.
- Evaluate local Ollaya text/vision first; hosted escalation requires a measured bottleneck and approval.
- Dig Dug uses one compact action judgment; HUD digits 0–3 are supported, others remain unknown.
- No verified Dig Dug stage clear, completed game, or working discovered-controller procedure yet.
- Fresh/resumed practice is unranked. Frame targets measure budget, not survival or digging progress.
- Failures release inputs and stop/save; unusable classifications cannot activate controllers.
- No delegation this iteration. Keep ROMs, credentials, states, images and videos out of Git.
## Setup
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-atari.txt
.venv/bin/playwright install chromium
PY=.venv/bin/python
ollaya list
ollaya show kev:0.8b
```
Use matching EmulatorJS npm **4.2.3** JS/core assets, currently in
`../EmulatorJS/node_modules/@emulatorjs/emulatorjs/data`; pass `create --assets PATH` otherwise.
Supply your ROM with `create --rom FILE`; default directory:
`~/Games/roms/Atari 2600 Champion Collection/` (Dig Dug: `Dig Dug (NA).a26`).
Use Omarchy CLI for any system-package work; never edit Omarchy core files.
## Front page and one continuous attempt (local inference)
```bash
$PY -m playjev.arcade --port 8765 --provider ollaya --open
$PY -m playjev.live runs/dig-dug-tunnel-v1 --out runs/my-dig-dug-live --provider ollaya
```
Front page: <http://127.0.0.1:8765/>. Choose game/provider, click Start, then Stop & save.
Use either launcher, not both for simultaneous attempts. No automatic batch/reset.
Direct live launch waits for **Start Jev**; `--autostart --seconds 10` is a disclosed smoke cap.
Provider changes apply to the next attempt; hosted selection spends quota on inference.
## Challenge and initial-load discovery (not training or scored gameplay)
```bash
$PY -m playjev.challenge create dig-dug runs/my-dig-dug-challenge --seconds 60
$PY -m playjev.discovery probe runs/my-dig-dug-challenge --out runs/my-discovery --visible
$PY -m playjev.discovery classify runs/my-discovery --provider ollaya
```
Creation records reset/510-frame intro setup. Probes restore explicitly before each bounded input.
Classification logs exact judgments and unknown/hold results; confidence alone is not role proof.
## Bounded practice and verified resumes
```bash
$PY -m playjev.practice runs/dig-dug-tunnel-v1 --metric frames --increment 120 \
  --cap-frames 120 --out-plan runs/my-fresh-plan.json
$PY -m playjev.live runs/dig-dug-tunnel-v1 --practice-plan runs/my-fresh-plan.json \
  --out runs/my-fresh-practice --provider ollaya --autostart
$PY -m playjev.practice runs/dig-dug-tunnel-v1 --metric frames --increment 120 \
  --cap-frames 120 --resume-from runs/my-fresh-practice --out-plan runs/my-resume-plan.json
$PY -m playjev.live runs/dig-dug-tunnel-v1 --practice-plan runs/my-resume-plan.json \
  --out runs/my-resumed-practice --provider ollaya --autostart
```
Resumes verify canonical state/image/challenge/ROM/assets hashes; never silently restart.
Checkpoint normalization/setup frames are disclosed. Failed/suspected-terminal sources cannot resume.
`--metric score` requires a supported baseline and repeated HUD evidence; unavailable for Dig Dug.
## Offline regression and paused calibration (zero inference)
```bash
$PY -m unittest discover -s tests -q
$PY -m compileall -q playjev tests
$PY -m playjev.check_resume runs/dig-dug-tunnel-v1 runs/my-fresh-practice --out runs/my-resume-check
$PY -m playjev.check_display runs/crackpots-start-v1 --out runs/my-display-check
$PY -m playjev.challenge leaderboard --out runs/my-scoreboard
```
Tests use mocked inference. Display/resume checks use local ROM/assets, not model services.
The offline suite enforces this runbook's 100-line limit; keep test results in run output, not here.
Leaderboard only includes supported score evidence; unknown scores never become zero.
## Reporting and evidence files
| File | Responsibility |
| --- | --- |
| `playjev/live.py`, `runtime.py`, `digdug.py` | Continuous loop, adapter hooks, experimental geometry/control |
| `playjev/metrics.py`, `games/emulatorjs/index.html` | Measured counters, inferred ASCII map, game-side panel |
| `games/arcade/index.html`, `playjev/arcade.py` | Provider/practice UI, front-page polling, attempt ownership |
| `playjev/transports.py`, `execution.py`, `timing.py` | CLI requests/logging, stale guards, bounded cycle clock |
| `playjev/native.py`, `checkpoints.py`, `practice.py` | Native capture, verified canonical checkpoints, targets |
| `playjev/discovery.py`, `hud.py`, `scoreboard.py` | Pixel probes, role hypotheses, score proof/cohorts |
| `runs/RUN/metrics.json`, `process.json` | Current counters/ASCII and process lifecycle; read-only reporting |
| `runs/RUN/inference.jsonl`, `decisions.jsonl`, `frames.jsonl` | Exact requests/outcomes, applied/rejected controls, capture hashes |
| `runs/RUN/summary.json`, `final.png`, `replay.webm` | Outcome, last observation, retained recording |
| `runs/RUN/checkpoint*.state`, `checkpoint.json`, `checkpoint.png` | Released-input continuation with disclosed setup |
Live/browser sizing and saved/disconnected reporting validation remain pending.
Reporting: [browser panels](docs/ASCII-REPORTING-REVIEW.md); local vision: [Ollaya models](docs/OLLAYA-MODELS.md).
ASCIIFlow is a candidate editor, not the chosen diagram; the user's visual reference is still pending.
Focus: visible play/one stage per game, supported score+tokens; then optimize and extract repeatable procedures.
## One-command progress save (explicit invocation authorizes the bounded save)
```bash
./scripts/check-in "Describe source progress without claiming completed gameplay"
```
The script stages safe source/docs/tests, runs quick checks and local Jev, commits and pushes your branch.
Operating guide/agent handoff: [CHECK-IN.md](docs/CHECK-IN.md); `--check-only` performs no Git writes.
`atari-continuous-jev` is your primary branch. No merges, resets, branch switches or pushes to `main`.
Local Jev warnings are advisory; actual secret/artifact/test errors block. No hosted fallback.
Details: [tasks](docs/ATARI-TASKS.md), [Dig Dug](docs/DIG-DUG.md), [testing](docs/TESTING-ATARI.md),
[arcade](docs/ARCADE.md), [research prompts](docs/REFACTOR-PROMPTS.md). Keep this runbook at **100 lines maximum**.
