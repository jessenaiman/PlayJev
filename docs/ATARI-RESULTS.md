# Reviewed Atari test results

Local high-score board: `runs/scoreboard/index.html`. Rebuild it with
`.venv/bin/python -m playjev.challenge leaderboard` from `PlayJev/`.

| Game | Observed high score | Game budget | Player | Result / replay |
| --- | ---: | ---: | --- | --- |
| Space Invaders | 1,640 | 120 seconds | `jev-gates` | First wave visually verified; `runs/first-wave-laser-gates-v3/replay.html` |
| Defender | 1,750 | 30 seconds | `jev-gates` / `DefenderJevPlayer` | Single attempt; `runs/defender-jev-gates-v2/replay.html` |

Both scores were visually reviewed by the assistant. They are **not** human-approved
or comparable across games/budgets. Space Invaders' score evidence is `final.png`;
Defender's is `frame-0053.png` (27 game seconds), with the same score at the end.
The leaderboard checks the evidence hash and links to the full replay and logs.

Defender ran 1,800 actual emulator frames: 56 hosted API requests and four explicit
terminal-hold decisions. The game-over color cycle was detected at frame 1,680;
the executed segment log verifies that all subsequent controls were `noop`.

An earlier Defender trial reached 1,750 then accidentally restarted through the
ordinary fire button. It is retained as `runs/defender-jev-gates-v1`, marked invalid
and excluded from ranking. Failed/incomplete and unreviewed older tests are also
retained and displayed unranked, not silently discarded.

The successful Space Invaders policy is saved under Git tag `atari-first-wave-v1`.
Defender tests extend the same frame runner, saved-state validation, recording and
scoring interfaces. They add ROM-specific observations and two-dimensional joystick
composition; they do not establish that Space Invaders' laser perception generalizes.

ROMs, API secrets and generated recordings are not committed. Keep `runs/` on disk
or back it up separately; the Git checkpoint alone does not include those artifacts.
