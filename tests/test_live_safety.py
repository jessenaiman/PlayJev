import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from playjev.challenge import digest
from playjev.execution import FrameStamp
from playjev.live import play
from playjev.transports import SafetyHold, HostedJevTransport
from test_digdug import raster


class LiveSafetyTests(unittest.IsolatedAsyncioTestCase):
    async def test_inference_limit_releases_stops_and_preserves_recording(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);challenge=root/'challenge';challenge.mkdir()
            rom=root/'rom.a26';rom.write_bytes(b'rom');assets=root/'assets';assets.mkdir()
            state=b'state';(challenge/'start.state').write_bytes(state)
            metadata={'game':'dig-dug','challenge_id':'same','rom_path':str(rom),'assets_path':str(assets),
                      'rom_sha256':digest(b'rom'),'assets_sha256':'assets','state_sha256':digest(state),'ready_state_sha256':'ready'}
            (challenge/'challenge.json').write_text(json.dumps(metadata))
            out=root/'run';frame=raster()
            env=Mock();env.page=Mock();env.page.is_closed.return_value=False
            env.page.get_by_role.return_value.click=AsyncMock();env.page.wait_for_function=AsyncMock()
            async def evaluate(script,*args):
                if script=='window.liveStopped':return False
                if 'liveOriginFrame??' in script:return 0
                if script=='window.trackingTransform()':
                    return {'canvas_rect':{'left':0,'top':0,'width':160,'height':210},
                            'content_rect':{'left':0,'top':0,'width':160,'height':210}}
                if script=='EJS_emulator.gameManager.getFrameNum()':return 12
                return None
            env.page.evaluate=AsyncMock(side_effect=evaluate)
            env.frames=AsyncMock();env.restore_matching=AsyncMock(return_value=(b'ready',2));env.started_wall=0
            session=AsyncMock();session.__aenter__.return_value=env
            async def close(*args):
                video=out/'video';video.mkdir();(video/'saved.webm').write_bytes(b'recording')
            session.__aexit__.side_effect=close
            transport=Mock();transport.request=AsyncMock(side_effect=SafetyHold(RuntimeError('Failed to allocate memory')))
            captures=[(frame,FrameStamp(0,1,digest(frame))),(frame,FrameStamp(2,4,digest(frame))),
                      (frame,FrameStamp(8,10,digest(frame)))]
            args=Namespace(challenge=challenge,out=out,provider='ollaya',model=None,autostart=True,seconds=None)
            with patch('playjev.live.EmulatorSession',return_value=session),patch('playjev.challenge.asset_digest',return_value='assets'),\
                 patch('playjev.live.probe_control',new=AsyncMock(return_value={'verified':True})),\
                 patch('playjev.startup.check',new=AsyncMock(return_value={'passed':True})),\
                 patch('playjev.live.ollaya_manifest',new=AsyncMock(return_value={'name':'kev:0.8b'})),\
                 patch('playjev.live.inference',return_value=('kev:0.8b',transport)),\
                 patch('playjev.live.native_capture',new=AsyncMock(side_effect=captures)),\
                 patch.object(HostedJevTransport,'request',new=AsyncMock()) as hosted:
                with self.assertRaises(RuntimeError):await play(args)
                hosted.assert_not_awaited()
            summary=json.loads((out/'summary.json').read_text())
            self.assertEqual(summary['status'],'incomplete')
            self.assertEqual(summary['stop_reason'],'inference-safety-hold')
            self.assertEqual(summary['safety_fallback']['kind'],'allocation-limit')
            self.assertEqual(summary['metrics']['failed'],1);self.assertEqual(summary['metrics']['applied'],0)
            self.assertTrue((out/'replay.webm').is_file());self.assertTrue((out/'final.png').is_file())
            env.page.evaluate.assert_any_await('()=>{window.releaseLive();EJS_emulator.pause();}')
            events=[json.loads(line)['event'] for line in (out/'inference.jsonl').read_text().splitlines()]
            self.assertEqual(events,['started','failed'])
            stream=[json.loads(line) for line in (out/'events.jsonl').read_text().splitlines()]
            self.assertTrue(any(row['classification']=='judgment.failed' for row in stream))
            self.assertFalse(summary['token_usage']['complete'])
