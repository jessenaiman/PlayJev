# Ollaya-first text and vision operation

Use **Ollaya CLI** for gameplay discovery/classification/control and check-ins.
Do not call Ollaya HTTP endpoints directly. Keep each attempt provider/model pinned;
model confidence is not role, score, terminal or action proof.

## Inspect before choosing

```bash
ollaya --version
ollaya list
ollaya ps
ollaya show kev:0.8b
ollaya run --help
```

`kev:0.8b` and the local `oc-instruction:latest` derivative are text decision models.
Do not infer image support from a name: verify capabilities and the model contract.
[`decider:2b-vision`](https://ollaya.dev/library/decider:2b-vision) is a separate
vision-capable model, not an installed/default PlayJev controller. Registry weights
are about 4.4 GB; inference requires additional memory. Check disk/device capacity
before choosing to download. Downloads and model probes are not offline regression.

## Optional local vision probe — manual, not gameplay

If you choose this download and have adequate capacity:

```bash
ollaya pull decider:2b-vision
ollaya show decider:2b-vision
ollaya run decider:2b-vision --image runs/dig-dug-tunnel-v1/start.png \
  --format json --questions '{"player_visible":{"type":"noul","instructions":"Is the purple miner player visibly present in this native Dig Dug game frame?"}}' \
  "This is a native Atari Dig Dug frame. Judge only the supplied image."
```

Use your own preserved emulator-only PNG, not a desktop screenshot. CLI `--image`
supports one PNG per request; the model has up to ten options per question. It
returns typed decisions, not arbitrary captions or sprite boxes. For localization,
code supplies candidate regions/crops and bounded choices, including unknown.

PlayJev's current Ollaya transport sends structured text, **not images**. Passing
`--model decider:2b-vision` to it does not add image input. Image/hash/frame-envelope
integration and labeled calibration are open tasks, not an enabled controller.
The check-in tool reviews text diffs and likewise does not need image input.

## Evaluate locally before escalating

1. Compare labeled text/vision cases, including absent, flickering, occluded and
   wrong-role negatives. Retain raw answers and expected labels; never activate
   a profile from confidence alone.
2. Measure cold-load and warm latency, decision age, memory, allocation failures,
   truncation and semantic error rate on this machine. Registry benchmarks are not
   Dig Dug calibration or a guarantee of fitting our execution deadline.
3. Try narrower state/questions, another verified local model and an explicitly
   configured local device. Separate slow semantic planning from fresh-frame code
   only with disclosed attribution; stale proposals still cannot execute.
4. A real bottleneck is reproducible failure to meet the needed accuracy/freshness
   contract, or resource/feature limits after reasonable local adjustments. Record
   the evidence and options, then ask before a hosted provider test or switch.

No timeout, memory failure or weak answer permits automatic hosted fallback.
Keep regression tests mocked/inference-free and all model probes explicitly bounded.
See [open tasks](ATARI-TASKS.md), [routing](VISION-ROUTING.md) and
[Ollaya's CLI reference](https://ollaya.dev/docs/cli).

## Question format versus model behavior

The installed CLI reports version **0.9.0**. It accepts the same question objects
as Jev: `type`, `instructions`, `criteria`. Choice criteria are a label/description
object, Score criteria are ordered levels, and Noul criteria use `true`/`false`.
Structured descriptions are valid; they are not evidence of equivalent accuracy.

Jev receives `{model, state, questions}` as one request. The CLI receives the model
as an argument, the question map via `--questions`, and state via stdin or an
argument (`--state-json` for a JSON object/array). `--questions` does not take the
whole Jev request envelope. The current Crackpots policy file contains template
values, not a directly runnable question map; that limitation is on the open checklist.

CLI JSON includes native timings/routing/truncation fields beyond the common
`model`, `answers`, `usage`. Local model names/limits/calibration differ; no implicit
hosted fallback is allowed. Ollaya documentation describes normalized-top confidence
for Score, while current Jev docs describe distance-aware Score confidence; do not
share Score thresholds blindly. Choice confidence uses the same documented formula.

The local adapter's serial splitting of questions is an application choice, not a
format requirement. Neither matching JSON nor the cookbook's hosted performance
numbers prove that `kev:0.8b` can select Atari intercepts. See
[compatibility](https://ollaya.dev/docs/typesafe-compatibility),
[question shapes](https://docs.typesafe.ai/sdk/python/api/types/questions.md) and
[confidence](https://docs.typesafe.ai/confidence.md).
