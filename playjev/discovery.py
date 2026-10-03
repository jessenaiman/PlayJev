"""Initial-load discovery/classification: pixel probes first, typed hypotheses second."""
import argparse
import asyncio
import io
import json
from collections import defaultdict
from pathlib import Path
from PIL import Image
from .challenge import EmulatorSession, GAMES, ROOT, JevPlayer, asset_digest, digest
from .invaders import components
from .transports import inference, RecordedTransport, safety_report
from .native import capture

TRACE=(('noop',[]),('left',[6]),('right',[7]),('up',[4]),('down',[5]),('pump',[0]))
ROLES={'player':'The controllable character: moves in response to joystick probes, unlike autonomous monsters or HUD',
       'enemy':'A separate hostile/monster candidate; not controlled directly by the joystick',
       'rock':'A compact obstacle/boulder; do not infer rock merely from lack of movement',
       'terrain':'Soil, tunnel or scenery; not an independently moving character',
       'hud':'Score/lives or other fixed display outside the playfield',
       'unknown':'Insufficient/ambiguous evidence; role cannot be supported from these probes'}


def image(data):
    return Image.open(io.BytesIO(data)).convert('RGB').resize((160,210),Image.Resampling.NEAREST)


def objects(data):
    im=image(data);colors=defaultdict(list)
    for y in range(210):
        for x in range(160):
            color=im.getpixel((x,y))
            if max(color)>40:colors[color].append((x,y))
    result=[]
    for color,mask in sorted(colors.items()):
        parts=[p for p in components(mask) if 4<=p['pixels']<=256 and p['box'][2]-p['box'][0]<24 and p['box'][3]-p['box'][1]<24]
        # Merge close, vertically multiplexed pieces only when their combined box
        # still has sprite-scale dimensions. Never merge a whole color's terrain.
        merged=[]
        for p in parts:
            old=next((o for o in merged if abs((p['box'][0]+p['box'][2]-o['box'][0]-o['box'][2])/2)<=3
                      and 0<=p['box'][1]-o['box'][3]<=4 and p['box'][3]-o['box'][1]<24),None)
            if old:
                old['box']=[min(old['box'][0],p['box'][0]),old['box'][1],max(old['box'][2],p['box'][2]),p['box'][3]]
                old['pixels']+=p['pixels']
            else:merged.append({**p,'box':list(p['box'])})
        for p in merged:
            if p['pixels']<12:continue
            x,y,x2,y2=p['box']
            signature=[''.join('#' if im.getpixel((xx,yy))==color else '.' for xx in range(x,x2+1)) for yy in range(y,y2+1)]
            result.append({**p,'palette':list(color),'signature':signature})
    return sorted(result,key=lambda o:(-o['pixels'],o['box']))[:16]


def pixel_change(before, after):
    a,b=image(before),image(after)
    points=[(x,y) for y in range(210) for x in range(160) if a.getpixel((x,y))!=b.getpixel((x,y))]
    box=[min(x for x,y in points),min(y for x,y in points),max(x for x,y in points),max(y for x,y in points)] if points else None
    return {'changed_pixels':len(points),'change_box':box,'source_size':[160,210]}


def displacement(start, end):
    candidates=[o for o in end if o['palette']==start['palette']]
    if not candidates:return None
    def distance(o):return abs(o['box'][0]-start['box'][0])+abs(o['box'][1]-start['box'][1])
    match=min(candidates,key=distance)
    if distance(match)>60:return None
    x,y,x2,y2=start['box'];a,b,a2,b2=match['box']
    return {'box':match['box'],'dx':(a+a2-x-x2)/2,'dy':(b+b2-y-y2)/2,
            'note':'Same-palette nearest candidate; animation/flicker/identity swaps can change this estimate'}


async def native_capture(env):
    data,_=await capture(env,paused=True)
    return data


