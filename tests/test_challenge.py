import asyncio
import io
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from PIL import Image
from playjev.challenge import BaselinePlayer, ComposedJevPlayer, GatedJevPlayer, DefenderJevPlayer, Freeway, GAMES, compare, replay_html, validate_run
from playjev.scoreboard import build, eligible
from playjev.invaders import geometry, motion


class ChallengeTests(unittest.TestCase):
    def test_geometry_keeps_player_and_counts_aliens(self):
        im = Image.new("RGB", (160, 210))
        for x in range(6):
            for y in range(6):
                for dx in range(6):
                    for dy in range(6):
                        im.putpixel((20 + x*16 + dx, 30+y*18+dy), (132,130,24))
        for x in range(75,82):
            for y in range(185,193):
                im.putpixel((x,y), (49,130,49))
        im.putpixel((122,196), (165,130,58))  # lower boundary marker is not a life-loss glyph
        buf = io.BytesIO()
        im.save(buf, "PNG")
        g = geometry(buf.getvalue())
        self.assertEqual(g["alien_count"], 36)
        self.assertEqual(len(g["columns"]), 6)
        self.assertIsNotNone(g["player"])
        self.assertFalse(g["life_indicator_visible"])

    def test_laser_motion_separates_enemy_from_own_shot(self):
        before = {"projectiles": [{"box":[40,150,40,157]}, {"box":[80,160,80,169]}]}
        after = {"projectiles": [{"box":[40,156,40,163]}, {"box":[80,145,80,154]}]}
        tracks = motion(before,after,6)
        self.assertEqual([t["direction"] for t in tracks], ["down","up"])
        self.assertEqual(tracks[0]["vy"],1)

    def test_gates_time_movement_and_guard_edge(self):
        from unittest.mock import AsyncMock
        def answer(choice, options):
            return {"choice": choice, "confidence": 1,
                    "probabilities": {k: float(k == choice) for k in options}}
        current = {"player": {"box": [143,185,149,194]}, "columns": [{"id":"column_0", "x":148,"remaining":3,"lowest_y":100}],
                   "projectiles": [], "aliens": [], "alien_count":3}
        player = GatedJevPlayer()
        player.request = AsyncMock(return_value={"answers": {
            "threat": answer("danger", ("danger","safe")),
            "dodge": answer("right", ("left","right","stay")),
            "target": answer("column_0", ("column_0","hold")),
            "trigger": answer("fire", ("fire","release"))}})
        d = asyncio.run(player.decide({"current":current, "game_frame":0,"action_frames":30}, GAMES["space-invaders"]))
        self.assertEqual(d["guard"], "screen-edge-frame-cap")
        self.assertLess(d["movement_frames"], 30)
        self.assertEqual(d["rest_choice"], "fire")

    def test_composed_controls(self):
        from unittest.mock import AsyncMock
        for direction in ("left", "right", "stay"):
            for trigger in ("fire", "release"):
                def answer(choice, options):
                    return {"choice": choice, "confidence": 0.8,
                            "probabilities": {k: float(k == choice) for k in options}}
                player = ComposedJevPlayer()
                player.request = AsyncMock(return_value={"answers": {
                    "movement": answer(direction, ("left", "right", "stay")),
                    "trigger": answer(trigger, ("fire", "release"))}})
                decision = asyncio.run(player.decide({}, GAMES["space-invaders"]))
                expected = ([] if direction == "stay" else [direction]) + (["fire"] if trigger == "fire" else [])
                self.assertEqual(decision["choice"], "+".join(expected) or "noop")
                self.assertIn(decision["choice"], GAMES["space-invaders"].actions)
                self.assertEqual(player.request.await_count, 1)

    def test_composed_rejects_bad_components(self):
        with self.assertRaises(ValueError):
            ComposedJevPlayer.validate_choice({"choice": "reset"}, {"left": "", "right": ""})
        with self.assertRaises(ValueError):
            asyncio.run(ComposedJevPlayer().decide({}, GAMES["freeway"]))

    def test_actions(self):
        self.assertEqual(set(GAMES), {"space-invaders", "freeway", "defender", "crackpots"})
        for game in GAMES.values():
            decision = asyncio.run(BaselinePlayer("fixed").decide({}, game))
            self.assertIn(decision["choice"], game.actions)

    def test_freeway_excludes_gray_road(self):
        im = Image.new("RGB", (160, 210), (140, 140, 140))
        for x in range(40, 46):
            for y in range(170, 177):
                im.putpixel((x, y), (250, 230, 20))
        buf = io.BytesIO()
        im.save(buf, "PNG")
        regions = Freeway().observation(buf.getvalue(), "regions")["foreground_regions"]
        self.assertEqual(len(regions), 1)
        self.assertEqual(regions[0]["box"], [40, 170, 45, 176])

    def test_bad_settings(self):
        for count in (0, 61, 1.5):
            with self.assertRaises(ValueError):
                validate_run(Namespace(player="jev", observation="regions", action_frames=count, speed=0.25, watch_delay=0))

    def test_defender_reuses_gate_contract(self):
        from unittest.mock import AsyncMock
        game = GAMES["defender"]
        player = DefenderJevPlayer()
        player.request = AsyncMock(return_value={"answers":{
            "movement":{"choice":"up-right","confidence":0.9,"probabilities":{k:float(k=="up-right") for k in ["stay",*game.directions]}},
            "trigger":{"choice":"fire","confidence":1,"probabilities":{"fire":1,"release":0}}
        }})
        d = asyncio.run(player.decide({},game))
        self.assertEqual(d["choice"],"up-right+fire")
        self.assertEqual(game.actions[d["choice"]],[4,7,0])

    def test_scoreboard_requires_unchanged_evidence_and_separates_games(self):
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            paths=[]
            for game in ("defender","space-invaders"):
                p=Path(tmp)/game
                p.mkdir()
                (p/"final.png").write_bytes(b"evidence")
                row=dict(game=game,challenge_id=game,status="complete",game_frames=60,budget_frames=60,
                         score=100,score_verified=True,score_review={"evidence":"final.png","evidence_sha256":hashlib.sha256(b"evidence").hexdigest()},config={"player":"jev-gates"})
                (p/"summary.json").write_text(json.dumps(row))
                self.assertTrue(eligible(p,row))
                paths.append(p)
            output=Path(tmp)/"board"
            build(paths,output)
            groups=json.loads((output/"scores.json").read_text())
            self.assertEqual(len(groups),2)
            (paths[-1]/"final.png").write_bytes(b"changed")
            self.assertFalse(eligible(paths[-1],row))

    def test_offline_replay_escapes_scripts(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            replay_html(directory, {"question": "</script><script>bad()"}, [])
            self.assertNotIn("</script><script>bad()", (directory / "replay.html").read_text())

    def test_unverified_and_incomplete_not_ranked(self):
        from contextlib import redirect_stdout
        with tempfile.TemporaryDirectory() as tmp:
            paths = []
            for i, (complete, verified) in enumerate(((True, True), (True, False), (False, True))):
                path = Path(tmp) / str(i)
                path.mkdir()
                row = dict(challenge_id="same", status="complete" if complete else "incomplete",
                           game_frames=60, budget_frames=60, score_verified=verified, score=10,
                           score_candidate=10, config={})
                (path / "summary.json").write_text(json.dumps(row))
                paths.append(path)
            output = io.StringIO()
            with redirect_stdout(output):
                compare(Namespace(runs=paths))
            self.assertEqual(output.getvalue().count("Unranked:"), 2)
            self.assertIn("1. 10", output.getvalue())


if __name__ == "__main__":
    unittest.main()
