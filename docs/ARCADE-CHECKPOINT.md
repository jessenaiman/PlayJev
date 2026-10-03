# Arcade prototype checkpoint — 2026-10-03

Code checkpoint: `a277a15b6af5fdc9c3688970f9ab590601973cef`, pushed to
<https://github.com/jessenaiman/PlayJev/tree/atari-continuous-jev>.
`main` was not changed. ROMs, credentials and recordings remain local.

Actual Git commands:

```bash
git commit -m "Add Ollaya CLI arcade switch and frame-safe viewport tracking"
git push fork atari-continuous-jev
git ls-remote fork refs/heads/atari-continuous-jev
```

The remote command returned the full code SHA above. Later documentation commits
may advance the branch; this SHA identifies the code milestone, not its future tip.

## Evidence checked

- 47 offline regressions passed, including the upstream seeded HTML Invaders harness,
  browser input release/deadlines, CLI isolation and evidence-linked HUD comparisons.
- Eight rendered gardener-pixel alignment checks passed; maximum error 0.85 CSS px.
  The diagnostic initially hung on recheck because a paused screenshot Promise was
  inadvertently awaited before its setup frame. The probe now queues without returning
  that Promise, advances one measured setup frame, and bounds screenshot waiting.
- Provider selector browser checks: no inference on page load/toggle, responsive
  layouts, pinned active provider, explicit Stop & save and retained video.
- Local CLI smoke: 728 continuous frames, one stale decision rejected, zero applied.
  Deterministic re-review supported HUD score 0 from 70 frames, with no inference.
  This demonstrates safe failure handling, **not successful local gameplay**.
- Existing hosted viewport/safety smoke recorded score 60, before development switched
  to local-only tests. No hosted inference was used for the subsequent default tests.

`playjev.review_checkin --authorized --provider ollaya` ran the actual staged checks
and reviewed a bounded check summary through the CLI. Deterministic checks passed
and Kev selected `ready`. Full packet/exact exchange is retained locally under
`runs/arcade-processes/checkin-review.json`. This was a scoped prototype-readiness
judgment, not a line-by-line code review, correctness certificate or hosted Jev call.

## Still open

Local inference latency/calibration and packed GPU allocation; actual Omarchy
fullscreen/touchscreen interactions; terminal calibration and full-attempt ranking;
alternating trials; additional ROM adapters; automatic/free-LLM vision routing;
progressive endpoint ledger/targets and optional practice-only checkpoint resumes.
See [ATARI-TASKS.md](ATARI-TASKS.md). Do not interpret this checkpoint as completing
those features or reproducing upstream's trained pixel-model benchmark.
