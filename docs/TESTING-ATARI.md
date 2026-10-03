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

Latest recorded upstream random check: 1,600 environment steps, 689 steps/s, four
episodes ended, mean completed-episode score 187.50. This is a short throughput
check, not a reproduction of the published 16-episode policy evaluation.

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

## Hosted development fallback — explicit only

Select **Jev · hosted** on the page, or launch with `--provider jev`. The TypeSafe key
stays server-side. There is no automatic fallback, hidden retry or provider substitution.
The recorded provider is used for the entire attempt. Hosted regression checks are
not part of the default test command. The older `playjev.challenge run --player jev...`
benchmark commands also spend hosted quota; local Invaders uses `--player ollaya-gates`.

## Current local findings, not successes

- The exact recorded five-question gameplay request passed sequential Ollaya CLI
  inference in 4.35 seconds without state truncation.
- The packed five-question CLI invocation failed CUDA allocation. Retained under
  `runs/arcade-processes/ollaya-cli-batch-probe-v1.json`.
- A visible local 12-second smoke advanced 728 frames continuously. One completed
  decision arrived 632 frames late and was rejected; zero actions were applied.
- Kev did not recognize the exact zero HUD glyph in the optional typed path. The
  strict scorer correctly left that earlier review unknown. Deterministic font lookup
  is now the shared default, avoiding unnecessary inference for exact-known glyphs.
- Some live local contexts still exhaust GPU memory. Failed runs preserve recordings,
  failure counters and unranked summaries. These are transport/model-performance
  blockers, not permission to quietly use hosted Jev.

Latency and allocation must improve before local high-score comparisons are meaningful.
The provider switch is working; effective local gameplay is not yet established.

## Community-facing extension boundaries

Build contributions as separable changes: inference adapters/profile selection,
frame-bound action safety, evidence-linked comparisons and reproducibility checks.
Avoid changing upstream teachers or claiming privileged JSON observations equal its
pixel-only contract. Add paired held-out trials (upstream uses 16 episodes per game),
random/reference rows, real-time/delayed-inference conditions and replay verification.
For ROMs, pin canonical states/assets/settings instead of treating a seed as enough;
keep fixed-budget and continuous natural-end cohorts distinct. No ROMs are distributed.
