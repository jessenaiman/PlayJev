# Atari iteration task list

Update this list and post the active checklist in chat whenever focus changes.
Do not mark a feature complete from a model judgment alone: attach tests/run evidence.

## 1. High scores, refactoring and front page — active

- [x] Extract shared live-game hooks: observe, track, overlay, prepare controls,
      lifecycle signal, player factory and score collector.
- [x] Share score evidence verification/grouping between static board and front page.
- [x] Landing page with available games, reviewed scores and replays. Detailed pending-result display remains a refinement.
- [x] Hosted Jev selects an available game from the user's intent and session state.
- [x] Start one attempt explicitly; save request/response and never fabricate a win.
- [x] Add a reusable timing/wait gate: Jev chooses readiness/wait reason and a
      bounded frame interval; code owns actual clocks, expiration and execution.
- [x] Tests for navigation, unavailable games, single-attempt launch, mutation authorization and stop/save.
- [x] Extend HTTP tests to rate limits, timeouts, concurrent recommendations and
      scoring/failed-child states (47-test offline pass).

## 2. Presentation and Jev metrics

- [x] Responsive front page and game-side ASCII observation panel.
- [x] Live gates/probabilities, inference age/latency, applied actions, vetoes and usage.
- [x] Show measured counters separately from inferred sprite labels and model confidence.
- [x] Browser layouts and continuous smoke check after refactor; raw-frame equality at three viewport sizes.
- [ ] Full touchscreen/fullscreen interaction and high-DPI emulator overlay alignment checks.
- [x] Reproduce the quarter-size canvas/renderer mismatch and fix WebGL viewport
      projection; eight rendered-pixel checks at four sizes and two DPRs passed.
- [ ] Recheck the actual bottom-right Omarchy tile and fullscreen/touch interactions;
      validate rendered sprite/outline alignment, not only raw-frame equality.
      paused pixel checks do not certify moving sprite detection on every layout.

## 3. Game over detection

- [ ] Calibrate Crackpots building-loss/terminal signals against full recorded attempts.
- [ ] Jev lifecycle judgments over observed temporal evidence: playing, respawning,
      wave transition, game over, unknown. Pair with deterministic restart protection.
- [ ] Validate Space Invaders' color-cycle candidate; do not equate it to proof.
- [ ] End naturally, record the final/highest HUD, never pad frames or auto-restart.
- [ ] Make full-attempt leaderboard eligibility explicit and tested.

## 4. Two-player Jev / Ollaya turns

- [ ] Resolve Kev GPU allocation failures or explicitly configure a working CPU server.
- [x] Separate inference transport from policy; Ollaya CLI only, no automatic hosted
      fallback, hosted credentials removed from child environments (transport tests).
- [x] Score-page Ollaya/Jev provider toggle; no inference on load/switch; active
      attempt stays pinned. Browser layout/toggle/early-stop video evidence saved.
- [ ] Reduce local inference latency and calibrate Kev judgments before comparisons:
      a 12-second smoke rejected a 632-frame-old answer; packed CLI contexts still
      fail CUDA allocation. Sequential CLI probes work but are not real-time.
- [ ] Alternate whole attempts from identical ROM/state/control settings and limits.
- [ ] Keep provider/model/turn identity and score/replay evidence in each record.
- [ ] Native alternating-player game modes, where supported, need separate calibration;
      they are not the same as benchmark alternation or shared-controller turns.
- [ ] Report paired observed scores; no universal winner from one trial.

## 5. New games

- [ ] Dig Dug: controls, terrain/enemy perception, pump timing, score glyphs, lifecycle.
- [ ] Pitfall: moving hazards, jumps, lives/timer, treasure scoring, lifecycle.
- [ ] Asteroids: heading/velocity, lead shots, wraparound prediction, HUD and lifecycle.
- [ ] Register adapters without adding per-game branches to the shared live loop.
- [ ] Visible smoke check and uncertainty review before promoting each game to playable.

## 6. Jev-assisted check-in and push

- [x] Capture exact diff scope, tests, secret/artifact exclusions, branch and remote.
- [x] Selected typed provider reviews release readiness; exact packet/request/response
      saved locally. Development used Ollaya CLI, with hosted Jev still opt-in.
- [x] Deterministic checks and explicit user authorization remain the authority.
- [x] Commit/push `a277a15` to `fork/atari-continuous-jev`; remote SHA verified.
- [x] Document the demonstrated workflow and limits, not an unsupported universal
      "best practice" or a claim that Jev itself ran Git.

