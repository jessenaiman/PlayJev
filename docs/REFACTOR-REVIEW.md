# Virtual controller design boundaries

Use [ATARI-TASKS.md](ATARI-TASKS.md) for unresolved work, not a parallel completed-
review log. Refactor only when a focused test or measured problem justifies it.
Preserve the upstream pixel-policy/harness/training contract and existing Atari CLIs.

## Contracts to preserve and validate

- **Frame-bound action contracts:** in `playjev/live.py` and `playjev/runtime.py`,
  bind observations/results to attempt, capture frame/hash, request and policy
  generation. Revalidate freshness and current Crackpots drop readiness at execution.
  Test capture delay, held-input vetoes and explicit safe release.
- **Lifecycle and metrics:** retain separate request outcomes and proposed/applied/
  sampled-input state. Validate startup, playing, stopping, recording, scoring and
  error presentation. Cancellation/failure must release inputs and preserve video.
- **One comparison contract:** share evidence verification and attempt eligibility
  between `playjev/challenge.py`, `playjev/scoreboard.py` and the front page. Repetition
  must mean independent frame observations, not duplicate final-image files.
- **Extract by responsibility:** share existing native-capture, checkpoint, transport
  and profile helpers before introducing another abstraction. Avoid inheriting game
  policies merely to change providers; broader challenge-module extraction remains
  optional until it simplifies a concrete change.
- **One display transform:** retain source dimensions, displayed content bounds,
  box convention and frame identity. Validate moving rendered pixels across actual
  tile/fullscreen/high-DPI layouts; source geometry alone is not that validation.
- **Arcade robustness:** explicit challenge selection, cached artifact discovery,
  per-file parse failures, lock-consistent process snapshots and visible pending/error
  rows in `playjev/arcade.py` and `games/arcade/index.html`.
- **Modest router:** separate profile registry, routing policy and provider transport.
  Manual pin wins; Jev auto-selection is bounded by code-filtered eligible profiles.
  Reject old-policy results after a switch. Do not copy a CLI fail-open policy blindly
  into game-control safety. See [VISION-ROUTING.md](VISION-ROUTING.md).

Choice selects among candidates; Noul reports p(yes); Score describes graded quality.
Confidence is not permission, pixel evidence or a successful game. Keep local Ollaya
first and stale/eligibility gates code-owned; review recommendations do not prove bugs.
Add focused regressions before broad extraction and retain run evidence locally.
