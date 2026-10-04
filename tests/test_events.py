import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock
from playjev.events import EventLog, action_class
from playjev.transports import RecordedTransport


class EventsTests(unittest.IsolatedAsyncioTestCase):
    async def test_judgment_and_execution_share_one_classified_stream(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);events=EventLog(root/'events.jsonl',{'model':'kev:0.8b'})
            local=Mock();local.request=AsyncMock(return_value={'answers':{},'usage':{'input_tokens':10,'output_tokens':0}})
            transport=RecordedTransport(local,root/'inference.jsonl',events)
            transport.context={'request_id':2,'source':{'before':10}}
            body={'questions':{'move':{'type':'choice'}},'state':{}}
            await transport.request(body)
            events.write('control','control.rejected.stale',context=transport.context,record={'applied':False})
            rows=[json.loads(line) for line in (root/'events.jsonl').read_text().splitlines()]
            self.assertEqual([r['classification'] for r in rows],['judgment.started','judgment.completed','control.rejected.stale'])
            self.assertEqual(rows[0]['request'],body)
            self.assertEqual(rows[1]['context']['request_id'],2)
            self.assertEqual([r['event_id'] for r in rows],[0,1,2])
            local.request.assert_awaited_once_with(body)

    async def test_event_taxonomy_needs_no_additional_inference(self):
        self.assertEqual(action_class('dig-dug','right+fire'),'pump')
        self.assertEqual(action_class('crackpots','fire'),'drop')
        self.assertEqual(action_class('space-invaders','left+fire'),'shoot')
        self.assertEqual(action_class('dig-dug','noop'),'abstain')
