import math
import unittest
from playjev.spatial import evidence


class SpatialTests(unittest.TestCase):
    def test_letterbox_and_window_offset(self):
        canvas={'left':960,'top':540,'width':640,'height':377}
        content={'left':1029,'top':540,'width':503,'height':377}
        e=evidence({'player':{'box':[30,24,36,40]}},canvas,content=content)
        self.assertEqual(e['projected_player_box'],[1029+30/160*503,540+24/210*377,
                                                  1029+37/160*503,540+41/210*377])
        self.assertTrue(e['code_bounds_valid'])

    def test_invalid_box_and_rect(self):
        canvas={'left':0,'top':0,'width':640,'height':480}
        for box in ([30,24,20,40],[-1,0,5,5],[0,0,160,210],[0,0,math.nan,5]):
            self.assertFalse(evidence({'player':{'box':box}},canvas)['code_bounds_valid'])
        for content in ({'left':-1,'top':0,'width':100,'height':100},
                        {'left':0,'top':0,'width':641,'height':480},
                        {'left':math.nan,'top':0,'width':640,'height':480}):
            self.assertFalse(evidence({},canvas,content=content)['code_bounds_valid'])
