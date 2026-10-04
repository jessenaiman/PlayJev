# Jev gameplay examples

These examples are the question files used by the Atari adapter, not alternate
providers or simulated high scores. Use local Ollaya CLI. States here are illustrative
source fixtures; recordings, responses and observed outcomes belong in local `runs/`.
Question output alone does not establish improved gameplay or a stage clear.

## Use from the browser — no imports

Open http://127.0.0.1:8765/, select **Jev · hosted**, then click **Start Crackpots**.
The server must already have its TypeSafe credential configured; never put it in
the page or question JSON. Provider selection applies only to the next attempt,
and the recorded run keeps its provider/model. Hosted use consumes API quota;
it is explicit, never a fallback after a local failure. Both providers use the
same recipe JSON. The local CLI examples below need no Python imports.

## 1. State: separate observations from option definitions

Source: https://docs.typesafe.ai/concepts/state

`playjev/crackpots_state.py` supplies current pot/intercept facts under `state.pots`.
`playjev/recipes/crackpots-lane.json` defines what each option means. No adapter
import is required to run the same question schema directly:

```sh
ollaya run kev:0.8b --format json --state-json \
  --questions @playjev/recipes/crackpots-lane.json \
  < experiments/jev-gameplay/01-state.json
```

The illustrated decision has an estimated catch at `pot_2`; waiting for
`ready_to_drop` would miss the required positioning step. Compare the actual answer
against that evidence. To observe execution, start one fresh Crackpots attempt from
the arcade at http://127.0.0.1:8765/. Inspect its end report and native frames; a
no-op-heavy replay or an uncleared wave remains a failure.

## Architecture

```text
Native frame
    |
    v
crackpots.py                    geometry, motion, interception estimates
    |
    v
crackpots_state.py              named observations, no question definitions
    |
    v
crackpots_player.py <---------- recipes/crackpots-lane.json
    |                          policies/crackpots.json (state configuration)
    v
transports.py -> Ollaya CLI     exact requests and typed responses recorded
    |
    v
crackpots_player.py             validate answer, resolve an available target
    |
    v
crackpots_control.command       deterministic bounded input proposal
    |
    v
crackpots_control.prepare       re-observe alignment/intercept; veto stale drops
    |
    v
execution.py -> Emulator        freshness, release rules, bounded execution

Saved run -> completion.py -> loss_review.py
             audit only       evidence-linked improvement handoff
```

`runtime.py` registers these hooks; it does not build tactical questions.
`live.py` runs the clock and records source hashes for each layer. Startup,
completion and improvement review remain outside the gameplay player. Future
Score/Noul composition belongs in dedicated tactical modules, not in perception
or the emulator execution loop. Each new implementation needs an updated diagram.

## 2. Score: grade pursuit evidence on eligible candidates

Sources: https://docs.typesafe.ai/primitives/score and the shortlist/ranking
decomposition in https://docs.typesafe.ai/cookbooks/rerank_typesafe. The latter uses
Noul for legal-passage relevance; this implementation uses ordered Score levels
for pursuit evidence, not the cookbook's question or claimed accuracy.

```sh
ollaya run kev:0.8b --format json --state-json \
  --questions @playjev/recipes/crackpots-quality.json \
  < experiments/jev-gameplay/02-score.json
```

Code shortlists at most two positive estimated intercepts by catch count, approach
time and label. `crackpots_quality.py` grades their evidence independently on the
same ordered scale, then ranks their fractional scores. `judgments.py` validates
the score/mean relationship and preserves the original legend, distribution and
provider-reported confidence. A tactical Score is not a HUD score or catch proof.
`judgment_display.py` renders the typed result read-only in the live ASCII panel;
Score answers are never forced into a Choice label to satisfy the display.
The shortlist may omit useful candidates; all original pot facts remain in the
recorded state. No estimated intercept means code chooses hold/scan with zero
inference usage; this is explicitly labeled, never fabricated as a model reply.

The active mode is `quality` in `playjev/policies/crackpots.json`. Set it explicitly
to `lane` for the baseline Choice recipe. This mode switch does not change providers.
The Crackpots runtime explicitly selects batched CLI question execution; other
profiles and independent lifecycle/review transports retain serial execution.
The Score model view includes only shortlisted candidates and their relevant
bug tracks. Full pot observations remain in each decision's `observations` field.
Actual latency and stale rejection must be observed before claiming usefulness;
neither a compact state nor batching permits weakening the frame deadline.

```text
Native frames -> crackpots.py -> crackpots_state.py
                                      |
                             crackpots_player.py
                                      |
                  policy.tactical_mode chooses ONE implementation
                         /                            \
             crackpots_lane.py               crackpots_quality.py
             Choice recipe                   shortlist + compact model view
                                             + Score recipe
                         \                            /
                           transports.py -> Ollaya CLI
                                      |
                              judgments.py validates
                                      |
                         selected target + raw judgments
                                      |
                 crackpots_control.py -> execution.py -> Emulator

Saved run -> completion.py -> loss_review.py (separate lifecycle/report workflows)
```
