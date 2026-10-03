# Space Invaders first-wave checkpoint

The visible, hosted-Jev `jev-gates` run cleared the first wave on 2026-10-03.

- Run: `runs/first-wave-laser-gates-v3/`
- Challenge: `runs/first-wave-120s/`, 7,200 emulator frames (120 game seconds).
- Completed all 7,200 frames, with 444 hosted API decisions.
- Live speed: 0.5x; nominal actions 30 frames, reduced to 12 near low lasers.
- Last alien: `frame-0235.png`, 63.7 game seconds.
- Empty field: `frame-0237.png` and `frame-0238.png`, 64.1 and 64.6 seconds.
- Fresh wave: `frame-0240.png`, 65.6 seconds.
- Replay transition: approximately 212–221 wall/video seconds.
- Stage evidence was visually reviewed by the assistant, not self-certified by Jev.

The policy combines threat, dodge, firing-lane and trigger Choice judgments.
Laser movement is measured over six actual emulator frames. Local code computes
collision candidates, vetoes unsafe escape choices using Jev's safe-choice
probabilities, and times alignment without crossing screen boundaries.

The successful source bytes before adding Defender:

```text
playjev/challenge.py SHA256 07e57ff03e8554041865b3913c54194c1f69df556489c1bb975bdcee5b03c247
playjev/invaders.py  SHA256 b0c3997218d5d687e60d36eb69f5248404e4a79680ef8751a25dfe0dcd8faa9d
```

The code is saved in the `atari-first-wave-v1` Git tag. Run artifacts remain on disk
under the ignored `runs/` directory; they are **not** included in Git. Preserve that
directory separately for the video, exact requests/responses, challenge states and
screenshots. No ROMs or API secrets are included in this checkpoint.

## Reproduce visibly

```bash
.venv/bin/python -m playjev.challenge run runs/first-wave-120s --player jev-gates --visible --speed 0.5 --action-frames 30 --watch-delay 0.1
```

Model responses can vary. This is evidence of one successful run, not a promise of
success on every retry. No random policy, mid-run restoration, RAM modification,
reset, extra-life hack or native emulator was used.
