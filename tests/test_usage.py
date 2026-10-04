import json
import tempfile
import unittest
from pathlib import Path
from playjev.usage import player_identity, token_usage


class UsageTests(unittest.TestCase):
    def test_all_recorded_replies_count_once_even_when_controls_were_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            rows=[{'sequence':0,'event':'started'},
                  {'sequence':0,'event':'completed','response':{'usage':{'input_tokens':20,'output_tokens':3}}},
                  {'sequence':1,'event':'started'},
                  {'sequence':1,'event':'completed','response':{'usage':{'input_tokens':40,'output_tokens':5}}}]
            (root/'inference.jsonl').write_text('\n'.join(json.dumps(r) for r in rows))
            (root/'decisions.jsonl').write_text(json.dumps({'applied':False,'decision':{'response':{'usage':{'input_tokens':999,'output_tokens':999}}}}))
            (root/'hud-jev.json').write_text(json.dumps({'unique_requests':1,'response':{'usage':{'input_tokens':7,'output_tokens':2}}}))
            result=token_usage(root,{})
            self.assertEqual((result['input_tokens'],result['output_tokens'],result['total_tokens']),(67,10,77))
            self.assertTrue(result['complete']);self.assertEqual(result['known_requests'],3)
            rows.extend([{'sequence':2,'event':'started'},{'sequence':2,'event':'cancelled'}])
            (root/'inference.jsonl').write_text('\n'.join(json.dumps(r) for r in rows))
            result=token_usage(root,{})
            self.assertEqual(result['total_tokens'],77);self.assertFalse(result['complete'])

    def test_legacy_costs_are_lower_bounds_and_missing_usage_is_not_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'decisions.jsonl').write_text(json.dumps({'decision':{'response':{'usage':{'input_tokens':12,'output_tokens':0}}}}))
            result=token_usage(root,{})
            self.assertEqual(result['total_tokens'],12);self.assertFalse(result['complete'])
            (root/'decisions.jsonl').write_text(json.dumps({'decision':{'response':{}}}))
            self.assertIsNone(token_usage(root,{})['total_tokens'])

    def test_model_handle_keeps_exact_identity_and_does_not_label_ai_as_human(self):
        self.assertEqual(player_identity({'model':'kev:0.8b','provider':'ollaya'})['name'],'KEV-0.8B')
        self.assertEqual(player_identity({'model':'kev:0.8b'})['kind'],'llm')
        self.assertEqual(player_identity({'player':'human','arcade_name':'ACE'})['name'],'ACE')

    def test_malformed_and_duplicate_usage_cannot_make_a_complete_cost_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            row={'event':'completed','sequence':0,'response':{'usage':{'input_tokens':10,'output_tokens':0}}}
            (root/'inference.jsonl').write_text(json.dumps(row)+'\n'+json.dumps(row)+'\n'+'broken\n')
            result=token_usage(root,{})
            self.assertEqual(result['total_tokens'],10);self.assertFalse(result['complete'])