async def discover(challenge,out,visible=False,frames=30):
    if type(frames) is not int or not 1<=frames<=60:raise ValueError('Probe frames must be an integer from 1 to 60')
    metadata=json.loads((challenge/'challenge.json').read_text())
    rom,assets=Path(metadata['rom_path']),Path(metadata['assets_path'])
    snapshot=(challenge/'start.state').read_bytes()
    if (digest(rom.read_bytes())!=metadata['rom_sha256'] or asset_digest(assets)!=metadata['assets_sha256']
            or digest(snapshot)!=metadata['state_sha256']):raise ValueError('Challenge bytes changed')
    out.mkdir(parents=True,exist_ok=False)
    repeats=[]
    for repeat in range(2):
        rows=[]
        async with EmulatorSession(assets,rom,visible,out/f'video-{repeat}',speed=1) as env:
            await env.frames([],40,slow=False)
            for name,buttons in TRACE:
                _,setup=await env.restore_matching(snapshot,metadata['ready_state_sha256'])
                start=await native_capture(env)
                await env.frames(buttons,frames,slow=False)
                end=await native_capture(env)
                prefix=f'repeat-{repeat}-{name}'
                (out/(prefix+'-start.png')).write_bytes(start);(out/(prefix+'-end.png')).write_bytes(end)
                rows.append({'probe':name,'buttons':buttons,'action_frames':frames,'restore_callbacks':setup,
                             'capture_setup_frames':2,'start_sha256':digest(start),'end_sha256':digest(end),
                             'start_evidence':prefix+'-start.png','end_evidence':prefix+'-end.png',
                             'pixel_change':pixel_change(start,end),'start_objects':objects(start),'end_objects':objects(end)})
        repeats.append(rows)
    repeatable=all(a['start_sha256']==b['start_sha256'] and a['end_sha256']==b['end_sha256'] for a,b in zip(*repeats))
    candidates=[]
    for i,obj in enumerate(repeats[0][0]['start_objects']):
        probes={row['probe']:displacement(obj,row['end_objects']) for row in repeats[0]}
        neutral=probes['noop']
        response={k:None if not v or not neutral else {'dx':v['dx']-neutral['dx'],'dy':v['dy']-neutral['dy']}
                  for k,v in probes.items()}
        observed=[v for v in probes.values() if v]
        candidates.append({**obj,'id':f'object_{i}','starting_box':obj['box'],'probes':probes,
            'joystick_response_vs_noop':response,
            'observed_motion_bounds':{'max_abs_dx':max((abs(v['dx']) for v in observed),default=0),
                                      'max_abs_dy':max((abs(v['dy']) for v in observed),default=0),
                                      'probe_frames':frames,'not_a_guaranteed_future_bound':True}})
    report={'schema':'atari-discovery-v1','game':metadata['game'],'challenge':metadata,
            'source_sha256':digest(Path(__file__).read_bytes()),'trace':list(TRACE),'repeats':repeats,
            'repeatable':repeatable,'candidates':candidates,'inference_requests':0,
            'coverage':'At most 16 compact same-palette pixel candidates. Large terrain, ghosts, flicker, occlusion and unseen objects can be missed. Not all objects or roles are known.',
            'note':'Discovery/calibration explicitly restores before each probe; it is not a scored attempt, gameplay continuation or model-weight training.'}
    (out/'discovery.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({'repeatable':repeatable,'candidates':len(candidates),'probes_per_repeat':len(TRACE),'inference_requests':0},indent=2))
    return report


async def classify(directory,provider='ollaya',model=None,min_confidence=0.6):
    from dotenv import load_dotenv
    load_dotenv(ROOT.parent/'.env',override=False)
    if not 0<=min_confidence<=1:raise ValueError('Minimum classification confidence must be between zero and one')
    if (directory/'profile.json').exists():raise ValueError('Profile already exists; use a new discovery directory to preserve prior hypotheses')
    report=json.loads((directory/'discovery.json').read_text());verify_discovery(directory,report)
    model,transport=inference(provider,model)
    recorder=RecordedTransport(transport,directory/'classification-inference.jsonl')
    player=JevPlayer(model=model,transport=recorder)
    judgments=[]
    classification={'schema':'atari-classification-v1','status':'in-progress','provider':provider,'model':model,
                    'minimum_confidence':min_confidence,'roles':judgments,
                    'note':'Confidence threshold is an experimental abstention policy, not a correctness guarantee.'}
    def save_classification():
        (directory/'classification.json').write_text(json.dumps(classification,indent=2))
    save_classification()
    for obj in report['candidates']:
        state={'game':report['game'],'game_goal':GAMES[report['game']].goal,
               'candidate':{k:obj[k] for k in ('id','palette','starting_box','signature','joystick_response_vs_noop','observed_motion_bounds')},
               'coordinate_space':'160x210 native pixels; y increases downward',
               'limits':report['coverage']}
        body={'model':model,'state':state,'questions':{'role':{'type':'choice',
            'instructions':'Classify this initial-load pixel candidate using its starting_box, sprite signature and response to bounded joystick probes versus noop. Player needs directional control response; enemy motion is not necessarily joystick control. Bottom display blocks may be HUD, while immobility alone cannot identify a rock. Use unknown when evidence is insufficient. These are role hypotheses, not ground truth.',
            'criteria':ROLES}}}
        try:
            response=await player.request(body)
            answer=player.validate_choice(response['answers']['role'],ROLES)
        except Exception as exc:
            classification.update(status='safety-hold',safety_fallback=safety_report(exc))
            save_classification()
            return classification
        judgments.append({'object_id':obj['id'],'palette':obj['palette'],'starting_box':obj['starting_box'],
                          'role':answer['choice'] if answer['confidence']>=min_confidence else 'unknown',
                          'answer':answer})
        save_classification()
    identified=[{'id':j['object_id'],'role':j['role'],'starting_box':j['starting_box']} for j in judgments]
    enough=sum(j['role']=='player' for j in judgments)==1 and any(j['role']=='enemy' for j in judgments)
    if not enough:
        classification.update(status='observation-only',safety_fallback={
            'kind':'unusable-classification','action':'observe-only-no-controller-activation',
            'automatic_hosted_fallback':False,'retry':'Improve probes/model or explicitly classify with --provider jev'})
        save_classification()
        print(json.dumps({'status':classification['status'],'roles':[(j['object_id'],j['role']) for j in judgments],
                          'safety_fallback':classification['safety_fallback']},indent=2))
        return classification
    state={'game':report['game'],'roles':identified,
           'controls':'Four-direction digging, facing and fire pump; fire can restart at title screen. Code must suppress it outside active-play evidence.',
           'limits':'Incomplete palette observations; rocks/ghosts/terminal signals uncalibrated. Code owns freshness, geometry, clocks and input release.'}
    body={'model':model,'state':state,'questions':{
        'strategy':{'type':'choice','instructions':'Which bounded Dig Dug controller strategy is supported by these initial-load role hypotheses? Tunnel toward an observed enemy, face it and pump only in an aligned candidate tunnel. Select observe if player/enemies are not sufficiently identified. This chooses a reusable strategy, not a future action or reset permission.',
                    'criteria':{'tunnel-pump':'Fresh native geometry can drive short guarded tunnel navigation and aligned pumping','observe':'Insufficient roles; release controls and gather more evidence'}},
        'cycle':{'type':'choice','instructions':'Choose a bounded fresh-frame controller cycle for close-contact Dig Dug pursuit/pumping. This is not a game reset; code will enforce the interval.',
                 'criteria':{'urgent':'6-frame fresh-geometry cycle for contact/pump control','normal':'18-frame fresh-geometry cycle for slower navigation','wait':'30-frame wait; no reliable active control','patient':'60-frame observation-only wait'}}}}
    try:
        result=await player.request(body)
        strategy=player.validate_choice(result['answers']['strategy'],body['questions']['strategy']['criteria'])
        cycle=player.validate_choice(result['answers']['cycle'],body['questions']['cycle']['criteria'])
    except Exception as exc:
        classification.update(status='safety-hold',safety_fallback=safety_report(exc));save_classification()
        return classification
    if strategy['choice']=='observe' or strategy['confidence']<min_confidence:
        classification.update(status='observation-only',safety_fallback={'kind':'unsupported-strategy',
            'action':'observe-only-no-controller-activation','automatic_hosted_fallback':False})
        save_classification();return classification
    profile={'schema':'atari-discovered-profile-v1','game':report['game'],'challenge_id':report['challenge']['challenge_id'],
             'discovery_sha256':digest((directory/'discovery.json').read_bytes()),'provider':provider,'model':model,
             'roles':judgments,'strategy':strategy,'cycle':cycle,
             'note':'Cached typed initial-load hypotheses, not per-frame Jev pixel monitoring. Runtime code must independently remeasure and guard every action.'}
    (directory/'profile.json').write_text(json.dumps(profile,indent=2))
    classification.update(status='classified',profile_sha256=digest((directory/'profile.json').read_bytes()))
    save_classification()
    print(json.dumps({'provider':provider,'roles':[(j['object_id'],j['role']) for j in judgments],'strategy':strategy['choice'],'cycle':cycle['choice']},indent=2))
    return profile


def verify_discovery(directory, report=None):
    directory=Path(directory)
    report=report or json.loads((directory/'discovery.json').read_text())
    if report.get('schema')!='atari-discovery-v1' or report.get('repeatable') is not True:
        raise ValueError('Discovery probes are not repeatable')
    if len(report.get('repeats',[]))!=2 or any(len(r)!=len(TRACE) for r in report['repeats']):
        raise ValueError('Discovery needs two complete bounded probe repeats')
    for a,b in zip(*report['repeats']):
        if a['start_sha256']!=b['start_sha256'] or a['end_sha256']!=b['end_sha256']:
            raise ValueError('Discovery repeat hashes disagree')
    for repeat in report['repeats']:
        for row,(name,buttons) in zip(repeat,TRACE):
            if row['probe']!=name or row['buttons']!=buttons or type(row['action_frames']) is not int or not 1<=row['action_frames']<=60:
                raise ValueError('Discovery probe contract changed')
            for prefix in ('start','end'):
                file=(directory/row[prefix+'_evidence']).resolve()
                if not file.is_relative_to(directory.resolve()) or digest(file.read_bytes())!=row[prefix+'_sha256']:
                    raise ValueError('Discovery snapshot changed')
    return report


def verified_profile(directory,metadata):
    directory=Path(directory);report=verify_discovery(directory)
    profile=json.loads((directory/'profile.json').read_text())
    classification=json.loads((directory/'classification.json').read_text())
    if classification.get('status')!='classified' or classification.get('profile_sha256')!=digest((directory/'profile.json').read_bytes()) or classification['roles']!=profile['roles']:
        raise ValueError('Discovery classification/profile binding changed')
    if profile.get('schema')!='atari-discovered-profile-v1' or profile.get('game')!='dig-dug':
        raise ValueError('Only experimental Dig Dug discovered controllers are supported')
    if profile['discovery_sha256']!=digest((directory/'discovery.json').read_bytes()):raise ValueError('Discovery profile evidence changed')
    if any(report['challenge'][k]!=metadata[k] for k in ('game','challenge_id','rom_sha256','assets_sha256','state_sha256')):
        raise ValueError('Discovery profile challenge mismatch')
    if profile['strategy']['choice']!='tunnel-pump':raise ValueError('Discovery classified this game as observation-only')
    players=[r for r in profile['roles'] if r['role']=='player']
    enemies=[r for r in profile['roles'] if r['role']=='enemy']
    if len(players)!=1 or not enemies:raise ValueError('Discovery must identify one player and enemy candidates')
    obj=next(o for o in report['candidates'] if o['id']==players[0]['object_id'])
    controlled=[k for k,v in obj['joystick_response_vs_noop'].items() if k in ('left','right','up','down') and v and abs(v['dx'])+abs(v['dy'])>=1]
    if len(controlled)<2:raise ValueError('Classified player lacks measured joystick response')
    # The existing ROM-specific pixel detector independently cross-checks this
    # bootstrap hypothesis. Discovery cannot replace geometry with confidence.
    from .digdug import geometry
    initial=geometry((directory/report['repeats'][0][0]['start_evidence']).read_bytes())
    if not initial['player'] or initial['player']['box']!=players[0]['starting_box']:
        raise ValueError('Classified player disagrees with the native bootstrap detector')
    return profile,report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    probe=sub.add_parser('probe');probe.add_argument('challenge',type=Path);probe.add_argument('--out',type=Path,required=True)
    probe.add_argument('--visible',action='store_true');probe.add_argument('--frames',type=int,default=30)
    judge=sub.add_parser('classify');judge.add_argument('directory',type=Path)
    judge.add_argument('--provider',choices=('ollaya','jev'),default='ollaya');judge.add_argument('--model')
    judge.add_argument('--min-confidence',type=float,default=0.6,help='Experimental abstention threshold, not proof of correct roles')
    args=parser.parse_args()
    if args.command=='probe':asyncio.run(discover(args.challenge,args.out,args.visible,args.frames))
    else:asyncio.run(classify(args.directory,args.provider,args.model,args.min_confidence))
