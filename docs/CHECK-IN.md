# One-command project save point

From `PlayJev/`:

```bash
./scripts/check-in "Describe the progress"
```

Use this when the user asks to save/check in progress; invoking it authorizes the
bounded source commit and push. No separate staging, global tool installation,
outside checkout, release packet or repeated approval is needed.

The script uses this project's `.venv/bin/python` and:

1. Checks the current branch and the user's fork, then stages changed source/docs/
   tests in its allowlisted paths. ROMs, run evidence, binaries and `.env` stay local.
   Already staged out-of-scope files or credential-shaped content stop the save;
   nothing is silently unstaged, reset or discarded.
2. Runs one offline test suite and whitespace check, then asks local Ollaya
   `kev:0.8b` typed security/message questions. The advisory is bounded to 8 seconds
   and a 6,000-character excerpt, prioritizing executable changes. Partial coverage,
   uncertainty or failed inference is disclosed, not a correctness/security certificate.
3. Commits and pushes **only** `fork/atari-continuous-jev`, then verifies its SHA.
   There is no merge, branch switch, force push, or push to `main`/upstream.

The whole command shares a 115-second subprocess budget, with at most 60 seconds
for tests; it does not run browser matrices, play games, hunt for models or delegate.
Jev warnings are advisory, not an approval loop. Deterministic credential/artifact/
test failures block the save. There is no hosted fallback or automatic retry.
Raw advisory requests/outcomes append locally to `.git/savepoint-review.jsonl`.

Optional switches:

```bash
./scripts/check-in "Describe the progress" --check-only  # source/tests preview; no staging/commit/push or inference
./scripts/check-in "Describe the progress" --model kev:0.8b  # pin the local advisory model
./scripts/check-in "Describe the progress" --no-review  # explicitly skip only the model advisory
```

Exit `0` means the requested operation succeeded; nonzero means inspect the printed
failure. If push fails, the local commit remains: rerun the same command to retry
the existing branch push without creating an empty commit. Fix test/credential
errors and rerun; the script does not clean away other work.

`atari-continuous-jev` **is the user's primary branch**. Staying in sync with upstream
is a separate, explicitly requested operation—not part of a progress save.

## Agent handoff for the remaining gameplay work

Copy this prompt into an agent session in `PlayJev/`:

```text
Read AGENTS.md, ATARI2600.md, docs/ATARI-TASKS.md, docs/DIG-DUG.md and
docs/OLLAYA-MODELS.md. Start with reliable Dig Dug controls, not a new game.
Use local Ollaya CLI only. Evaluate narrower text judgments and optional local
vision on labeled native frames; ask before an unapproved model download.
Keep model proposals distinct from pixel evidence and code-owned execution.
Measure accuracy, memory and cold/warm latency before selecting a model.
Do not weaken freshness/restart guards or silently use hosted inference.
Preserve recordings, failed attempts and exact request/action evidence locally.
Work toward pumping, supported score/game-over detection and comparable repeated
runs, then replayable procedures. Remove only validated tasks from the open list;
Git maintains change history, so do not add completed-task logs.
When I ask to save progress, use ./scripts/check-in "descriptive message";
it owns the quick checks, source staging, commit and push. Do not add ceremonies,
merge/switch branches or push main. Without a save request, do not publish.
Report any actual local bottleneck and options before asking to change providers.
```
