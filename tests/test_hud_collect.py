import asyncio
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from PIL import Image
from playjev.challenge import digest
from playjev.hud import FONT, collect


def raster():
    im=Image.new('RGB',(160,210))
    for i,digit in enumerate('1640'):
        for row,cells in enumerate(FONT[digit]):
            for col,cell in enumerate(cells):
                if cell=='#':
                    for x in range(4+i*16+col*4,8+i*16+col*4):im.putpixel((x,12+row*2),(30,150,30))
    buf=io.BytesIO();im.save(buf,'PNG');return buf.getvalue()


class HudCollectionTests(unittest.TestCase):
    def check_case(self,intervals):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);data=raster();rows=[]
            for i,(before,after) in enumerate(intervals):
                name=f'frame-{i:04}.png';(p/name).write_bytes(data)
                rows.append({'evidence':name,'before':before,'after':after,'sha256':digest(data)})
            (p/'final.png').write_bytes(data)
            (p/'frames.jsonl').write_text('\n'.join(json.dumps(row) for row in rows))
            (p/'decisions.jsonl').write_text('')
            (p/'summary.json').write_text(json.dumps({'game':'space-invaders','status':'stopped','score':None,'score_verified':False,
                'config':{'provider':'jev','model':'jev-latest'}}))
            with patch('playjev.challenge.JevPlayer.request',new=AsyncMock(side_effect=AssertionError('No inference in default HUD scoring'))) as request:
                asyncio.run(collect(p));request.assert_not_awaited()
            report=json.loads((p/'hud-jev.json').read_text());summary=json.loads((p/'summary.json').read_text())
            self.assertTrue(report['duplicate_final_excluded']);self.assertEqual(report['unique_requests'],0)
            return report,summary

    def test_duplicate_final_cannot_supply_repeat(self):
        report,summary=self.check_case([(10,11)])
        self.assertIsNone(report['highest_supported_score']);self.assertFalse(summary['score_verified'])

    def test_identical_pixels_at_independent_frames_support_score(self):
        report,summary=self.check_case([(10,11),(12,13)])
        self.assertEqual(summary['score'],1640);self.assertTrue(summary['score_verified'])

    def test_overlapping_capture_intervals_do_not_supply_repeat(self):
        report,summary=self.check_case([(10,12),(12,14)])
        self.assertIsNone(summary['score']);self.assertFalse(summary['score_verified'])
