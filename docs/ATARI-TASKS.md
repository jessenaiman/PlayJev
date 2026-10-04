# Atari open tasks

**Focus: visible local AI play, supported scores/costs, and one stage clear per game.**
This is the single open-work checklist. Remove a gameplay task only after native recordings
support its acceptance criteria; do not keep completed checkboxes, release summaries
or past-work logs here. Git holds change history; local run artifacts hold evidence.
Native task tooling is not exposed in this session; this is a Markdown checklist.
Provider policy: **Ollaya first**, including local vision where useful. Hosted
options require a reproducible local bottleneck and explicit user approval;
never switch automatically. See [local models](OLLAYA-MODELS.md).

## Active iteration fixes

Operating loop: visible game → evidence-linked end report → bounded JSON change →
visible replay. Show the outcome after every ending. Only a verified stage clear is
success; a score increase, applied controls or passing tests is not. Do not run system
tests to classify moves or iterate policies; use them only to diagnose an actual crash.

- [ ] `playjev/policies/crackpots.json`: resolve repeated `hold`/`scan` choices when
      another pot has an estimated catch. Judge each revision by visible gameplay,
      not wording, confidence or changes in command counts alone.
- [ ] `playjev/loss_review.py`: automatically compare the exact previous/current JSON
      and supported gameplay outcomes in each end report; reject recycled failed
      rubrics and no-op edit operations. Preserve original reviews and disclose
      parent hypotheses separately from model recommendations.
- [ ] `playjev/loss_review.py`: improve alternative-action judgments using the ignored
      intercept and full move/frame identity; distinguish missing movement, missed
      firing, rejected execution and unknown perception instead of a generic refactor.
- [ ] `playjev/crackpots.py`, `playjev/runtime.py`: establish native first-wave-clear
      evidence. Keep stage success separate from the startup/score-progress audit in
      `playjev/completion.py`; never promote `progressed` to a win.
- [ ] `playjev/crackpots.py`, `playjev/policies/crackpots.json`: separate candidate facts
      in state from option definitions, and make the gameplay question JSON directly
      reusable with `ollaya run --questions`; changing a rubric must not require a
      new Python renderer/import or a different provider schema.
- [ ] `playjev/transports.py`: resolve unnecessary one-question CLI calls within a
      workflow against the parallel-questions cookbook using recorded local memory,
      latency and token evidence. Keep startup/gameplay/completion/review separate.
- [ ] Review useful Noul/Score judgments against the function-calling/confidence
      cookbooks before adding them; compact gameplay currently uses Choice only.
      Code-known counts and native proof do not need extra model questions. Account
      for provider-specific Score confidence rather than assuming identical semantics.

