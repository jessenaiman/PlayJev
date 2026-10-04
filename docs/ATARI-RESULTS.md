# Score evidence and comparisons

Local high-score board: `runs/scoreboard/index.html`. Rebuild it with
`.venv/bin/python -m playjev.challenge leaderboard` from `PlayJev/`.

The generated board/front page is the source of reviewed scores and replay links;
do not copy scores, trial counts or completed-run summaries into documentation.
The verifier checks the selected score image hash. Support and ranking eligibility
are separate: an observed HUD can be valid while an incomplete/practice run is unranked.

Compare only matching game/challenge/playback contracts. Keep paused calibration,
capped smoke runs, fresh/resumed practice and natural-end evaluation separate.
Retain failed or accidentally restarted attempts unranked; never silently discard
them or treat a stop, empty screen, elapsed budget or model confidence as completion.
Unknown scores stay unknown. Dig Dug's partial HUD font reports supported observed
values with coverage disclosed; full HUD/terminal/stage calibration remains pending.
Scorecards include model handles and recorded input/output/total tokens. Missing
usage is unknown or a marked lower bound; never treat it as a free winning attempt.
See [arcade cost scope and local event files](ARCADE.md#local-arcade-records-and-token-costs).

ROMs, API secrets and generated recordings are not committed. Keep `runs/` on disk
or back it up separately; Git history does not include those artifacts.
