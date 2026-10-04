"""Bounded local typed review -> evidence-linked, file-scoped improvement handoff."""
import argparse
import asyncio
import json
from collections import Counter, deque
from pathlib import Path
from .challenge import ROOT, GAMES, JevPlayer, digest
from .events import EventLog
from .participation import score_attributable
from .transports import inference, RecordedTransport, safety_report


POLICY='playjev/policies/crackpots.json'
PURSUIT_INSTRUCTIONS=('Choose a catchable pot by the bug positions and needed_direction, not its pot_N label. '
    'Move left or right to follow the intercept as bugs shift. Prefer ready_to_drop, then short arrival_frames. '
    'Do not keep the previous target when it has zero catchable_bugs. If none are catchable, scan centrally or hold. '
    'Code handles bounded movement and fresh aligned drops; never restart.')


def fixes(game,root=ROOT):
    """Closed, parent-owned edit sites; the model cannot invent paths or commands."""
    source={'crackpots':'crackpots.py','dig-dug':'digdug.py','space-invaders':'invaders.py'}[game]
    result={
        'lifecycle':{'kind':'refactor','file':'playjev/runtime.py','symbol':'registry',
                     'change':'Calibrate the active/demo/terminal gate from the supplied native sequence; do not use HUD readability as player-control proof.',
                     'test':'.venv/bin/python -m unittest discover -s tests -p test_participation.py'},
        'perception':{'kind':'refactor','file':'playjev/'+source,'symbol':'geometry',
                     'change':'Correct the specific player/target estimates contradicted by the supplied frames; retain unknown cases.',
                     'test':'.venv/bin/python -m unittest discover -s tests -p test_'+source},
        'execution':{'kind':'refactor','file':'playjev/runtime.py','symbol':{'crackpots':'crackpots_prepare','dig-dug':'registry','space-invaders':'invaders_prepare'}[game],
                     'change':'Inspect stale/veto and applied-input evidence at this prepare hook; preserve deadlines and release rules.',
                     'test':'.venv/bin/python -m unittest discover -s tests -p test_execution.py'},
    }
    if game=='crackpots':
        path=Path(root)/POLICY;before=json.loads(path.read_text())
        result['pursuit_values']={'kind':'classification-values','file':POLICY,
            'change':'Set include_pursuit_evidence=true and replace lane_instructions with the supplied bug-following rubric.',
            'source_sha256':digest(path.read_bytes()),
            'operations':[{'op':'replace','key':key,'before':before[key],'value':value}
                          for key,value in {'include_pursuit_evidence':True,'lane_instructions':PURSUIT_INSTRUCTIONS}.items()],
            'test':'.venv/bin/python -m unittest discover -s tests -p test_crackpots.py'}
    result['unknown']={'kind':'evidence-needed','file':None,'change':'Label the supplied uncertain frames before proposing code edits.','test':None}
    return result


def compact_observation(game,current):
    player=current.get('player');box=player['box'] if player else None
    row={'player':box,'targets':[o['box'] for o in current.get('bugs',current.get('enemies',current.get('aliens',[])))[:3]],
         'active_candidate':current.get('active_play_evidence'),'roof':current.get('pot_row')}
    if game=='crackpots':
        from .crackpots import interception
        _,lanes=interception(current)
        row['lanes']=[{'x':l['x'],'catchable':l['catchable_bugs'],'ready':l['ready_to_drop']} for l in lanes]
    return row


