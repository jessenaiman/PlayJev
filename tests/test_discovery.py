import asyncio
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from PIL import Image, ImageDraw
from playjev.challenge import digest
from playjev.discovery import TRACE, ROLES, objects, pixel_change, displacement, classify, verify_discovery, verified_profile
from playjev.native import capture
from playjev.transports import SafetyHold


def raster(x=76):
    im=Image.new('RGB',(160,210));d=ImageDraw.Draw(im)
    d.rectangle((x,87,x+6,97),fill=(189,146,255))
    d.rectangle((98,87,105,97),fill=(231,146,90))
    d.rectangle((16,181,19,187),fill=(198,105,57))
    buf=io.BytesIO();im.save(buf,'PNG');return buf.getvalue()


def fixture(directory):
    data=raster();(directory/'start.png').write_bytes(data)
    candidates=[]
    for i,obj in enumerate(objects(data)):
        candidates.append({**obj,'id':f'object_{i}','starting_box':obj['box'],
            'joystick_response_vs_noop':{'left':{'dx':-3,'dy':0},'right':{'dx':4,'dy':0}} if obj['palette'][2]==255 else {},
            'observed_motion_bounds':{'max_abs_dx':4,'max_abs_dy':0,'probe_frames':30}})
    rows=[{'probe':name,'buttons':buttons,'action_frames':30,'start_sha256':digest(data),'end_sha256':digest(data),
           'start_evidence':'start.png','end_evidence':'start.png'} for name,buttons in TRACE]
    metadata={'game':'dig-dug','challenge_id':'same','rom_sha256':'rom','assets_sha256':'assets','state_sha256':'state'}
    report={'schema':'atari-discovery-v1','repeatable':True,'repeats':[rows,rows],'candidates':candidates,
            'game':'dig-dug','challenge':metadata,'coverage':'Partial pixel candidates only'}
    (directory/'discovery.json').write_text(json.dumps(report))
    return report,metadata


def answer(value,options,confidence=1):
    return {'choice':value,'confidence':confidence,'probabilities':{k:float(k==value) for k in options}}


class DiscoveryTests(unittest.TestCase):
    def test_pixel_change_and_bounded_same_palette_tracking(self):
        a,b=raster(),raster(80)
        obj=next(o for o in objects(a) if o['palette'][2]==255)
        self.assertEqual(displacement(obj,objects(b))['dx'],4)
        self.assertGreater(pixel_change(a,b)['changed_pixels'],0)
        self.assertEqual(pixel_change(a,a),{'changed_pixels':0,'change_box':None,'source_size':[160,210]})
        self.assertIsNone(displacement(obj,[]))

    def test_tampered_snapshot_and_nonrepeatable_trace_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);report,_=fixture(p);verify_discovery(p)
            report['repeats'][1][0]['end_sha256']='changed'
            with self.assertRaises(ValueError):verify_discovery(p,report)
            fixture(p);(p/'start.png').write_bytes(b'changed')
            with self.assertRaises(ValueError):verify_discovery(p)

    def test_low_confidence_roles_fall_back_to_observation_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);fixture(p)
            transport=AsyncMock();transport.request.return_value={'answers':{'role':answer('enemy',ROLES,0.16)}}
            with patch('playjev.discovery.inference',return_value=('kev:0.8b',transport)):
                result=asyncio.run(classify(p))
            self.assertEqual(result['status'],'observation-only')
            self.assertTrue(all(r['role']=='unknown' for r in result['roles']))
            self.assertFalse((p/'profile.json').exists())
            self.assertFalse(result['safety_fallback']['automatic_hosted_fallback'])

    def test_allocation_safety_hold_preserves_partial_judgments(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);fixture(p)
            transport=AsyncMock();transport.request.side_effect=RuntimeError('Failed to allocate memory')
            with patch('playjev.discovery.inference',return_value=('kev:0.8b',transport)):
                result=asyncio.run(classify(p))
            self.assertEqual(result['status'],'safety-hold')
            self.assertEqual(result['safety_fallback']['kind'],'allocation-limit')
            self.assertTrue((p/'classification.json').is_file());self.assertFalse((p/'profile.json').exists())

    def test_verified_profile_requires_model_and_pixel_evidence_agreement(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);_,metadata=fixture(p)
            async def request(body):
                if 'candidate' in body['state']:
                    c=body['state']['candidate'];role='player' if c['palette'][2]==255 else 'enemy' if c['palette'][0]==231 else 'hud'
                    return {'answers':{'role':answer(role,ROLES)}}
                return {'answers':{key:answer('tunnel-pump' if key=='strategy' else 'urgent',q['criteria']) for key,q in body['questions'].items()}}
            transport=AsyncMock();transport.request.side_effect=request
            with patch('playjev.discovery.inference',return_value=('kev:0.8b',transport)):
                asyncio.run(classify(p))
            profile,_=verified_profile(p,metadata);self.assertEqual(profile['strategy']['choice'],'tunnel-pump')
            with self.assertRaises(ValueError):verified_profile(p,{**metadata,'rom_sha256':'changed'})
            profile['roles'][0]['role']='player';(p/'profile.json').write_text(json.dumps(profile))
            with self.assertRaises(ValueError):verified_profile(p,metadata)


class NativeCaptureTests(unittest.IsolatedAsyncioTestCase):
    async def test_paused_capture_advances_one_disclosed_setup_frame(self):
        env=AsyncMock();env.page.evaluate.side_effect=[None,{'data':[1,2,3],'before':100,'after':101}]
        data,stamp=await capture(env,paused=True)
        self.assertEqual(data,b'\x01\x02\x03');self.assertEqual((stamp.before,stamp.after),(100,101))
        env.frames.assert_awaited_once_with([],1,slow=False)

    async def test_live_capture_does_not_pause_or_advance_the_game(self):
        env=AsyncMock();env.page.evaluate.side_effect=[None,{'data':[1],'before':100,'after':103}]
        await capture(env);env.frames.assert_not_awaited()
