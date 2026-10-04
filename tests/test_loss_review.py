import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from playjev.challenge import ROOT, digest
from playjev.loss_review import fixes, handoff, packet, request_for, review
from playjev.startup import check as startup_check
from playjev.completion import check as completion_check
from test_participation import verified_proof, raster


def answer(choice,options):
    return {'type':'choice','choice':choice,'confidence':1,'probabilities':{k:float(k==choice) for k in options}}


def summary(root,score=30):
    data=raster(score=str(score));(root/'final.png').write_bytes(data)
    decision={'step':0,'executed_choice':'noop','applied':True,'decision':{'request':{
        'state':{'player_x':42},'questions':{'lane':{'criteria':{'pot_0':{'x':39,'catchable_bugs':0},'pot_1':{'x':71,'catchable_bugs':1}}}}},
        'components':{'lane':{'choice':'pot_0'}}}}
    (root/'decisions.jsonl').write_text(json.dumps(decision)+'\n')
    return {'game':'crackpots','status':'stopped','game_frames':100,'challenge_id':'same','stop_reason':'suspected-game-over',
            'participation':verified_proof(root),'startup_check':{'passed':True},'participation_required':True,
            'score':score,'score_verified':True,'score_review':{'evidence':'final.png','evidence_sha256':digest(data)},
            'config':{'provider':'ollaya','model':'kev:0.8b','source_sha256':{'policies/crackpots.json':digest((ROOT/'playjev/policies/crackpots.json').read_bytes())}}}


def frames(root,samples):
    rows=[]
    for i,data in enumerate(samples):
        name=f'frame-{i:04}.png';(root/name).write_bytes(data)
        rows.append({'evidence':name,'sha256':digest(data),'before':i*10,'after':i*10+1})
    (root/'frames.jsonl').write_text('\n'.join(json.dumps(row) for row in rows))


