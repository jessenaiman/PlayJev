import io
import unittest
from PIL import Image, ImageDraw
from playjev.digdug_score import FONT, digit_grids
from playjev.execution import FrameStamp
from playjev.hud import read_score, LiveScore


def hud(text):
    im=Image.new('RGB',(160,210));ImageDraw.Draw(im).rectangle((12,3,147,18),fill=(60,60,180))
    for i,d in enumerate(text.rjust(6)):
        if d==' ':continue
        for row,pattern in enumerate(FONT[d]):
            for col,c in enumerate(pattern):
                if c=='#':im.putpixel((100+i*8+col,181+row),(198,105,57))
    return im


def png(im):
    buf=io.BytesIO();im.save(buf,'PNG');return buf.getvalue()


class DigDugScoreTests(unittest.TestCase):
    def test_partial_font_reads_labeled_digits_and_rejects_unknown_and_title(self):
        for value in (0,10,20,30,330):self.assertEqual(read_score('dig-dug',png(hud(str(value)))),value)
        im=hud('30');im.putpixel((140,181),(198,105,57))
        self.assertIsNone(read_score('dig-dug',png(im)))
        im=hud('30');ImageDraw.Draw(im).rectangle((12,3,147,18),fill=(0,0,0))
        self.assertIsNone(read_score('dig-dug',png(im)))
        self.assertTrue(all(not any('#' in r for r in grid) for grid in digit_grids(png(im))))

    def test_live_score_needs_independent_matching_captures(self):
        score=LiveScore()
        self.assertIsNone(score.observe(30,FrameStamp(10,12,'a'),'a.png')['score'])
        self.assertIsNone(score.observe(30,FrameStamp(12,13,'b'),'b.png')['score'])
        result=score.observe(30,FrameStamp(14,15,'c'),'c.png')
        self.assertEqual((result['score'],result['best_supported_score']),(30,30))
        self.assertEqual([r['evidence'] for r in result['score_evidence']],['b.png','c.png'])
        result=score.observe(None,FrameStamp(16,17,'d'),'d.png')
        self.assertIsNone(result['score']);self.assertEqual(result['best_supported_score'],30)
