# Copy/paste research prompts

Project: <https://github.com/jessenaiman/PlayJev/tree/atari-continuous-jev>.
The newest iteration may still be local: ask for the current diff before reviewing it.
Return source URLs, exact versions, licenses, maintenance status and a small proposed
diff/test plan. Prefer deleting duplication over adding frameworks. No ROMs, keys or
recordings should be uploaded. Do not change global CLI/system settings.

## 1. Native pixel discovery and motion

```text
Research the smallest reliable Python tools for initial-load Atari game discovery
and classification using EmulatorJS native 160x210 PNGs. Compare Pillow-only pixel
diffs/connected components with NumPy, OpenCV and scikit-image. We need reproducible
bounded joystick probes, same-palette object candidates, starting boxes, empirical
motion bounds, identity uncertainty, terrain/tunnel estimates and calibrated HUD
glyph decoding. Dig Dug has flickering/multiplexed sprites, ghosts, rocks and soil
stripes; do not treat every color blob as a known object or elapsed time as progress.

Recommend the least dependency-heavy option that simplifies code, not the largest
vision framework. Give actual APIs, licenses/versions, expected performance with a
measurement plan, and what custom code it would replace. Include offline tests for
flicker, merged/split sprites, letterboxing, ambiguous identities and missing glyphs.
Keep exact pixel evidence distinct from classifier hypotheses. No RAM reads/writes,
ROM redistribution, hosted inference calls or invented benchmark results.
```

## 2. Emulator lifecycle, checkpoints and async execution

```text
Review approaches/packages that can simplify a Python + Playwright + EmulatorJS
Atari arcade's lifecycle and checkpoint handling. EmulatorJS loadState is queued:
restore must reach an exact canonical state hash, with setup callbacks disclosed.
Gameplay continues during inference. One subprocess/attempt is owned by a loopback
launcher; Stop must release inputs, cancel/reap CLI inference and preserve video,
last-observed evidence and compatible local checkpoints, even on failure.

Compare a small explicit state machine/asyncio design against lightweight lifecycle
libraries. Propose one shared native capture/restore/recording abstraction and typed
attempt contracts. Preserve fresh benchmark vs fresh adaptive practice vs resumed
practice cohorts, conservative frame deadlines, evidence hashes and no hidden reset.
Name code to remove, not just new abstractions. Supply an incremental migration and
offline regression plan; don't modify upstream PlayJev's pixel-training/HTML harness.
No direct Ollaya HTTP: use ollaya CLI only; hosted Jev is an explicit opt-in.
```

## 3. Typed discovery profiles and fast control

```text
Read current TypeSafe docs (https://docs.typesafe.ai/llms.txt), especially Choice,
state, function calling and extraction cascades. Design a small initial-load
discovery/classification workflow: deterministic bounded pixel probes -> typed
object-role hypotheses with unknown -> evidence-verified game profile -> fresh-frame
guarded controller. Code owns geometry, clocks, permissions and score proof. Jev
supplies typed semantic decisions; confidence is not evidence.

Local Ollaya judgments can miss Dig Dug's execution deadline; measure current
accuracy/latency before choosing a model. Compare cached typed strategy + local
servo against slow high-level target selection with fresh bounded execution, without
silently replacing Jev with an unrelated baseline. Explain honest controller/provider
attribution, invalidation when ROM/assets/profile/state changes, and fair cohorts.
Compare dataclasses vs Pydantic/msgspec only if they reduce total code. Return a
minimal architecture, exact request/response examples, a latency budget and an
offline failure/calibration test plan. Local CLI is the development default; no
hosted quota or inferred success claims. Do not propose training weights as though
discovery/classification already performs training.
```

## 4. OpenCode V2 task tracking and lightweight experiments

```text
Using only current OpenCode V2 docs (https://opencode.ai/v2/docs/), verify what native
todo/task-list support actually exists in the installed version. This agent session
currently exposes no todo tool, and the published V2 API has no todo route/schema.
Do not invent V1 endpoints or claim a Markdown checklist is a native task update.

Find a supported minimal way to maintain ordered open tasks with pending/in-progress/
blocked status, acceptance criteria and local artifact links. Remove validated tasks;
Git maintains change history, so do not add completed-task archives or work logs.
Compare native capabilities, maintained plugins, plain Markdown and small local
JSON/SQLite tracking; preserve the project checklist as a source of truth rather
than maintaining conflicting copies. Provide verified APIs/install/configuration
requirements and a reversible integration plan. Separately suggest lightweight
local experiment/provenance tools only when they simplify this arcade. No automatic
plugin installation, global configuration edits, delegation or paid-model calls.
```

## Reply format

```text
1. Verified options (package/version/license/source URL).
2. Recommended smallest change and why.
3. Existing modules/duplicate code replaced or removed.
4. Minimal example/diff and offline acceptance tests.
5. Tradeoffs, unresolved facts and what must be measured locally.
```