## Existing limitations to preserve visibly

Crackpots game-over detection is unvalidated. Ollaya gameplay is blocked. Live smoke
scores are reviewed but unranked. ROMs, credentials and run artifacts remain local.
The launcher is Python/Playwright, not yet a fully hosted HTML-roster integration.
Development now defaults to Ollaya CLI. Exact-template HUD scoring requires no
inference; hosted Jev is an explicit score-page switch, not a hidden fallback.
See [TESTING-ATARI.md](TESTING-ATARI.md) for upstream/local test contracts and failures.

## 7. Vision + Jev cookbook research — queued after this iteration

- [x] Review jev-router's documented interfaces and record integration boundaries
      in [the vision routing plan](VISION-ROUTING.md).
- [ ] Include a pinned jev-router integration after verifying its source/API and
      license; document model swaps without altering the user's global CLI settings.
- [ ] Review live TypeSafe extraction cascades, function calling and guardrail cookbooks.
- [ ] Verify available OpenCode Go models, actual image support and current free pricing.
- [ ] Draft a workflow where the communication/vision model proposes structured
      screen evidence and invokes Jev's typed checks; code validates and executes.
- [ ] Prefer deterministic native pixels/OCR first, vision on ambiguous cases only.
- [ ] Record image provenance, proposed evidence, Jev questions/answers, latency,
      usage and failure routing. No model confidence is evidence of a real score.
- [x] Delegate a read-only architecture review after passing a three-question
      TypeSafe quiz; recommendations recorded in [REFACTOR-REVIEW.md](REFACTOR-REVIEW.md).
- [ ] Add user-pinned and Jev-auto controller model selection; pins take precedence,
      and auto routing sees only verified eligible profiles plus abstain.
- [ ] Add a free-LLM-only OpenCode Go profile policy; verify actual account pricing,
      image/tool support and access. Hosted Jev remains separately accounted for.
- [ ] Compare "which LLM operates the Jev Atari virtual controller best": paired,
      repeated attempts with identical starts/settings and evidence-linked scores.
- [ ] Separate fixed-model attempts from adaptive-router attempts; show high scores,
      score distributions, latency, stale/veto rates, failures and usage, not one winner
      inferred from a single lucky run.

## Current iteration evidence and next execution order

- [x] Fix letterboxing with the WebGL viewport; display diagnostic recorded under
      `runs/arcade-processes/display-check-v1/` (max gardener error 0.85 CSS px).
- [x] Frame-bound request envelopes, execution-time stale checks and explicit release;
      current-frame Crackpots interception recheck. Browser-control regressions pass.
- [x] Started/completed/failed/cancelled counters, proposed-vs-executed labels,
      lifecycle phases and failure recording preservation.
- [x] CLI comparison now shares board evidence hashing and game/challenge/mode grouping.
- [x] Upstream HTML Invaders random bench and paired seed/action/frame-hash regression;
      preserve pixel-policy/teacher distinction and the upstream training recipe.
- [x] Finish regression documentation and prototype check-in; see
      [the release checkpoint](ARCADE-CHECKPOINT.md).
- [ ] Local inference performance/calibration, then terminal calibration and comparable
      whole-attempt contracts. Keep unavailable Ollaya setups visibly blocked.
- [ ] Alternating/provider-profile comparisons, new game adapters, then queued vision
      and free-model routing cookbook implementation; no premature playable/winner claims.

## 8. Progressive practice targets — tracking/preview implemented

- [x] Record a last-observed endpoint ledger: run/frame/image hash, supported score,
      observed game progress, stop cause, player/target geometry and replay links.
      Keep last observation distinct from the exact terminal state if capture lags.
- [x] Score-page configurable X and best-supported-score + X goal preview, scoped to
      one challenge; tested Crackpots 690 + 100 = 790 with no inference/launch.
- [ ] Calibrate game-progress metrics (e.g. cleared aliens/waves); unsupported
      wave/score values stay unknown. Budget increments, if added, must be explicit
      practice caps rather than completion/progress evidence.
- [ ] Supply endpoint failures and progress targets as bounded context to the next
      controller attempt, preserving inference/action provenance.
- [ ] Fresh-start evaluation stays separate from adaptive practice and any explicitly
      resumed checkpoints. Never silently resume/reset or rank evolving budgets together.
- [x] Test unknown baseline, evidence tampering, capture/hash mismatch, repeated
      failures and increment bounds; browser ledger/goal preview and layouts checked.
- [ ] Test achieved-target execution and caps before enabling automatic progression.
