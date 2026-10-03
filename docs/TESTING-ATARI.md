# Testing this PlayJev fork without hosted quota

Keep upstream `scripts/reproduce.sh`, `playjev.env.VecGame`, the HTML hooks and
the pixel-model training/inference paths intact. See [HARNESS.md](HARNESS.md).
This fork extends those ideas; it does not replace the upstream benchmark or
pretend the Atari ROM is the HTML5 Space Invaders environment.

## Offline regression layer

```bash
.venv/bin/python -m unittest discover -s tests -q
.venv/bin/python -m playjev.bench invaders --pages 8 --steps 200
```

Regression inference adapters are mocked. The browser-control tests use fake frame
clocks, while the upstream harness test checks identical seed/action histories for
equal scores, clocks and frame hashes. No inference service or hosted key is needed.
The original random-policy bench uses the real unmodified HTML harness; episode
restarts there are explicit benchmark resets, not hidden resets in a visible Atari
attempt. Do not run the full training/reproduction pipeline as a routine smoke test:
upstream documents substantial CUDA/training requirements.

The suite covers input release/recording preservation on failure, observation-only
discovery fallback, native capture, checkpoint tampering and bounded progression.
Keep test output in the local check/run report, not a manually updated pass-count log.

Upstream reports Space Invaders 400 for its pixel policy and teacher on held-out
HTML-game episodes, with random 215 in the published table. The model reads the
frame and options, not HTML or teacher `info()`. Never compare those numbers to
Atari ROM points such as this fork's reviewed 1,640.

## Explicit local integration layer

```bash
ollaya list
ollaya show kev:0.8b
.venv/bin/python -m playjev.arcade --provider ollaya --open
```

Use the score-page **Decision provider** selector. It affects the next recommendation
or attempt and does not itself invoke inference. Active attempts retain their provider.
The server defaults to Ollaya and the page no longer requests recommendations on load.

The adapter invokes `ollaya run MODEL --format json --questions JSON`, passing
structured state via stdin with `--state-json`. It does not implement an Ollaya HTTP
client. Hosted credentials are removed from its child environment. Questions are
serialized with full state/rubrics to avoid the measured packed-context GPU failure;
subrequests and subresponses are retained. Truncated state is rejected, never hidden.

Optional visible capped development check (not a ranked full attempt):

```bash
.venv/bin/python -m playjev.live runs/crackpots-start-v1 \
  --out runs/my-local-smoke --provider ollaya --seconds 12 --autostart
```

Use a fresh output directory. Normal visitor attempts have no default time cap.
Known font glyphs use identical deterministic template/repetition scoring regardless
of controller provider; damaged glyphs remain unknown. `frames.jsonl` binds sampled
PNGs to capture intervals; a duplicate `final.png` cannot supply a second observation.
The optional `playjev.hud RUN --typed` explicitly invokes the run's selected provider
for additional glyph judgments; it still cannot override exact pixel checks.

## Hosted exception — measured bottleneck and approval only

Only after local evaluation and explicit approval, select **Jev · hosted** on the
page, or launch with `--provider jev`. The TypeSafe key
stays server-side. There is no automatic fallback, hidden retry or provider substitution.
The recorded provider is used for the entire attempt. Hosted regression checks are
not part of the default test command. The older `playjev.challenge run --player jev...`
benchmark commands also spend hosted quota; local Invaders uses `--player ollaya-gates`.

## Practice/resume and discovery checks

Use a fresh output directory/plan filename:

```bash
.venv/bin/python -m playjev.practice runs/dig-dug-tunnel-v1 \
  --out-plan runs/my-practice-plan.json --metric frames --increment 120 \
  --cap-frames 120 --resume-from runs/dig-dug-resume-smoke-v1
.venv/bin/python -m playjev.live runs/dig-dug-tunnel-v1 \
  --out runs/my-resumed-practice --practice-plan runs/my-practice-plan.json \
  --provider ollaya --autostart
.venv/bin/python -m playjev.check_resume runs/dig-dug-tunnel-v1 \
  runs/dig-dug-resume-smoke-v1 --out runs/my-resume-check
```

The last command makes no inference call. It replays seven fixed input segments
twice and compares image/state hashes. It is paused control calibration, not a score.
The earlier commands explicitly invoke local inference during one capped practice
segment. A frame-budget achievement is not proof of survival, cleared terrain or a win.

Discovery/classification is a separate workflow; see [DIG-DUG.md](DIG-DUG.md).
Initial probes restore before each input, with two native-capture setup frames per
probe. Typed classification is opt-in (`--provider ollaya` by default); unusable roles
or inference limits save a safety hold/observation-only report. No automatic hosted
fallback or controller activation occurs. An explicit `--provider jev` classification
retry spends hosted quota; do not include it in routine regressions.

## Local-model validation requirements

Measure cold/warm latency, decision age, memory and labeled semantic accuracy
separately. A fast request or repeatable deterministic input trace does not prove
accurate role classification, effective pumping or continuous Jev gameplay.
Keep unusable roles observation-only; do not weaken expiry guards to obtain movement.
Exact logical requests/responses/cancellations belong in `inference.jsonl`, including
requests that produce no completed decision row. Preserve failed recordings and
unranked summaries locally, without duplicating a trial history in documentation.

Evaluate [Ollaya text and vision](OLLAYA-MODELS.md) before considering an explicitly
approved hosted exception for a reproducible local bottleneck. Regression tests
remain mocked; optional vision/model downloads and probes are separate operations.

## Community-facing extension boundaries

Build contributions as separable changes: inference adapters/profile selection,
frame-bound action safety, evidence-linked comparisons and reproducibility checks.
Avoid changing upstream teachers or claiming privileged JSON observations equal its
pixel-only contract. Add paired held-out trials (upstream uses 16 episodes per game),
random/reference rows, real-time/delayed-inference conditions and replay verification.
For ROMs, pin canonical states/assets/settings instead of treating a seed as enough;
keep fixed-budget and continuous natural-end cohorts distinct. No ROMs are distributed.