class ReviewTests(unittest.IsolatedAsyncioTestCase):
    async def test_startup_completion_and_improvement_are_distinct_recipes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);s=summary(root);local=Mock();seen=[]
            async def request(body):
                seen.append(body)
                picks={'session':'active' if 'input_effect_verified' in body['state'] else 'progressed',
                       'behavior':'not_following','alternative':'unknown','expected':'pursuit','fix':'pursuit_values'}
                return {'answers':{k:answer(picks[k],v['criteria']) for k,v in body['questions'].items()},'usage':{'input_tokens':10,'output_tokens':0}}
            local.request=AsyncMock(side_effect=request)
            with patch('playjev.startup.inference',return_value=('kev:0.8b',local)),\
                 patch('playjev.completion.inference',return_value=('kev:0.8b',local)),\
                 patch('playjev.loss_review.inference',return_value=('kev:0.8b',local)):
                self.assertTrue((await startup_check(root,s))['passed'])
                (root/'summary.json').write_text(json.dumps(s))
                report=await review(root)
                self.assertTrue(report['completion_check']['passed'])
                self.assertEqual(report['handoff']['route'],'classification-worker')
                self.assertEqual(report['handoff']['allowed_edit'],['playjev/policies/crackpots.json'])
                self.assertEqual(set(seen[0]['questions']),{'session'})
                self.assertEqual(set(seen[1]['questions']),{'session'})
                self.assertEqual(set(seen[2]['questions']),{'behavior','alternative','expected','fix'})
                self.assertEqual(local.request.await_count,3)
                await review(root);self.assertEqual(local.request.await_count,3)
                self.assertTrue((root/'improvement.md').is_file())
                total=json.loads((root/'summary.json').read_text())['token_usage']
                self.assertEqual(total['total_tokens'],30)
                self.assertEqual(set(total['by_phase']),{'startup','completion','review'})

    async def test_no_score_increase_or_unverified_start_is_failure_even_if_model_claims_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);s=summary(root,score=0);state=packet(root,s)
            local=Mock();local.request=AsyncMock(return_value={'answers':{'session':answer('progressed',['progressed','no_gain','not_started','unknown'])}})
            with patch('playjev.completion.inference',return_value=('kev:0.8b',local)):
                result=await completion_check(root,s,state)
            self.assertFalse(result['passed']);self.assertEqual(result['expected_class'],'no_gain')
            s['attribution_hold']='demo';self.assertEqual(packet(root,s)['checks']['outcome'],'failed-startup')

    async def test_demo_cannot_route_direction_edits_and_source_mismatch_returns_to_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);s=summary(root);catalog=fixes('crackpots');state=packet(root,s)
            questions=request_for(state,catalog,'kev:0.8b')['questions']
            answers={k:answer(v,questions[k]['criteria']) for k,v in {'behavior':'repetition','alternative':'unknown','expected':'pursuit','fix':'pursuit_values'}.items()}
            s['completion_check']={'classification_agrees':True}
            self.assertEqual(handoff(state,answers,catalog,s)['route'],'classification-worker')
            s['config']['source_sha256']={};self.assertEqual(handoff(state,answers,catalog,s)['route'],'parent')
            state['checks']['started']=False
            job=handoff(state,answers,catalog,s)
            self.assertEqual(job['changes'][0]['file'],'playjev/runtime.py');self.assertEqual(job['allowed_edit'],[])

    async def test_counts_split_proposed_and_applied_and_missing_actions_remain_legal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);s=summary(root)
            rows=[{'step':0,'executed_choice':'left+fire','applied':True},
                  {'step':1,'executed_choice':'right','proposed_choice':'right','applied':False,'execution':{'reason':'stale'}}]
            (root/'decisions.jsonl').write_text('\n'.join(json.dumps(r) for r in rows))
            state=packet(root,s)
            self.assertEqual((state['control_counts']['left'],state['control_counts']['fire'],state['control_counts']['right']),(1,1,0))
            self.assertIn('right',state['unused_controls']);self.assertEqual(state['rejected_commands'],1)
            self.assertFalse(state['loss_verified'])

    async def test_stationary_native_gameplay_is_a_reported_fact_and_dominant_noop_is_not_a_missing_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);s=summary(root)
            frames(root,[raster(40,score='30')]*4)
            state=packet(root,s)
            self.assertEqual(state['movement']['stationary_fraction'],1)
            self.assertIn('did not move',state['findings'][0])
            self.assertNotIn('noop',request_for(state,fixes('crackpots'),'kev:0.8b')['questions']['alternative']['criteria'])
            self.assertEqual(state['missed_opportunity']['needed_direction'],'right')
            criteria=request_for(state,fixes('crackpots'),'kev:0.8b')['questions']
            answers={k:answer(v,criteria[k]['criteria']) for k,v in {'behavior':'stationary','alternative':'right','expected':'pursuit','fix':'perception'}.items()}
            answers['fix']['confidence']=0.2
            job=handoff(state,answers,fixes('crackpots'),s)
            self.assertEqual(job['route'],'parent');self.assertEqual(job['changes'][0]['file'],'playjev/policies/crackpots.json')
            self.assertFalse(job['automatic_apply'])

    async def test_unverified_stationary_sprites_do_not_become_a_gameplay_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);s=summary(root);s['attribution_hold']='demo disputed'
            frames(root,[raster(40)]*4)
            state=packet(root,s)
            self.assertEqual(state['movement']['stationary_fraction'],1)
            self.assertFalse(state['checks']['started'])
            self.assertFalse(any('Player did not move' in finding for finding in state['findings']))
            self.assertIn('not attributable',state['findings'][0])

    async def test_noop_commands_do_not_prove_stationary_native_positions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);s=summary(root)
            frames(root,[raster(x) for x in (40,50,60,70)])
            state=packet(root,s)
            self.assertEqual(state['movement']['noop_fraction'],1)
            self.assertEqual(state['movement']['stationary_fraction'],0)
            self.assertFalse(any('Player did not move' in finding for finding in state['findings']))

    async def test_building_collapse_and_terminal_intervals_are_unknown_not_stationary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);s=summary(root)
            frames(root,[raster(40,roof=roof) for roof in (46,54,94,94)])
            state=packet(root,s)
            self.assertIsNone(state['movement']['stationary_fraction'])
            self.assertEqual(state['movement']['unknown_interval_frames'],27)
            self.assertFalse(any('Player did not move' in finding for finding in state['findings']))
