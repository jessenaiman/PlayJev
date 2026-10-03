# Vision fallback and swappable models — integration plan

Status: planned, not a working vision fallback. Finish the current rendered-overlay
alignment fix before implementing the queued cookbook iteration.

## Include jev-router

Upstream: <https://github.com/gargpratyush/jev-router> (MIT, per its README).
The README reviewed for this plan describes `jev-claude` and `jev-codex` wrappers:
Jev selects a model tier on fresh user turns, while native CLIs retain their tools,
authentication, permissions and sessions. Concrete model selection pauses routing;
the router sentinel resumes it. Codex tier models can be overridden with
`JEV_CODEX_FAST_MODEL`, `JEV_CODEX_BALANCED_MODEL`, `JEV_CODEX_STRONG_MODEL`, and
`JEV_CODEX_LONG_MODEL`. See upstream for current defaults and installation steps.

These are **CLI-turn routing features**, not an OpenCode Go provider adapter or a
gameplay image-check API. Do not claim that installing the package enables either.
Before including runnable upstream code, inspect its source, pin a revision, retain
its license, and test the integration boundary. No upstream code is vendored yet.
Keep arcade model configuration separate from global Claude/Codex/OpenCode settings.

## Proposed arcade flow

1. Code observes native pixels and computes the actual displayed content rectangle.
   First fix projection arithmetic/letterboxing; vision must not hide that bug.
2. The normal combined Jev gameplay request also judges whether available evidence
   warrants a visual audit. Signals can include failed bounds checks, missing player,
   disagreement between observations, resize events or a user's mismatch report.
   A periodic visual audit can catch mismatches these signals do not expose.
3. A selected vision-capable communication model receives an emulator-only rendered
   crop plus its coordinate transform and, where needed, the native frame. Compare
   a clean rendered crop against the proposed boxes; an annotated copy is context,
   not proof. Do not upload the desktop, unrelated windows, ROM or credentials.
4. The vision model proposes structured evidence: observed sprite boxes, displayed
   content bounds, disagreements and uncertainty. It invokes a bounded Jev-check tool
   using that evidence. Jev checks the supplied claims; it does not independently
   see pixels in the existing structured-state API.
5. Code validates schema, coordinate transforms, bounds, frame identity and freshness.
   Validated diagnoses can flag/suppress suspect overlays. Do not let a stale vision
   answer directly overwrite current controller actions or claim a verified score.

Emulation remains continuous. Visual audits run asynchronously, rate-limited with
at most one audit in flight. Failed/unavailable vision produces an explicit unknown
state, not a hidden game reset, blocking wait or silent paid-model fallback.

## Model swap contract to implement

- Named profiles map to exact provider/model IDs and verified image/tool capabilities.
- Separate routing policy from inference transport and credentials.
- An explicit profile override wins over automatic selection; unavailable models are
  reported rather than silently substituted.
- Allow a configured free-only policy; verify current pricing and account access.
  OpenCode Go availability is not itself evidence that a model is free or image-capable.
- Log the selected profile, exact model, route reason, image/frame hash, transform,
  tool exchange, Jev request/answer, latency, usage, validation and stale rejection.
- Publish tested swap commands and a minimal vision/tool probe with the implementation.
- Provide `pinned` and `auto` routing modes. User pinning takes precedence; in auto
  mode code filters profiles by permissions, capabilities, availability and budget,
  then Jev chooses among eligible profiles plus abstain. A model switch increments
  the policy generation so pending results from the previous policy cannot execute.
- Define "free LLM only" separately from total pipeline cost: the existing hosted
  Jev checks still consume tokens. No unexpected paid LLM escalation is permitted.

## Virtual-controller score comparison

The swappable model is the communication/vision LLM operating a bounded Jev controller,
not a replacement for Jev's typed endpoint. Keep its tool/action contract stable.
Compare fixed-profile attempts separately from adaptive routing: an adaptive score
belongs to the routing policy, not to the last model selected.

Use identical ROM/core/start-state hashes, difficulty/player settings, observations,
control limits and attempt contracts. Run paired repeated trials in balanced order;
retain failures. Separate paused fixed-budget benchmarks, continuous full attempts,
and smoke/user-stop sessions. Publish supported HUD scores with frame/recording
evidence, trial counts and distributions alongside best scores, latency, decision age,
stale rejection, vetoes, request failures, usage and cost. Never normalize incompatible
attempt contracts into a single leaderboard.

## Cookbook work and acceptance evidence

Review live TypeSafe function-calling, extraction-cascade and verification examples.
Adapt their communication-model/typed-judgment separation rather than conflating a
language model's description with independently verified visual evidence.

Reviewed live examples:

- [SDE cascade](https://docs.typesafe.ai/cookbooks/sde_cascade.md): model IDs are
  supplied to an extraction function; narrow per-field Nouls decide escalation.
  Swap model transports/profiles while retaining the extraction/check contract.
  Its text-extraction results and example thresholds do not validate Atari vision.
- [Function calling](https://docs.typesafe.ai/cookbooks/function_calling.md): closed-set
  tool names/arguments can be batched; code consumes the selected branch. This example
  is a TypeSafe dispatcher, not itself a vision LLM tool loop. We can expose that
  bounded dispatcher as a tool to the communication model.

Thus cookbook logic is reusable across models, but image/tool wire formats, capability
support and inference latency still require per-provider adapters and tests.

Test quarter-screen tiling, resized/letterboxed windows, high DPI and fullscreen;
correct and deliberately displaced outlines; missing sprites; malformed evidence;
timeouts, unavailable profiles and stale responses. Compare the rendered boxes with
known captured pixels. Preserve failures as evidence, not only model confidence.
