# Read-only live reporting

Use the existing browser panels; no extra renderer library is required or installed.
The workflow diagram remains a proposal until the user's intended visual reference
and genuinely applied Dig Dug gameplay can inform it. Keep unresolved validation in
[ATARI-TASKS.md](ATARI-TASKS.md), change history in Git, and diagnostic artifacts local.

## Optional presentation references

These tagged MIT references are design options, not installed dependencies or a
claim that these are the latest available releases.

| Pinned reference | Example/API | Fit for PlayJev |
| --- | --- | --- |
| [Rich v15.0.0](https://github.com/Textualize/rich/releases/tag/v15.0.0) | [`Layout` + `Live`](https://github.com/Textualize/rich/blob/main/examples/layout.py) | Optional terminal observer, not the existing HTML `<pre>`. Borrow presentation, not random simulator data. |
| [Textual v8.2.8](https://github.com/Textualize/textual/releases/tag/v8.2.8) | [Widgets and timers](https://github.com/Textualize/textual/blob/v8.2.8/README.md) | Defer until an interactive TUI is requested. |
| [Toolong v1.4.0](https://github.com/Textualize/toolong/releases/tag/v1.4.0) | [JSONL search/live tailing](https://github.com/Textualize/toolong) | Keep detailed event logs separate from compact status. |
| [mermaid-ascii 1.6.1](https://github.com/AlexanderGrooff/mermaid-ascii/releases/tag/1.6.1) | [Flowcharts and labeled edges](https://github.com/AlexanderGrooff/mermaid-ascii) | Optional static diagrams; never run graph layout in the gameplay loop. |
| [beautiful-mermaid v1.1.2](https://github.com/lukilabs/beautiful-mermaid/releases/tag/v1.1.2) | [`renderMermaidASCII`](https://github.com/lukilabs/beautiful-mermaid/blob/v1.1.2/README.md) | Optional build-time SVG/ASCII output; tagged dependencies include `elkjs` and `entities`. |
| [ASCIIFlow v1.1.0](https://github.com/lewish/asciiflow/releases/tag/v1.1.0) | [Web editor](https://asciiflow.com/) | Optional authoring reference, not a telemetry engine or selected design. |

The user supplied ASCIIFlow, then clarified it may not be the intended diagram.
It is **not a selected design**, dependency or substitute for the still-missing reference.

## User's Jev guide

[Hugging Face community article](https://huggingface.co/blog/sora-2/jev-ai-workflows-and-use-cases-a-practical-guide-t),
published 2026-09-29 by `sora-2`/bna. It is a conceptual reference, not the authoritative
SDK/API specification; its links calling another site "official" were not adopted.
Cross-check: [TypeSafe building guide](https://docs.typesafe.ai/concepts/how-to-build-with-system-one.md)
and [confidence reference](https://docs.typesafe.ai/confidence.md).

Useful reporting boundary: **state -> typed judgment -> code policy -> bounded action
-> recorded outcome**. Show Choice confidence and alternatives as judgments, Noul as
`p(yes)`, and frame/permission/veto results as code outcomes. Confidence is not an
accuracy percentage, score proof, input authorization or a successful game.
Official API batching/latency descriptions do not describe our measured sequential
Ollaya CLI transport: its multi-question latency and local failures must stay visible.

## Current reporting contract

`playjev/metrics.py` provides compact measured analytics and a separate inferred map/
judgment view. Pending wait/source age and unknown-before-first-reply timing are
distinct. Sampled held buttons are not the last issued action; rejection reasons
and failed/cancelled outcomes remain visible. The front page collapses details and
marks saved/stopped, stalled and disconnected feeds. The game panel preserves ASCII
whitespace and receives the final snapshot. Browser validation remains pending.

Retain atomic `metrics.json` writes, text-only browser insertion and local JSONL
evidence. Outstanding presentation requirements include request/source/deadline
identity and explicit unknown score/terminal state. Source geometry or a synthetic
DOM fixture cannot certify actual compositor, touchscreen or moving-overlay behavior.

## Procedure diagram — proposal, not a played trace

Keep a fixed compact status area, a narrow workflow with a visible rejection branch,
an optional inferred-object map, and detailed probability/event logs behind a separate
view. Avoid redraw-driven simulation: only recorded or directly sampled state may
change a node. Use stable node IDs so the flow does not jump around between frames.

This schematic shows the code contract, not completed gameplay or sample run metrics.

```text
DIG-DUG / OLLAYA CLI
RESUMED PRACTICE / UNRANKED
SCORE unknown
TERMINAL unknown

CAPTURE -> ESTIMATE -> JUDGE
                        |
                   CODE GATES
                  /          \
             accept         reject
                |              |
          bounded input     release
                \              /
                    LOG / SAVE
```

### Dependency decision

**Do not add a library yet.** Our live side panels are browser `<pre>` elements, not
terminal applications. Their immediate problems are missing state and width/overflow;
Rich or Textual cannot fix those just by rendering more attractive text.

1. Keep a deterministic plain-ASCII renderer over a small shared report state for both
   browser panels; keep rendering read-only and away from inference/action timing.
2. If a terminal observer is wanted, use **Rich `Live` + `Layout` + `Text`** as an optional
   presentation dependency. Poll the same artifacts independently of gameplay. Use
   explicit refresh, plain text/no markup for external values, and ASCII-safe boxes.
3. If procedure graphs grow beyond this fixed flow, trial one Mermaid renderer at
   build time, cache its output, and test real width/edges. Do not install both Go and
   JavaScript diagram stacks or run graph layout in every capture cycle.
4. Defer Textual until an interactive TUI is requested; borrow Toolong's separate
   event-log view without adding it to gameplay requirements.
5. Treat ASCIIFlow as an optional authoring editor only. A manually drawn template
   still needs application-owned live status/evidence mapping; do not install its
   development toolchain or imply it supplies that reporting engine.

## Validation requirements

- First reply missing -> unknown, not zero; pending wait/age and capture age are distinct.
- Applied/resting/expired controls match sampled `liveButtons`, not the last proposal.
- Stale/veto/failure/cancelled outcomes are visible with evidence/request IDs; no
  fabricated "passed" nodes or fake animation progress while inference is blocked.
- Both panels preserve complete arrows/borders at 390×844, 960×540 and 1440×900;
  compact/mobile view puts hold/release/stop reason above detailed maps/probabilities.
- Saved/disconnected states are unmistakable; stopped games are not called complete.
- All reporting tests stay inference-free and preserve upstream seeded/pixel-policy tests.
- After genuinely applied Dig Dug runs exist, compare the flow with the recording
  before describing a reusable Jev gameplay procedure. Score/terminal proof is separate.
- Incorporate the user's additional references before choosing the final visual treatment.
