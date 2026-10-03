import io
import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw
from playjev.digdug import geometry, candidates, prepare, track, collect
from playjev.challenge import GAMES


def raster(player=(76,87,82,97)):
    im=Image.new('RGB',(160,210));d=ImageDraw.Draw(im)
    d.rectangle(player,fill=(189,146,255))
    d.rectangle((98,87,105,97),fill=(231,146,90))
    d.rectangle((16,181,19,187),fill=(198,105,57))
    buf=io.BytesIO();im.save(buf,'PNG');return buf.getvalue()


class DigDugTests(unittest.TestCase):
    def test_native_roles_tunnel_candidates_and_unknown_score(self):
        g=geometry(raster())
        self.assertEqual(g['player']['box'],[76,87,82,97])
        self.assertTrue(g['active_play_evidence']);self.assertEqual(len(g['enemies']),1)
        self.assertIsNone(g['score']);self.assertIsNone(g['rocks'])
        self.assertIn('right+fire',candidates(g));self.assertNotIn('fire',candidates(g))
        g['facing']='right';self.assertIn('fire',candidates(g))

    def test_intro_and_missing_player_cannot_fire_or_reset(self):
        intro=geometry(raster((130,5,136,15)))
        self.assertFalse(intro['active_play_evidence']);self.assertEqual(list(candidates(intro)),['noop'])
        self.assertTrue(prepare(intro,{'choice':'fire'})[2])
        active=geometry(raster());active['player']=None
        self.assertTrue(prepare(active,{'choice':'right+fire'})[2])
        for buttons in GAMES['dig-dug'].actions.values():self.assertNotIn(3,buttons)

    def test_tracking_facing_and_execution_recheck(self):
        a,b=geometry(raster()),geometry(raster((78,87,84,97)))
        track(a,b,4);self.assertEqual(b['facing'],'right')
        decision={'choice':'right+fire','movement_frames':30}
        self.assertEqual(prepare(b,decision)[1:],(14,False))
        b['enemies']=[];self.assertTrue(prepare(b,decision)[2])

    def test_soil_blocks_pump_estimate(self):
        g=geometry(raster());g['terrain']['grid']=['.'*16]*19
        self.assertNotIn('right+fire',candidates(g))

    def test_uncalibrated_hud_collector_never_fabricates_score(self):
        import asyncio
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'summary.json').write_text('{"game":"dig-dug","status":"stopped"}')
            (p/'decisions.jsonl').write_text('')
            asyncio.run(collect(p));row=json.loads((p/'summary.json').read_text())
            self.assertIsNone(row['score']);self.assertFalse(row['score_verified'])
