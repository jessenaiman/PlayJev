# Atari iteration task list

Update this list and post the active checklist in chat whenever focus changes.
Do not mark a feature complete from a model judgment alone: attach tests/run evidence.

## Current ordered work queue

This file is the persistent project checklist. Completed means tested/artifact-backed,
not merely a model's opinion. OpenCode's native todo tool is not exposed in this
session; V2 API discovery found no todo route/schema. No native todo update is claimed.

1. **Implemented; calibration blocked:** initial-load discovery/classification (§10):
   repeatable probes and typed hypotheses exist; actual Kev roles stay unknown/observe-only.
2. **Completed/tested:** bounded progression/resume (§9): exact 120-frame fresh/resumed
   browser segments, compatible checkpoints, paired traces and cancelled-request evidence.
3. **Blocked:** effective per-action Ollaya control: latest 600-frame Dig Dug trial
   completed two replies after 258/215 frames (4.24/3.53 s), rejected both, zero applied.
4. **Pending:** Dig Dug high-score/pump/terminal calibration and fresh-frame discovered
   controller integration; never claim a win or unknown score as zero.
5. **Completed:** tested code checkpoint `a49128d` pushed to the fork and remote SHA
   verified. Native capture is consolidated; further lifecycle refactoring awaits
   findings from [REFACTOR-PROMPTS.md](REFACTOR-PROMPTS.md).
6. **Queued:** terminal contracts, real compositor/touch checks, fair provider trials,
   additional games, vision/free-model routing and supported native task integration.

## 1. High scores, refactoring and front page

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

- [x] Dig Dug experimental adapter: four-direction/pump actions, native player/enemy
      and coarse tunnel estimates; local challenge and visible calibration artifacts.
- [ ] Dig Dug: effective pump timing, rocks/ghosts, score glyphs and lifecycle calibration.
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
- [x] Supply endpoint failures and progress targets as bounded context to the next
      controller attempt, preserving inference/action provenance.
- [x] Fresh-start evaluation stays separate from adaptive practice and any explicitly
      resumed checkpoints. Never silently resume/reset or rank evolving budgets together.
- [x] Test unknown baseline, evidence tampering, capture/hash mismatch, repeated
      failures and increment bounds; browser ledger/goal preview and layouts checked.
- [x] Test repeated-score goal acceptance and frame-budget execution/caps; fresh goal
      clipping is reported not achieved. Actual score-goal gameplay remains unproven.
- [ ] Optional automatic batches/checkpoint schedules need separate user authorization,
      explicit reset rules and terminal calibration; current progression is one click/segment.

## 9. Active iteration: resumable practice and Dig Dug

- [x] Explicit next-practice launch: supported score + X, or labelled frame-budget
      extension + X; configurable per-segment cap, no automatic batch/reset.
- [x] Save a released-input, canonical emulator checkpoint with ROM/assets/challenge
      hashes, state/image hashes, parent linkage and disclosed setup-frame counts.
- [x] Verify checkpoint bytes and canonical restore before resuming; reject changed,
      incompatible, failed or suspected-terminal sources rather than restarting silently.
- [x] Stop on supported repeated HUD target or frame cap; supply bounded prior endpoint
      context to the controller and keep all practice modes explicitly unranked.
- [x] Add front-page fresh/resume practice controls and tests for unknown scores,
      achieved targets, caps, repeated failures, tampering and provider pinning.
- [x] Create `dig-dug-tunnel-v1` with disclosed intro setup; test four-direction/pump
      inputs and native terrain/enemy/player candidates. Score remains unknown.
- [x] Run visible Dig Dug and resume checks on Ollaya CLI only; preserve delayed/failed
      actions and recordings without claiming successful LLM play.
- [x] Update docs, run 75 offline regressions, local CLI evidence review (`ready`),
      and publish code checkpoint `a49128d`; remote SHA verified. See
      [RESUME-DISCOVERY-CHECKPOINT.md](RESUME-DISCOVERY-CHECKPOINT.md).

## 10. Initial-load discovery and classification — active

- [x] Make initial-load calibration a repeatable script: canonical restore, bounded
      joystick/pump probes, native snapshots, pixel deltas and object-motion bounds.
- [x] Separate measured candidate objects/starting boxes from typed role hypotheses;
      include unknown/coverage gaps and retain exact Jev/Ollaya questions/probabilities.
- [x] Profile verification gates bind repeatable snapshot evidence and challenge/ROM/
      assets/script; tests reject tampering and unsupported player hypotheses. Actual
      Kev role failures are disclosed; no live discovered controller was enabled.
- [ ] Combine the classified profile with fresh-frame geometry for Dig Dug control;
      measure scores and failures, never call discovery a completed high-score run.
- [x] Keep discovery/classification distinct from model training, scored gameplay,
      automatic ROM execution, benchmark resets and hidden inference/provider fallback.
- [x] Local limit/unsupported-feature safety fallback: release/stop/save for failed
      gameplay; observation-only for unusable classification. Exact requests retained.
      Mocked live failure test verifies recording preservation and no hosted call.
- [ ] Calibrate narrow typed-role judgments or select an explicitly working provider;
      cached strategy/controller integration cannot proceed from the rejected roles.

## 11. Research and systematic tracking

- [x] Copy/paste package/refactor prompts in [REFACTOR-PROMPTS.md](REFACTOR-PROMPTS.md).
- [x] Refresh this ordered queue, per-feature tasks and current evidence/blockers.
- [x] Verify OpenCode V2 API/tool availability rather than inventing a native todo update.
- [ ] Use a supported native todo/task tool if exposed later; currently unavailable.
- [ ] Review the user's returned research, choose minimal dependencies and test the
      migration before installing packages or replacing working contracts.

### Latest evidence

75 offline tests passed. Shared native capture passed eight rendered-pixel checks
(max 0.85 CSS px) and seven paired resume image/state comparisons. Browser practice
checks at 390×844, 960×540 and 1440×900 passed; latest resumed segment saved the exact
cancelled request, video and checkpoint at 120 frames. Evidence is local under
`runs/arcade-processes/practice-resume-browser-check-v2.json`, `display-check-v2/`,
`dig-dug-resume-check-v2/` and `dig-dug-discovery-v1/`. No hosted inference was used
for this iteration. Dig Dug high-score completion and real-time Ollaya play are blocked.
