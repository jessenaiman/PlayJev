import asyncio
import io
import unittest
from unittest.mock import AsyncMock
from PIL import Image
from playjev.crackpots import geometry, tracks, interception, guard, CrackpotsPlayer
from playjev.challenge import GAMES
from playjev.crackpots_score import FONT, digit_grids
from playjev.hud import assemble, request_for


class CrackpotsTests(unittest.TestCase):
    def test_windows_and_bricks_not_bugs(self):
        im=Image.new('RGB',(160,210),(140,138,140))
        for x in range(30,37):
            for y in range(24,41):im.putpixel((x,y),(222,178,82))
        for left in (36,52,68,84,100,116):
            for x in range(left,left+7):
                for y in range(46,48):im.putpixel((x,y),(49,130,49))
            for x in range(left,left+8):
                for y in range(68,76):im.putpixel((x,y),(0,0,0))
        for y in range(100,108):
            for x in range(80,88):
                if y in (103,104) or x in (82,85):im.putpixel((x,y),(0,0,0))
        buf=io.BytesIO();im.save(buf,'PNG');g=geometry(buf.getvalue())
        self.assertEqual(len(g['pots']),6)
        self.assertEqual(len(g['bugs']),1)
        self.assertEqual(g['window_y'],76)
        self.assertIsNotNone(g['player'])

    def test_bug_motion_and_intercept(self):
        previous={'bugs':[{'box':[80,130,87,137],'color':'black'}]}
        current={'bugs':[{'box':[80,127,87,134],'color':'black'}],
                 'player':{'box':[80,24,86,40]},'pots':[{'box':[80,46,86,47]}],
                 'pot_row':46,'window_y':76}
        current['bug_tracks']=tracks(previous,current,12)
        self.assertEqual(current['bug_tracks'][0]['vy'],-0.25)
        px,lanes=interception(current)
        self.assertLessEqual(lanes[0]['intercepts'][0]['horizontal_miss'],1)
        self.assertTrue(lanes[0]['intercepts'][0]['before_window'])
        self.assertTrue(guard({'player':None},'fire'))

    def test_gate_composition(self):
        current={'player':{'box':[30,24,36,40]},'pots':[{'box':[36,46,42,47]}],
                 'bugs':[],'bug_tracks':[],'pot_row':46,'window_y':76}
        p=CrackpotsPlayer()
        def answer(choice,options):return {'choice':choice,'confidence':1,'probabilities':{k:float(k==choice) for k in options}}
        p.request=AsyncMock(return_value={'answers':{'lane':answer('pot_0',['pot_0','hold','scan']),
                                                    'drop':answer('release',['fire','release'])}})
        d=asyncio.run(p.decide({'current':current},GAMES['crackpots']))
        self.assertEqual(d['choice'],'right')
        self.assertLessEqual(d['movement_frames'],26)

    def test_activision_hud_and_six_digit_assembly(self):
        im=Image.new('RGB',(160,210))
        for left,digit in zip((83,91,99),'690'):
            for row,cells in enumerate(FONT[digit]):
                for col,cell in enumerate(cells):
                    if cell=='#':im.putpixel((left+col,11+row),(214,211,214))
        buf=io.BytesIO();im.save(buf,'PNG');grids=digit_grids(buf.getvalue())
        choices=['blank']*3+list('690')
        response={'answers':{f'digit_{i}':{'choice':c,'confidence':1,'probabilities':{k:float(k==c) for k in request_for(grids,FONT)['questions'][f'digit_{i}']['criteria']}} for i,c in enumerate(choices)}}
        self.assertEqual(assemble(grids,response,FONT)['value'],690)
        grids[-2][0]='......'
        self.assertFalse(assemble(grids,response,FONT)['accepted'])