def packet(directory,summary):
    """Counts are facts about logged commands, not proof of actual motion or loss."""
    game=summary['game'];all_controls=Counter();all_labels=Counter();actions=Counter();last=deque(maxlen=8);applied=0;rejected=0;opportunity=None
    log=directory/'decisions.jsonl'
    if log.is_file():
        with log.open() as file:
            for line in file:
                row=json.loads(line);decision=row.get('decision',{});choice=row.get('executed_choice','noop')
                if row.get('applied'):
                    applied+=1
                    actions[choice]+=1
                    for control in choice.split('+'):all_controls[control]+=1
                else:rejected+=1
                for key,value in decision.get('components',{}).items():
                    if key in ('lane','action','movement','target'):all_labels[str(value.get('choice'))]+=1
                if game=='crackpots' and choice=='noop' and opportunity is None:
                    request=decision.get('request',{});criteria=request.get('questions',{}).get('lane',{}).get('criteria',{})
                    px=request.get('state',{}).get('player_x');label=decision.get('components',{}).get('lane',{}).get('choice')
                    selected=criteria.get(label);catchable=[(key,value) for key,value in criteria.items() if isinstance(value,dict) and value.get('catchable_bugs',0)>0]
                    ignored=(isinstance(selected,dict) and selected.get('catchable_bugs')==0) or label in ('hold','scan')
                    if ignored and px is not None and catchable:
                        candidate,value=max(catchable,key=lambda pair:pair[1]['catchable_bugs'])
                        opportunity={'step':row.get('step'),'request_frame':row.get('game_frame'),'player_x':px,
                            'selected':label,'selected_catchable_bugs':selected.get('catchable_bugs') if isinstance(selected,dict) else None,'other_candidate':candidate,'other_x':value['x'],
                            'other_catchable_bugs':value['catchable_bugs'],'needed_direction':'right' if value['x']>px+3 else 'left' if value['x']<px-3 else 'aligned',
                            'scope':'Recorded code interception estimate, not proof that a catch would succeed.'}
                last.append({'step':row.get('step'),'frame':row.get('applied_at_frame',row.get('game_frame')),
                             'choice':choice,'proposed':row.get('proposed_choice',decision.get('choice')),
                             'applied':row.get('applied'),'reason':row.get('execution',{}).get('reason')})
    legal=list(GAMES[game].actions)
    controls=sorted({part for choice in legal for part in choice.split('+')})
    from .runtime import registry
    from .hud import read_score
    profile=registry()[game];frames=deque(maxlen=120);observations=[];previous=None;previous_after=None
    stationary=moving=unknown=0;motion_previous=None;motion_after=None
    index=directory/'frames.jsonl'
    if index.is_file():
        with index.open() as file:
            for line in file:
                row=json.loads(line);frames.append(row)
                source=(directory/row['evidence']).resolve()
                if not source.is_relative_to(directory.resolve()):raise ValueError('Review motion evidence path escape')
                data=source.read_bytes()
                if digest(data)!=row['sha256']:raise ValueError('Review motion evidence hash mismatch')
                current=profile.observe(data)
                if motion_previous is not None:
                    dt=max(0,row['before']-motion_after);a=motion_previous.get('player');b=current.get('player')
                    usable=bool(a and b and profile.inference_ready(current) and profile.inference_ready(motion_previous))
                    if game=='crackpots' and motion_previous.get('pot_row')!=current.get('pot_row'):usable=False
                    if not usable:unknown+=dt
                    else:
                        axes=(0,) if game in ('crackpots','space-invaders') else (0,1)
                        delta=max(abs((b['box'][axis]+b['box'][axis+2]-a['box'][axis]-a['box'][axis+2])/2) for axis in axes)
                        if delta<=1:stationary+=dt
                        else:moving+=dt
                motion_previous,motion_after=current,row['after']
    candidates=list(frames)
    selected=[candidates[i] for i in sorted({0,len(candidates)//2,len(candidates)-1})] if candidates else []
    for row in selected:
        file=(directory/row['evidence']).resolve()
        if not file.is_relative_to(directory.resolve()):raise ValueError('Review evidence path escape')
        frame=file.read_bytes()
        if digest(frame)!=row['sha256']:raise ValueError('Review native-frame hash mismatch')
        current=profile.observe(frame)
        if previous is not None:profile.track(previous,current,max(1,row['after']-previous_after))
        observations.append({'evidence':row['evidence'],'sha256':row['sha256'],'before':row['before'],'after':row['after'],
                             'hud':read_score(game,frame),**compact_observation(game,current)})
        previous,previous_after=current,row['after']
    proof=summary.get('participation',{});baseline=next((r.get('score') for r in proof.get('observations',[]) if r.get('choice')=='noop'),None)
    started=score_attributable(directory,summary) and bool(proof.get('verified')) and summary.get('startup_check',{}).get('passed',False)
    from .scoreboard import score_supported
    score=summary.get('score') if started and score_supported(directory,summary) else None
    increased=type(score) is int and type(baseline) is int and score>baseline
    outcome='failed-startup' if not started else 'progressed' if increased else 'failed-no-supported-score-increase'
    observed=stationary+moving;stationary_fraction=round(stationary/observed,4) if observed else None
    noops=all_controls['noop'];ratio=round(noops/applied,4) if applied else None
    findings=[]
    if started and stationary_fraction is not None and stationary_fraction>=0.75:
        findings.append(f'Player did not move during most sampled active intervals: {stationary_fraction:.1%} stationary. Building-collapse transitions and missing sprites excluded.')
    elif not started and stationary_fraction is not None:
        findings.append('Observed sprite positions are not attributable to controlled gameplay; no player-movement diagnosis is accepted.')
    if ratio is not None and ratio>=0.75:findings.append(f'Most applied decisions were noop: {noops}/{applied} ({ratio:.1%}).')
    if all_labels:
        label,count=all_labels.most_common(1)[0]
        findings.append(f'Most selected target/action label: {label}, {count} replies. Labels are not fixed sprite identities.')
    return {'game':game,'ending':summary.get('stop_reason','unknown'),'loss_verified':summary.get('game_over_candidate',{}).get('verified',False),
            'checks':{'started':started,'baseline_score':baseline,'best_attributed_score':score,'score_increased':increased,'outcome':outcome},
            'control_counts':{k:all_controls[k] for k in controls},'unused_controls':[k for k in controls if not all_controls[k]],
            'selected_labels':dict(all_labels.most_common(6)),'applied_commands':applied,'rejected_commands':rejected,
            'action_counts':{k:actions[k] for k in legal},'missed_opportunity':opportunity,
            'movement':{'stationary_interval_frames':stationary,'moving_interval_frames':moving,'unknown_interval_frames':unknown,
                        'stationary_fraction':stationary_fraction,'noop_fraction':ratio,
                        'scope':'Native sampled intervals, not a census of every emulator frame; ignores <=1px sprite jitter.'},'findings':findings,
            'last_moves':list(last),'native_observations':observations,
            'limits':'Commands are not motion. Unequal control use is not inherently wrong. Native roles are estimates; alternative outcomes are hypotheses. Text-only review receives geometry/HUD, not image vision.'}


def request_for(state,catalog,model):
    def choice(instructions,criteria):return {'type':'choice','instructions':instructions,'criteria':criteria}
    review_state={key:state[key] for key in ('game','checks','action_counts','unused_controls','selected_labels','movement','findings','missed_opportunity')}
    review_state['last_moves']=state['last_moves'][-4:]
    review_state['scenes']=[{key:r[key] for key in ('player','targets','roof','hud')} for r in state['native_observations']]
    return {'model':model,'state':review_state,'questions':{
        'behavior':choice('Which recorded failure pattern dominates this played attempt? If movement.stationary_fraction is above 0.75 with a high noop_fraction, stationary fits: the player did not move for most active intervals. Unequal left/right use alone is not a fault. Do not diagnose movement from demo/unverified play.',
            {'stationary':'Player did not move for most sampled active gameplay; usually waiting or repeating an aligned target while other bugs need pursuit','not_following':'Available targets shifted but movement did not follow','repetition':'Repeated the same direction despite a relevant changed state','trigger':'Missed aligned drop/pump/shoot opportunities','execution':'Stale, vetoed or unapplied actions','perception':'Incorrect/missing roles or geometry','lifecycle':'Unstarted/demo or post-loss control attribution','unknown':'No supported cause'}),
        'alternative':choice('Which underused legal input could improve the recorded missed_opportunity? Prefer its needed_direction when an estimated catchable target was ignored. This is a hypothesis, not a guaranteed catch. Unknown without a relevant opportunity; do not choose the dominant already-used input.',
            {**{k:'Legal game input: '+k for k in GAMES[state['game']].actions if state['action_counts'][k]<max(state['action_counts'].values(),default=1)},'unknown':'No supported alternative'}),
        'expected':choice('If an alternative action is supported, what improvement is plausible? This is a hypothesis, not a verified counterfactual or guaranteed longer survival.',
            {'pursuit':'Better follow/align with a moving target','interception':'Better chance to catch/drop/pump/shoot before the opportunity closes','escape':'Less exposure to the observed hazard','none':'No expected benefit supported','unknown':'Insufficient evidence'}),
        'fix':choice('Choose ONE bounded next change from these known edit sites. Classification values go to a restricted worker; lifecycle, perception or execution refactoring returns to the parent. Unknown when evidence does not justify a change.',
            {key:{'scope':v['kind'],'file':v['file'],'change':v['change']} for key,v in catalog.items()})}}


def handoff(state,answers,catalog,summary):
    chosen=answers['fix']['choice'];item=catalog[chosen];route='parent';reasons=[]
    if not state['checks']['started']:chosen='lifecycle';item=catalog[chosen];reasons.append('Player-control/start attribution failed; do not patch a direction rubric from demo movement')
    if chosen=='pursuit_values':
        recorded=summary.get('config',{}).get('source_sha256',{}).get('policies/crackpots.json')
        ready=(state['checks']['started'] and state.get('missed_opportunity') is not None and recorded==item['source_sha256'] and
               answers['behavior']['choice'] in ('stationary','not_following','repetition') and
               answers['fix']['confidence']>=0.5 and answers['behavior']['confidence']>=0.5)
        if ready:route='classification-worker'
        else:reasons.append('Source/evidence/classification agreement not sufficient for a small worker job')
    changes=[] if chosen=='unknown' else [dict(item)]
    if not summary.get('completion_check',{}).get('classification_agrees',False):
        route='parent';reasons.append('Independent completion audit unresolved or disagrees with native/code facts')
    if answers['fix']['confidence']<0.5:
        route='parent';reasons.append('Low-confidence fix is an unaccepted hypothesis, not an instruction to change code')
        changes=[]
        reasons.append('No best edit is established. Parent must compare the actual failed JSON revision and gameplay outcome before proposing a different revision; do not recycle the initial rubric.')
    return {'route':route,'changes':changes[:2],'reasons':reasons,
            'allowed_edit':[v['file'] for v in changes] if route=='classification-worker' else [],
            'forbidden':'No directory scan, unrelated edits, safety/timing changes, inference fallback, reset, commit or push.',
            'worker_status':'not-dispatched; parent must grade three-question TypeSafe quiz and verify eligible model/cost before OpenCode CLI delegation',
            'acceptance':'Replay the changed JSON in visible gameplay. Only a verified stage clear establishes success; score and native movement explain failures.',
            'automatic_apply':False}


def markdown(report):
    state=report['evidence'];checks=state['checks'];judgments=report.get('judgments',{});job=report['handoff']
    lines=['# Gameplay improvement handoff',f"Attempt: `{report['run']}` · {state['game']}",
           f"Ending: {state['ending']} · verified loss: {state['loss_verified']}",
           f"Check: **{checks['outcome']}** · started: {checks['started']} · score {checks['baseline_score']} → {checks['best_attributed_score']}",
           '', '## Recorded facts',f"Applied commands: {state['applied_commands']}; rejected: {state['rejected_commands']}.",
           *state.get('findings',[]),
           'Control use: `'+json.dumps(state['control_counts'])+'`.', 'Unused: `'+json.dumps(state['unused_controls'])+'`.',
           'Last moves: `'+json.dumps(state['last_moves'])+'`.',
           'Native evidence: '+', '.join('`'+r['evidence']+'`' for r in state['native_observations'])+'.',
           'Missed opportunity estimate: `'+json.dumps(state.get('missed_opportunity'))+'`.',
           '', '## Typed hypotheses (not proof)', 'No valid review response.' if not judgments else
           '; '.join(f"{k}: {v['choice']} (confidence {v['confidence']:.2f})" for k,v in judgments.items())+'.',
           '',f"## Route: {job['route']}"]
    if not job['changes']:lines.append('Label the supplied evidence; no implementation change is justified yet.')
    for index,change in enumerate(job['changes'],1):
        lines.extend([f"{index}. **`{change['file']}`**: {change['change']}"])
        if change.get('proposal_source'):lines.append('   Proposal provenance: '+change['proposal_source']+'.')
        if change.get('operations'):lines.extend(['```json',json.dumps(change['operations'],indent=2),'```'])
        if change.get('symbol'):lines.append('   Edit site: `'+change['symbol']+'`.')
        lines.append('   Gameplay check: replay from the same challenge and compare the supported score, observed movement and verified stage progression.')
    lines.extend(['',job['forbidden'],job['worker_status'],job['acceptance'],
                  '', 'No automatic patch, model retraining, longer-survival claim or game-completion claim.',
                  'This document is assembled from typed selections and code-owned templates, not unconstrained Jev-generated prose.'])
    return '\n'.join(lines)+'\n'


async def review(directory,*,events=None,note=None,root=ROOT,rereview=False):
    directory=Path(directory);path=directory/'loss-review.json'
    document='improvement.md'
    if path.exists():
        if not rereview:return json.loads(path.read_text())  # No hidden retry/spend.
        revision=2
        while (directory/f'loss-review-{revision}.json').exists():revision+=1
        path=directory/f'loss-review-{revision}.json';document=f'improvement-{revision}.md'
    summary=json.loads((directory/'summary.json').read_text());state=packet(directory,summary)
    catalog=fixes(summary['game'],root);provider=summary['config'].get('provider','ollaya')
    model,transport=inference(provider,summary['config'].get('model'))
    events=events or EventLog(directory/'events.jsonl',{'kind':'llm','provider':provider,'model':model})
    from .completion import check as completion_check
    report_check=summary.get('completion_check') if rereview else None
    if not report_check or report_check.get('checks')!=state['checks']:report_check=await completion_check(directory,summary,state,events)
    summary['completion_check']=report_check
    logged=RecordedTransport(transport,directory/'review-inference.jsonl',events);logged.context={'phase':'post-game-review'}
    body=request_for(state,catalog,model);report={'schema':'jev-loss-review-v1','run':directory.name,'provider':provider,
        'model':model,'evidence':state,'note':note,'request':body,'status':'pending','judgments':{}}
    try:
        if summary.get('safety_fallback') or summary.get('score_error'):raise ValueError('Play/score verification already failed; no additional inference')
        response=await asyncio.wait_for(logged.request(body),20);report['response']=response
        if set(response.get('answers',{}))!=set(body['questions']):raise ValueError('Review question set mismatch')
        report['judgments']={key:JevPlayer.validate_choice(response['answers'][key],q['criteria']) for key,q in body['questions'].items()}
        report['status']='reviewed'
    except Exception as exc:report.update(status='unavailable',error=safety_report(exc))
    if report['judgments']:
        alternative=report['judgments']['alternative']['choice']
        report['validated_alternative']=alternative if state['checks']['started'] and alternative!='unknown' else None
        report['handoff']=handoff(state,report['judgments'],catalog,summary)
    else:
        report['handoff']={'route':'parent','changes':[catalog['lifecycle']], 'allowed_edit':[], 'automatic_apply':False,
            'forbidden':'No directory scan or automatic edit.','worker_status':'not-dispatched','acceptance':'Repair evidence/review failure before accepting an improvement.'}
    report['completion_check']=report_check
    report['handoff']['failed_moves']=state['last_moves'];report['handoff']['evidence_files']=[r['evidence'] for r in state['native_observations']]
    path.write_text(json.dumps(report,indent=2));(directory/document).write_text(markdown(report))
    summary['completion_check']=report['completion_check']
    summary['evaluation_outcome']=state['checks']['outcome'] if report['completion_check']['passed'] else 'failed-validation'
    summary['loss_review']={'report':path.name,'document':document,'status':report['status'],'route':report['handoff']['route']}
    from .usage import token_usage
    summary['token_usage']=token_usage(directory,summary);(directory/'summary.json').write_text(json.dumps(summary,indent=2))
    events.write('post-game-review','review.'+report['status'],judgments=report['judgments'],handoff=report['handoff'],completion_check=report['completion_check'])
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('run',type=Path);parser.add_argument('--note');parser.add_argument('--rereview',action='store_true',help='Explicit extra review; preserve prior report and count added tokens')
    args=parser.parse_args()
    print(json.dumps(asyncio.run(review(args.run,note=args.note,rereview=args.rereview))['handoff'],indent=2))
