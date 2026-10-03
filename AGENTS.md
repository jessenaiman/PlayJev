# PlayJev fork development

Read `docs/ATARI-TASKS.md` for the persistent iteration checklist and
`docs/HARNESS.md` before changing upstream HTML-game hooks.

- Preserve upstream's pixel-policy/harness/training paths. ROM adapters are a
  separate input/execution contract, not evidence of reproducing upstream results.
- Offline regression tests must not invoke inference services. Development integration
  defaults to **Ollaya CLI only**, using `ollaya run --format json --questions ...`.
  Never directly call Ollaya HTTP endpoints or silently substitute hosted Jev.
- Hosted TypeSafe Jev is available through an explicit provider switch only. Do not
  spend hosted quota for routine tests. Prefer local Ollaya text/vision models; propose
  hosted tests only for a measured local bottleneck and with explicit user approval.
  Keep credentials out of child CLI environments.
- Use live TypeSafe docs/cookbooks for typed-question design. Code owns clocks,
  projections, safety, score verification and execution; confidence is not proof.
- Delegate only through the OpenCode CLI using the user-requested DeepSeek v4.1
  Flash or verified free OpenCode Go models. Resolve exact model IDs and capability/
  pricing first. Every new reviewer must pass a parent-graded three-question
  TypeSafe quiz **before** inspecting the project. Do not guess IDs or silently
  delegate to paid/default models.
- Use Omarchy CLI for system-package work; never modify Omarchy core files.
- Keep ROMs, secrets, recordings and generated run evidence local and out of Git.
- Post the active checklist when switching focus. Keep `docs/ATARI-TASKS.md` open-only:
  remove tasks only with tests/artifact evidence; do not keep completed-task or past-work
  logs in documentation. Git maintains change history. Preserve local incomplete,
  failed and unranked run evidence; keep operating instructions and current limitations.
- For an authorized progress save, run `./scripts/check-in "descriptive message"`:
  one offline suite, bounded local Jev security advisory, source-only commit and push.
  Do not add release ceremonies, archived-evidence gates or repeated consent prompts.
  `atari-continuous-jev` is the user's primary branch: never merge, switch, reset or
  push `main` as part of a save point. Upstream sync is a separate requested operation.
