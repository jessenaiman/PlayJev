import io
import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw
from playjev.challenge import digest
from playjev.participation import probe_valid, score_attributable
from playjev.crackpots_score import FONT
from playjev.runtime import registry


def raster(x=40,roof=46,score='0'):
    im=Image.new('RGB',(160,210),(140,138,140));draw=ImageDraw.Draw(im)
    draw.rectangle((x,roof-22,x+6,roof-6),fill=(222,178,82))
    for left in (36,52,68,84,100,116):draw.rectangle((left,roof,left+6,roof+1),fill=(49,130,49))
    draw.rectangle((59,11,104,18),fill=(0,0,0))
    for left,d in zip((59,67,75,83,91,99),score.rjust(6)):
        if d==' ':continue
        for row,cells in enumerate(FONT[d]):
            for col,cell in enumerate(cells):
                if cell=='#':im.putpixel((left+col,11+row),(214,211,214))
    buf=io.BytesIO();im.save(buf,'PNG');return buf.getvalue()


def verified_proof(root):
    rows=[]
    for choice,x in [('noop',40),('left',32),('right',52)]:
        data=raster(x);name='control-'+choice+'.png';(root/name).write_bytes(data)
        rows.append({'choice':choice,'evidence':name,'sha256':digest(data),'before':10,'after':11,'score':0,'player_box':[x,24,x+6,40],'pot_row':46})
    return {'schema':'native-control-probe-v1','game':'crackpots','verified':True,'resumed':False,'observations':rows}


class ParticipationTests(unittest.TestCase):
    def test_native_input_effect_not_an_asserted_boolean(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);proof=verified_proof(root)
            self.assertTrue(probe_valid(root,proof))
            summary={'game':'crackpots','participation':proof}
            self.assertTrue(score_attributable(root,summary))
            self.assertFalse(score_attributable(root,{**summary,'attribution_hold':'demo disputed'}))
            self.assertFalse(score_attributable(root,{'game':'crackpots','score_verified':True}))
            (root/'control-right.png').write_bytes(b'changed')
            self.assertFalse(probe_valid(root,proof))

    def test_identical_motion_demo_score_and_path_escape_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);proof=verified_proof(root)
            for row in proof['observations']:
                data=raster(40);(root/row['evidence']).write_bytes(data);row['sha256']=digest(data)
            self.assertFalse(probe_valid(root,proof))
            proof=verified_proof(root)
            for row in proof['observations']:
                data=raster(40,score='30');(root/row['evidence']).write_bytes(data);row['sha256']=digest(data)
            self.assertFalse(probe_valid(root,proof))
            proof['observations'][0]['evidence']='../outside.png'
            self.assertFalse(probe_valid(root,proof))

    def test_final_layer_candidate_is_not_an_active_screen(self):
        profile=registry()['crackpots']
        self.assertTrue(profile.inference_ready(profile.observe(raster(40,86))))
        final=profile.observe(raster(40,94))
        self.assertFalse(profile.inference_ready(final));self.assertTrue(profile.terminal_candidate(final))
