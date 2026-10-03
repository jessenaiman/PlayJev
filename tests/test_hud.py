import io
import unittest
from PIL import Image
from playjev.hud import FONT, digit_grids, assemble, request_for


class HudTests(unittest.TestCase):
    def raster(self, text, top=12):
        im=Image.new('RGB',(160,210))
        for i,digit in enumerate(text):
            for row,cells in enumerate(FONT[digit]):
                for col,cell in enumerate(cells):
                    if cell=='#':
                        for x in range(4+i*16+col*4,8+i*16+col*4):
                            im.putpixel((x,top+row*2),(30,150,30))
        buf=io.BytesIO();im.save(buf,'PNG');return buf.getvalue()

    def test_read_shifted_interlaced_hud(self):
        for top in (10,12):
            self.assertEqual(digit_grids(self.raster('1640',top)),[FONT[c] for c in '1640'])

    def test_choice_cannot_override_pixels(self):
        grids=[FONT[c] for c in '1640']
        def response(text):
            return {'answers':{f'digit_{i}':{'choice':c,'confidence':1,'probabilities':{k:float(k==c) for k in request_for(grids)['questions'][f'digit_{i}']['criteria']}} for i,c in enumerate(text)}}
        self.assertEqual(assemble(grids,response('1640'))['value'],1640)
        self.assertIsNone(assemble(grids,response('1648'))['value'])

    def test_unknown_and_blank_not_invented(self):
        self.assertEqual(len(request_for([FONT['0']])['questions']),1)
