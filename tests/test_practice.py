import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock
from playjev.challenge import digest, JevPlayer
from playjev.checkpoints import verify
from playjev.execution import FrameStamp
from playjev.practice import Goal, plan, validate
from playjev.scoreboard import eligible


def checkpoint(directory,frames=120,score=10):
    directory.mkdir(parents=True,exist_ok=True)
    metadata={'game':'crackpots','challenge_id':'same','rom_sha256':'rom','assets_sha256':'assets'}
    row={'schema':'atari-checkpoint-v1',**metadata,'logical_frames':frames,'inputs_released':True}
    for name,key in (('checkpoint.state','state_sha256'),('checkpoint-ready.state','ready_state_sha256'),('checkpoint.png','image_sha256')):
        data=name.encode();(directory/name).write_bytes(data);row[key]=digest(data)
    (directory/'checkpoint.json').write_text(json.dumps(row))
    data=b'final';(directory/'final.png').write_bytes(data)
    summary={'game':'crackpots','challenge_id':'same','status':'stopped','game_frames':frames,'checkpoint':row,
             'score':score,'score_verified':score is not None,
             'score_review':{'evidence':'final.png','evidence_sha256':digest(data)}}
    (directory/'summary.json').write_text(json.dumps(summary))
    return metadata,summary


class PracticeTests(unittest.TestCase):
    def test_fresh_frame_progression_caps_and_resume_increment(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'source';m,_=checkpoint(source)
            fresh=plan(m,[source],100,'frames',150)
            self.assertEqual((fresh['target'],fresh['segment_frames'],fresh['base_frames']),(220,150,0))
            resumed=plan(m,[source],100,'frames',1000,source)
            self.assertEqual((resumed['target'],resumed['segment_frames'],resumed['base_frames']),(220,100,120))
            self.assertEqual(validate(resumed,m),resumed)
            result=Goal(fresh).finish(150)
            self.assertTrue(result['cap_reached']);self.assertFalse(result['achieved'])
            self.assertTrue(Goal(resumed).finish(100)['achieved'])

    def test_score_goal_requires_baseline_and_failure_does_not_ratchet(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'source';m,row=checkpoint(source)
            a=plan(m,[source],100,'score',60)
            self.assertEqual(a['target'],110)
            self.assertEqual(a,plan(m,[source],100,'score',60))
            row['score_verified']=False;(source/'summary.json').write_text(json.dumps(row))
            with self.assertRaises(ValueError):plan(m,[source],100,'score',60)
            self.assertEqual(plan(m,[],10,'frames',60)['target'],10)

    def test_goal_requires_two_independent_exact_observations(self):
        goal=Goal({'metric':'score','target':100,'segment_frames':60})
        self.assertIsNone(goal.observe(100,FrameStamp(1,3,'a'),'frame-0.png',3))
        self.assertIsNone(goal.observe(100,FrameStamp(3,5,'b'),'frame-1.png',5))
        self.assertIsNone(goal.observe(None,FrameStamp(7,9,'c'),'frame-2.png',9))
        self.assertIsNone(goal.observe(100,FrameStamp(11,13,'d'),'frame-3.png',13))
        self.assertEqual(goal.observe(100,FrameStamp(15,17,'e'),'frame-4.png',17)['value'],100)
        self.assertTrue(goal.finish(17)['achieved'])

    def test_checkpoint_tampering_identity_and_failure_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);m,row=checkpoint(p)
            self.assertEqual(verify(p,m)['logical_frames'],120)
            with self.assertRaises(ValueError):verify(p,{**m,'rom_sha256':'changed'})
            row['status']='incomplete';(p/'summary.json').write_text(json.dumps(row))
            with self.assertRaises(ValueError):verify(p,m)
            row['status']='stopped';row['game_over_candidate']={'verified':False}
            (p/'summary.json').write_text(json.dumps(row))
            with self.assertRaises(ValueError):verify(p,m)
            del row['game_over_candidate'];(p/'summary.json').write_text(json.dumps(row))
            value=plan(m,[p],100,'frames',120,p)
            (p/'checkpoint.state').write_bytes(b'changed')
            with self.assertRaises(ValueError):validate(value,m)

    def test_invalid_limits_and_unknown_metrics_rejected(self):
        m={'game':'crackpots','challenge_id':'same'}
        for step in (0,True,-1,1.5,100001):
            with self.assertRaises(ValueError):plan(m,[],step,'frames')
        for cap in (0,True,36001):
            with self.assertRaises(ValueError):plan(m,[],10,'frames',cap)
        with self.assertRaises(ValueError):plan(m,[],10,'wave')
        value=plan(m,[],10,'frames',60)
        with self.assertRaises(ValueError):validate({**value,'target':999},m)
        with self.assertRaises(ValueError):validate({**value,'segment_frames':9},m)

    def test_resumed_scores_cannot_seed_fresh_target_or_rank(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);m,row=checkpoint(p,score=5000)
            row.update(practice={'resume_from':'parent'},status='complete',budget_frames=120)
            (p/'summary.json').write_text(json.dumps(row))
            self.assertFalse(eligible(p,row))
            with self.assertRaises(ValueError):plan(m,[p],100,'score')

    def test_bounded_practice_context_is_in_exact_transport_request(self):
        import asyncio
        transport=AsyncMock();transport.request.return_value={}
        player=JevPlayer(transport=transport)
        player.practice_context={'target':790,'previous_player_box':[30,24,36,40],'no_reset_or_resume_authority':True}
        asyncio.run(player.request({'state':{'current':{}},'questions':{}}))
        self.assertEqual(transport.request.call_args.args[0]['state']['practice'],player.practice_context)