Cookbook/schema references: [function calling](https://docs.typesafe.ai/cookbooks/function_calling.md),
[confidence](https://docs.typesafe.ai/confidence.md),
[parallel questions](https://docs.typesafe.ai/cookbooks/parallel_questions.md),
[Ollaya compatibility](https://ollaya.dev/docs/typesafe-compatibility).

## Gameplay milestones — in order

### First-stage arcade goals
- [ ] Clear Dig Dug's first round with recorded enemy defeats and a supported HUD;
      a title return, a timer or applied controls alone is not a stage clear.
- [ ] Clear a Crackpots bug wave and verify its transition from native frames.
- [ ] Reproduce Space Invaders' first-wave clear with the local Ollaya controller;
      older paused/hosted evidence is a separate playback/provider contract.
      Optimize and repeat after playable progress; do not gate ordinary visible
      attempts behind the later procedure-reuse acceptance bar.

### 1. Reliable controls
- [ ] Calibrate narrow role/action judgments on labeled native frames, including
      player identity, enemies, rocks, ghosts and unknown/occluded cases.
- [ ] Evaluate `decider:2b-vision` via CLI `--image` after an approved download;
      add image/hash/frame-envelope handling to the transport only after measuring
      local memory, cold/warm latency and labeled accuracy. Text-only integration
      is not image support, and a vision model is not a working gameplay policy.
- [ ] Resolve local allocation/latency failures without weakening stale guards;
      verify semantic accuracy separately from response speed.
- [ ] Independently verify a discovered profile and connect it to fresh-frame,
      bounded execution, with explicit Jev-versus-code controller attribution.
      **Acceptance:** recorded continuous play shows intended movement actually
      applied before expiry; missing/ambiguous evidence releases inputs. Paused
      calibration or a completed inference request alone does not qualify.

### 2. Calibrated pumping
- [ ] Measure facing, alignment, pump range and hold/tap/release timing against
      native frame sequences; distinguish inflation, defeat and lost contact.
- [ ] Demonstrate repeatable enemy defeats without accidental restarts; cover
      wrong-facing, out-of-range, respawn and missing-player negative cases.
      **Acceptance:** recordings show the target inflating and bursting, linked
      to bounded executed inputs and independently supported score changes.

### 3. Supported score and terminal evidence
- [ ] Complete the partial bottom-right HUD font on labeled frames; reject unreadable or
      unfamiliar glyphs and verify scores over independent capture intervals.
- [ ] Distinguish active play, respawn, round transition and game over using
      temporal evidence; prevent fire from starting another game after death.
      **Acceptance:** supported score/terminal outcomes link to hashed native
      frames and replay. Unknown stays unknown; stop/save never implies completion.

### 4. Repeatable runs and reusable procedures
- [ ] Run at least three fresh-start attempts with identical challenge/ROM/assets,
      provider/model, controls and attempt limits; retain failures and report
      supported scores/progress alongside latency, stale/veto rates and usage.
- [ ] Confirm repeatable movement and enemy defeat/round progression, then extract
      recorded stages into procedures with preconditions, typed questions,
      fresh-frame gates, bounded actions, failure/abstain paths and outcome checks.
      **Acceptance:** replay the procedures on Dig Dug before porting their shared
      interface to another game. Keep calibration, fresh/resumed practice and
      ranked evaluation separate; no high-score or completed-game claim by default.

## Current blockers

Role calibration cannot activate a valid discovered controller. Local inference
can still fail allocation or return incorrect/uncertain judgments. Enemy defeat,
full Dig Dug HUD coverage and verified stage/terminal detection remain unresolved. See
[Dig Dug](DIG-DUG.md) for operational details and acceptance requirements.

## Supporting work

- [ ] Validate both reporting panels at mobile/desktop sizes and real Omarchy
      tile/fullscreen/touch/high-DPI layouts, including saved/disconnected states
      and moving sprite/outline alignment. Expose request/source/deadline identity
      and unknown score/terminal state. See [reporting](ASCII-REPORTING-REVIEW.md).
- [ ] Validate separate lifecycle recipes on the other ROM adapters; reject
      uncertain or contradictory improvement recommendations. Add labeled
      demo/active/terminal negatives before generalizing native
      input-effect proofs to every ROM or trusting automatic improvement routing.
- [ ] Incorporate the user's visual reference before selecting a procedure diagram;
      no new renderer dependency unless the working workflow requires it.
- [ ] If local model routing becomes necessary, verify/pin jev-router source/API/
      license before reuse; retain eligible profiles, manual-pin precedence and
      stale-generation rejection. Do not add a router merely to run one local model.
      See [routing](VISION-ROUTING.md).

## Later backlog

- [ ] Add human keyboard/touch challenges with saved player handles, shared start/
      action contracts and code-controlled score evidence. Do not label an AI run human.
- [ ] Compare model handles by stage progress, score, tokens, latency and vetoes under
      matching contracts; extend the attempt-token panel to discovery/navigation/
      development costs and hardware/time budgets before claiming an all-cost winner.

- [ ] Calibrate Crackpots and Space Invaders terminal signals and natural-end
      attempt/leaderboard eligibility; never use a color-cycle candidate as proof.
- [ ] Calibrate real progress/score-goal practice; frame caps are not survival or wins.
      Automatic batches/checkpoint schedules require separate authorization.
- [ ] Compare repeated paired fixed-provider and adaptive-router attempts fairly;
      retain model/turn attribution and keep native two-player modes separate.
- [ ] Only if local evaluation establishes a real bottleneck, catalog hosted
      capabilities/access/pricing and request explicit approval for a bounded
      comparison. The check-in OpenRouter adapter is not gameplay integration.
- [ ] Add Pitfall and Asteroids through shared adapter hooks, each with movement,
      hazard, HUD and terminal calibration before promotion to playable.
- [ ] Review returned research before lifecycle/policy extraction or dependency
      changes; keep CLI contracts and upstream pixel-policy/harness paths intact.
      See [research prompts](REFACTOR-PROMPTS.md) and [refactoring](REFACTOR-REVIEW.md).
- [ ] Adopt native task tracking only if supported tooling becomes available;
      keep one open-work source of truth, without completed-task archives.
