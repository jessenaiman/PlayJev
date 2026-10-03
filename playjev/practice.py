"""Explicit single-segment progression. Measurements and stopping belong to code."""
import json
from pathlib import Path
from .checkpoints import verify
from .progress import load
from .scoreboard import score_supported


def bounded_integer(value, name, maximum):
    if type(value) is not int or not 1<=value<=maximum:
        raise ValueError(f'{name} must be an integer from 1 to {maximum}')
    return value


def plan(metadata, runs, increment=100, metric='score', cap_frames=3600, resume_from=None):
    bounded_integer(increment,'Increment',100000)
    bounded_integer(cap_frames,'Practice frame cap',36000)
    if metric not in ('score','frames'):raise ValueError('Practice metric must be score or frames')
    runs=list(map(Path,runs))
    previous=None;checkpoint=None;offset=0
    baseline=None
    if resume_from is not None:
        source=Path(resume_from)
        checkpoint=verify(source,metadata)
        offset=checkpoint['logical_frames']
        row=json.loads((source/'summary.json').read_text())
        baseline=row['score'] if score_supported(source,row) else None
        previous=row.get('endpoint')
        if previous:
            from .challenge import digest
            try:
                if previous['evidence']!='final.png' or digest((source/'final.png').read_bytes())!=previous['evidence_sha256']:
                    previous=None
            except (OSError,KeyError,TypeError):previous=None
    else:
        group=next((g for g in load(runs) if g['game']==metadata['game'] and g['challenge_id']==metadata['challenge_id']),None)
        if group:
            baseline=group['best_supported_score']
            previous=(group['latest'] or {}).get('endpoint')
    if metric=='score':
        if baseline is None:raise ValueError('Score baseline is unknown; use a frame-budget extension or record supported HUD evidence first')
        target=baseline+increment
        segment=cap_frames
    else:
        baseline=offset
        if resume_from is None:
            for directory in runs:
                try:baseline=max(baseline,verify(directory,metadata)['logical_frames'])
                except (OSError,ValueError,KeyError,TypeError):continue
        target=baseline+increment
        segment=min(cap_frames,max(1,target-offset))
    return {'schema':'atari-practice-v1','game':metadata['game'],'challenge_id':metadata['challenge_id'],
            'metric':metric,'increment':increment,'previous_best':baseline,'target':target,
            'cap_frames':cap_frames,'segment_frames':segment,'base_frames':offset,
            'resume_from':str(Path(resume_from).resolve()) if resume_from else None,
            'checkpoint':checkpoint,'previous_endpoint':previous,
            'note':'One explicitly launched, unranked practice segment. Frames are a budget/continuation target, not cleared terrain, survival or game completion. No automatic batch or reset.'}


def validate(value, metadata):
    if value.get('schema')!='atari-practice-v1' or any(value.get(k)!=metadata[k] for k in ('game','challenge_id')):
        raise ValueError('Practice plan identity mismatch')
    bounded_integer(value.get('increment'),'Increment',100000)
    bounded_integer(value.get('cap_frames'),'Practice frame cap',36000)
    bounded_integer(value.get('segment_frames'),'Practice segment',value['cap_frames'])
    if value.get('metric') not in ('score','frames') or type(value.get('target')) is not int or value['target']<1:
        raise ValueError('Invalid practice target')
    if type(value.get('base_frames')) is not int or value['base_frames']<0:
        raise ValueError('Invalid practice continuation frame offset')
    if type(value.get('previous_best')) is not int or value['previous_best']<0 or value['target']!=value['previous_best']+value['increment']:
        raise ValueError('Practice target does not match previous baseline + increment')
    expected_segment=value['cap_frames'] if value['metric']=='score' else min(value['cap_frames'],max(1,value['target']-value['base_frames']))
    if value['segment_frames']!=expected_segment:
        raise ValueError('Practice segment does not match target/frame cap')
    if value.get('resume_from'):
        actual=verify(value['resume_from'],metadata)
        if actual!=value.get('checkpoint') or actual['logical_frames']!=value['base_frames']:
            raise ValueError('Practice checkpoint changed after launch')
    elif value.get('checkpoint') or value['base_frames']!=0:
        raise ValueError('Fresh practice cannot contain a resume offset')
    return value


class Goal:
    def __init__(self, value):
        self.plan=value;self.previous=None;self.achievement=None

    def observe(self, score, stamp, evidence, frames):
        if self.plan['metric']=='frames':
            if self.plan['base_frames']+frames>=self.plan['target']:
                self.achievement={'metric':'frames','value':self.plan['base_frames']+frames,
                                  'note':'Frame-budget target reached; not game-progress/completion evidence'}
        elif score is not None:
            prior=self.previous
            if prior and prior['value']==score and prior['after']<stamp.before and score>=self.plan['target']:
                self.achievement={'metric':'score','value':score,'observations':[prior,
                    {'value':score,'before':stamp.before,'after':stamp.after,'sha256':stamp.sha256,'evidence':evidence}]}
        self.previous=None if score is None else {'value':score,'before':stamp.before,'after':stamp.after,'sha256':stamp.sha256,'evidence':evidence}
        return self.achievement

    def finish(self, frames):
        if self.plan['metric']=='frames' and self.plan['base_frames']+frames>=self.plan['target']:
            self.achievement={'metric':'frames','value':self.plan['base_frames']+frames,
                              'note':'Frame-budget target reached; not game-progress/completion evidence'}
        return {'achieved':self.achievement is not None,'achievement':self.achievement,
                'executed_frames':frames,'cap_reached':frames>=self.plan['segment_frames']}

    def context(self):
        e=self.plan.get('previous_endpoint') or {}
        return {'metric':self.plan['metric'],'target':self.plan['target'],'increment':self.plan['increment'],
                'resumed':bool(self.plan['resume_from']),'base_frames':self.plan['base_frames'],
                'previous_player_box':e.get('player_box'),'previous_observed_targets':e.get('observed_targets'),
                'endpoint_is_not_current_state':True,'no_reset_or_resume_authority':True}


if __name__=='__main__':
    import argparse
    from .challenge import ROOT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('challenge',type=Path);parser.add_argument('--out-plan',type=Path,required=True)
    parser.add_argument('--increment',type=int,default=100);parser.add_argument('--metric',choices=('score','frames'),default='score')
    parser.add_argument('--cap-frames',type=int,default=1800);parser.add_argument('--resume-from',type=Path)
    parser.add_argument('--runs-root',type=Path,default=ROOT/'runs')
    args=parser.parse_args()
    value=plan(json.loads((args.challenge/'challenge.json').read_text()),
               (p.parent for p in args.runs_root.rglob('summary.json')),args.increment,args.metric,args.cap_frames,args.resume_from)
    args.out_plan.parent.mkdir(parents=True,exist_ok=True)
    with args.out_plan.open('x') as file:file.write(json.dumps(value,indent=2))
    print(json.dumps({k:value[k] for k in ('metric','target','segment_frames','resume_from','note')},indent=2))
