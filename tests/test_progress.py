import json
import tempfile
import unittest
from pathlib import Path
from playjev.challenge import digest
from playjev.execution import FrameStamp
from playjev.progress import endpoint, load, next_target, save


class ProgressTests(unittest.TestCase):
    def test_endpoint_is_last_observation_not_verified_death(self):
        e=endpoint('crackpots',{'player':{'box':[30,24,36,40]},'bugs':[{}]},FrameStamp(100,102,'hash'),90,'hash')
        self.assertEqual(e['capture_interval']['game_before'],10)
        self.assertEqual(e['player_box'],[30,24,36,40]);self.assertFalse(e['terminal_verified']);self.assertIsNone(e['wave'])
        with self.assertRaises(ValueError):endpoint('crackpots',{},FrameStamp(100,102,'hash'),90,'changed')

    def test_unknown_and_failed_attempts_do_not_rachet_goal(self):
        p={'game':'crackpots','challenge_id':'same','best_supported_score':None}
        self.assertIsNone(next_target(p,100)['target'])
        p['best_supported_score']=690
        a=next_target(p,100);b=next_target(p,100)
        self.assertEqual(a['target'],790);self.assertEqual(a,b)
        self.assertFalse(a['changes_budget']);self.assertFalse(a['launches_attempt'])
        for step in (0,-1,True,1.5,100001):
            with self.assertRaises(ValueError):next_target(p,step)
        with self.assertRaises(ValueError):next_target(p,1,'wave')

    def test_ledger_grouping_and_tampered_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);data=b'evidence';(p/'final.png').write_bytes(data)
            row={'game':'crackpots','challenge_id':'same','status':'stopped','game_frames':60,'stop_reason':'user-stop',
                 'score':690,'score_verified':True,'score_review':{'evidence':'final.png','evidence_sha256':digest(data)},
                 'endpoint':endpoint('crackpots',{},FrameStamp(50,52,digest(data)),0,digest(data))}
            (p/'summary.json').write_text(json.dumps(row));save(p)
            result=load([p])[0];self.assertEqual(result['best_supported_score'],690)
            self.assertEqual(result['latest']['stop_reason'],'user-stop')
            (p/'final.png').write_bytes(b'changed')
            result=load([p])[0];self.assertIsNone(result['best_supported_score']);self.assertIsNone(result['latest'])
