# Virtual controller refactor review

Read-only delegated review, 2026-10-03. No implementation or test results are implied.
The reviewer answered the prerequisite quiz before receiving permission to inspect
the project. Parent graded all three answers as passing:

1. Choice selects a profile; Noul checks evidence support; Score rates graded quality.
   Noul 0.5 means equal probability of yes/no, not medium quality; confidence is not
   permission or proof of correctness.
2. Independent questions with existing evidence can share a request. They cannot
   consume each other's answers; new vision evidence requires subsequent verification.
3. Code rejects stale results, honors user pins/free-only constraints and enforces
   bounds. Model agreement alone does not establish grounded or comparable outcomes.

## Recommendations to validate before implementing

Priority implementation remains the reported rendered-overlay alignment issue.
Reviewer identified possible coordinate and temporal risks, not a confirmed cause.

- **Frame-bound action contracts:** in `playjev/live.py` and `playjev/runtime.py`,
  bind observations/results to attempt, capture frame/hash, request and policy
  generation. Revalidate freshness and current Crackpots drop readiness at execution.
  Test capture delay, held-input vetoes and explicit safe release.
- **Lifecycle and metrics:** separate started/completed/failed/cancelled requests and
  proposed/applied actions in `playjev/metrics.py`. Expose startup, playing, stopping,
  recording, scoring and error states through `playjev/arcade.py`. Check that transport
  cancellation and failure cleanup actually release inputs and preserve partial video.
- **One comparison contract:** share evidence verification and attempt eligibility
  between `playjev/challenge.py`, `playjev/scoreboard.py` and the front page. Repetition
  must mean independent frame observations, not duplicate final-image files.
- **Extract by responsibility:** split `playjev/challenge.py` into emulator execution,
  challenge identity, inference transports, game policies and comparison/recording.
  Keep its CLI stable; avoid inheriting gameplay policies just to change providers.
- **One display transform:** remove duplicated hard-coded geometry assumptions between
  `playjev/spatial.py` and `games/emulatorjs/index.html`. Include source dimensions,
  displayed content bounds, box convention and frame identity; test rendered pixels.
- **Arcade robustness:** explicit challenge selection, cached artifact discovery,
  per-file parse failures, lock-consistent process snapshots and visible pending/error
  rows in `playjev/arcade.py` and `games/arcade/index.html`.
- **Modest router:** separate profile registry, routing policy and provider transport.
  Manual pin wins; Jev auto-selection is bounded by code-filtered eligible profiles.
  Reject old-policy results after a switch. Do not copy a CLI fail-open policy blindly
  into game-control safety. See [VISION-ROUTING.md](VISION-ROUTING.md).

Add focused regression tests before broad extraction. These are source-review findings,
not reproduced runtime defects. Existing recorded runs/tests remain separate evidence.
