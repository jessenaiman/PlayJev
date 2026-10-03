import asyncio
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import httpx
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from playjev.arcade import Arcade, handler
from playjev.timing import DecisionClock, INTERVALS
from playjev.runtime import registry
from playjev.metrics import Metrics
from playjev.spatial import evidence


def choice(value,options):
    return {'choice':value,'confidence':1,'probabilities':{k:float(k==value) for k in options}}


class ArcadeTests(unittest.TestCase):
    def test_clock_measured_by_code_and_bounded_by_judgment(self):
        c=DecisionClock();self.assertTrue(c.due(0))
        c.restart(10,choice('wait',INTERVALS))
        self.assertFalse(c.due(39));self.assertTrue(c.due(40))
        self.assertEqual(c.state(20)['elapsed_frames'],10)
        with self.assertRaises(ValueError):c.restart(40,choice('reset-game',['reset-game']))

    def test_registration_has_complete_reusable_hooks(self):
        for profile in registry().values():
            for name in ('observe','track','overlay','prepare','terminal_candidate','player_factory','score_collector'):
                self.assertTrue(callable(getattr(profile,name)))
        self.assertFalse(registry()['crackpots'].terminal_candidate({}))

    def test_fractional_projection_does_not_change_native_geometry(self):
        current={'player':{'box':[20,40,29,59]}}
        a=evidence(current,{'left':10,'top':20,'width':320,'height':420})
        b=evidence(current,{'left':100,'top':50,'width':1600,'height':840})
        self.assertEqual(a['normalized_player_box'],b['normalized_player_box'])
        self.assertEqual(a['native_player_box'],[20,40,29,59])
        self.assertEqual(a['projected_player_box'],[50,100,70,140])
        self.assertTrue(b['code_bounds_valid'])

    def test_measured_metrics_separate_from_inferred_ascii(self):
        m=Metrics('crackpots')
        m.start_request()
        m.record({'applied':False,'collision_veto':True,'age_frames':65,'latency_s':0.2,'executed_choice':'fire',
                  'decision':{'response':{'usage':{'input_tokens':12,'output_tokens':4}},'components':{}}})
        s=m.snapshot({'bugs':[{'box':[20,100,25,105]}],'player':{'box':[30,24,36,40]}},120,False,DecisionClock())
        self.assertEqual((s['requests'],s['applied'],s['vetoes'],s['stale']),(1,0,1,1))
        self.assertIn('P',s['ascii']);self.assertEqual(s['input_tokens'],12)
        self.assertIn('released / waiting',s['ascii'])
        self.assertEqual(s['completed'],1)

    def test_jev_selects_only_catalog_options_and_records_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            app=Arcade(tmp)
            entries=[{'id':'crackpots','available':True,'challenge':Path(tmp),'goal':'catch bugs'}]
            response={'answers':{'game':choice('crackpots',['crackpots','wait']),
                                 'readiness':choice('ready',['ready','wait_active','wait_setup','review_scores'])}}
            with patch('playjev.arcade.catalog',return_value=entries),patch('playjev.arcade.JevPlayer.request',new=AsyncMock(return_value=response)):
                r=asyncio.run(app.recommend('Play Crackpots'))
            self.assertEqual(r['choice'],'crackpots')
            self.assertTrue((Path(tmp)/'runs/arcade-processes/navigation.jsonl').is_file())

    def test_single_attempt_and_no_arbitrary_game_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            app=Arcade(tmp)
            entries=[{'id':'crackpots','available':True,'challenge':Path(tmp),'goal':'catch bugs'}]
            process=Mock(pid=123);process.poll.return_value=None
            with patch('playjev.arcade.catalog',return_value=entries),patch('playjev.arcade.subprocess.Popen',return_value=process) as spawn:
                with self.assertRaises(ValueError):app.start('../.env')
                app.start('crackpots')
                with self.assertRaises(ValueError):app.start('crackpots')
                self.assertEqual(spawn.call_count,1)
                app.stop()
                self.assertTrue((Path(tmp)/'runs'/'arcade-processes'/f'{app.active["run"]}.stop.request').is_file())
                self.assertFalse((Path(tmp)/'runs'/app.active['run']).exists())

    def test_toggle_changes_next_attempt_without_inference_or_active_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            app=Arcade(tmp)
            process=Mock(pid=123);process.poll.return_value=None
            entries=[{'id':'crackpots','available':True,'challenge':Path(tmp),'goal':'catch bugs'}]
            with patch('playjev.arcade.catalog',return_value=entries),patch('playjev.arcade.subprocess.Popen',return_value=process),patch('playjev.arcade.JevPlayer.request',new=AsyncMock()) as request:
                app.start('crackpots')
                selection=app.configure_inference('jev')
                self.assertFalse(selection['inference_called'])
                self.assertEqual(app.active['provider'],'ollaya')
                self.assertEqual(app.state()['inference']['provider'],'jev')
                request.assert_not_awaited()
            with self.assertRaises(ValueError):app.configure_inference('unknown')
            with self.assertRaises(ValueError):app.configure_inference('ollaya','--reset')

    def test_process_scoring_failed_and_malformed_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            app=Arcade(tmp);app.active={'run':'attempt','game':'crackpots'}
            app.process=Mock();app.process.poll.return_value=None
            run=Path(tmp)/'runs'/'attempt';run.mkdir(parents=True)
            (run/'process.json').write_text('{"phase":"scoring"}')
            (run/'summary.json').write_text('incomplete json')
            with patch('playjev.arcade.catalog',return_value=[]):
                self.assertEqual(app.state()['active']['phase'],'scoring')
                app.process.poll.return_value=1
                self.assertEqual(app.state()['active']['phase'],'failed')
                self.assertEqual(app.state()['scores'],[])

    def test_rate_limits_timeouts_and_concurrent_recommendation(self):
        with tempfile.TemporaryDirectory() as tmp:
            app=Arcade(tmp);server=ThreadingHTTPServer(('127.0.0.1',0),handler(app))
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            url=f'http://127.0.0.1:{server.server_port}'
            def call():
                req=urllib.request.Request(url+'/api/recommend',b'{"intent":"play"}',{'Content-Type':'application/json','Origin':url,'X-Arcade-Token':app.token})
                return urllib.request.urlopen(req)
            try:
                response=httpx.Response(429,headers={'Retry-After':'10'},request=httpx.Request('POST','https://api.typesafe.ai/v1/systemone'))
                exceptions=((httpx.HTTPStatusError('rate limit',request=response.request,response=response),429),
                            (httpx.ReadTimeout('timeout'),504))
                for exc,status in exceptions:
                    with patch.object(app,'recommend',new=AsyncMock(side_effect=exc)):
                        with self.assertRaises(urllib.error.HTTPError) as e:call()
                        self.assertEqual(e.exception.code,status);e.exception.close()
                        self.assertFalse(app.recommending)
                app.recommending=True
                with self.assertRaises(urllib.error.HTTPError) as e:call()
                self.assertEqual(e.exception.code,409);e.exception.close()
            finally:server.shutdown();server.server_close();thread.join()

    def test_loopback_mutations_need_origin_and_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            app=Arcade(tmp);server=ThreadingHTTPServer(('127.0.0.1',0),handler(app))
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                url=f'http://127.0.0.1:{server.server_port}'
                req=urllib.request.Request(url+'/api/stop',b'{}',{'Content-Type':'application/json'})
                with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(req)
                self.assertEqual(e.exception.code,403)
                e.exception.close()
                with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(url+'/runs/../.env')
                self.assertEqual(e.exception.code,404)
                e.exception.close()
            finally:server.shutdown();server.server_close();thread.join()
