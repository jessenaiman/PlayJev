import asyncio
import json
import os
import unittest
from unittest.mock import AsyncMock, Mock, patch
from playjev.transports import OllayaTransport, HostedJevTransport, inference, ollaya_manifest
from playjev.challenge import JevPlayer


class TransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_cli_contract_and_no_hosted_credentials(self):
        question={'type':'noul','instructions':'Ready?'}
        response={'model':'kev:0.8b','answers':{'q':{'type':'noul','noul':0.9}},'usage':{'input_tokens':25,'output_tokens':0},'state_truncated':False}
        process=Mock(returncode=0)
        process.communicate=AsyncMock(return_value=(json.dumps(response).encode(),b''))
        with patch.dict(os.environ,{'TYPESAFE_API_KEY':'test-secret','JEV_API_KEY':'other-secret'}),patch('asyncio.create_subprocess_exec',new=AsyncMock(return_value=process)) as spawn:
            result=await OllayaTransport().request({'model':'kev:0.8b','state':{'ready':True},'questions':{'q':question}})
        args=spawn.call_args.args;env=spawn.call_args.kwargs['env']
        self.assertEqual(args[:3],('ollaya','run','kev:0.8b'))
        self.assertNotIn('TYPESAFE_API_KEY',env);self.assertNotIn('JEV_API_KEY',env)
        self.assertEqual(json.loads(args[-1]),{'q':question})
        self.assertEqual(json.loads(process.communicate.call_args.args[0]),{'ready':True})
        self.assertIn('ollaya-cli',result['transport'])

    async def test_cli_failure_truncation_and_bad_output_do_not_fallback(self):
        for code,stdout,stderr in ((1,b'',b'GPU allocation failed'),
            (0,b'{"state_truncated":true,"answers":{"q":{}}}',b''),
            (0,b'{"answers":{"other":{}}}',b'')):
            process=Mock(returncode=code);process.communicate=AsyncMock(return_value=(stdout,stderr))
            with patch('asyncio.create_subprocess_exec',new=AsyncMock(return_value=process)),patch.object(HostedJevTransport,'request',new=AsyncMock()) as hosted:
                with self.assertRaises((RuntimeError,ValueError)):
                    await OllayaTransport().request({'model':'kev:0.8b','state':{},'questions':{'q':{}}})
                hosted.assert_not_awaited()

    async def test_timeout_kills_and_reaps_cli(self):
        process=Mock(returncode=None)
        process.communicate=AsyncMock(side_effect=[asyncio.TimeoutError(),(b'',b'')])
        with patch('asyncio.create_subprocess_exec',new=AsyncMock(return_value=process)):
            with self.assertRaises(asyncio.TimeoutError):
                await OllayaTransport().run('kev:0.8b',{}, {'q':{}})
        process.kill.assert_called_once();self.assertEqual(process.communicate.await_count,2)

    async def test_default_is_cli_and_explicit_hosted_switch(self):
        model,transport=inference();self.assertEqual(model,'kev:0.8b');self.assertIsInstance(transport,OllayaTransport)
        model,transport=inference('jev');self.assertEqual(model,'jev-latest');self.assertIsInstance(transport,HostedJevTransport)
        with self.assertRaises(ValueError):inference('silent-fallback')

    async def test_model_manifest_uses_cli(self):
        process=Mock(returncode=0);process.communicate=AsyncMock(return_value=(b'FROM sha256:pinned\n',b''))
        with patch('asyncio.create_subprocess_exec',new=AsyncMock(return_value=process)) as spawn:
            result=await ollaya_manifest('kev:0.8b')
        self.assertEqual(spawn.call_args.args,('ollaya','show','kev:0.8b','--modelfile'))
        self.assertEqual(result['name'],'kev:0.8b')
        self.assertEqual(len(result['modelfile_sha256']),64)

    async def test_same_policy_adds_both_accuracy_checks_and_clock(self):
        transport=Mock();transport.request=AsyncMock(return_value={'answers':{}})
        player=JevPlayer(model='kev:0.8b',transport=transport)
        player.decision_timing={'elapsed_frames':6};player.accuracy_evidence={'player_observed':True}
        body={'model':player.model,'state':{},'questions':{'move':{'type':'choice','criteria':{'noop':'wait'}}}}
        await player.request(body)
        self.assertEqual(set(body['questions']),{'move','cycle','perception_check','projection_check'})
        transport.request.assert_awaited_once_with(body)
