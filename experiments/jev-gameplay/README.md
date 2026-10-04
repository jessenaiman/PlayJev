# Jev gameplay examples

These examples are the question files used by the Atari adapter, not alternate
providers or simulated high scores. Use local Ollaya CLI. States here are illustrative
source fixtures; recordings, responses and observed outcomes belong in local `runs/`.
Question output alone does not establish improved gameplay or a stage clear.

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
