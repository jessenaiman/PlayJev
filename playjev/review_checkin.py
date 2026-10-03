"""Evidence packet for Jev-assisted check-in review; never executes commit/push."""
import argparse
import asyncio
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from .challenge import ROOT, JevPlayer
from .transports import inference


def command(args):
    p=subprocess.run(args,cwd=ROOT,capture_output=True,text=True)
    return {'command':args,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}


async def review(args):
    load_dotenv(ROOT.parent/'.env',override=False)
    names=command(['git','diff','--cached','--name-only'])['stdout'].splitlines()
    forbidden=[name for name in names if name.startswith(('runs/','.env')) or
               Path(name).suffix in ('.a26','.bin','.state','.webm') or '.env' in Path(name).name]
    diff=command(['git','diff','--cached'])['stdout']
    key=os.environ.get('TYPESAFE_API_KEY','')
    # Only the exact-value check is used; do not put the key or full diff in packets.
    secret_match=bool(key and key in diff)
    tests=command([sys.executable,'-m','unittest','discover','-s','tests','-q'])
    whitespace=command(['git','diff','--cached','--check'])
    branch=command(['git','branch','--show-current'])['stdout'].strip()
    remote=command(['git','remote','get-url','fork'])['stdout'].strip()
    checks={}
    for name in ('browser-check.json','resize-check.json','provider-toggle-check.json','display-check-v1/display-check.json','progress-check.json'):
        file=ROOT/'runs'/'arcade-processes'/name
        checks[name]=json.loads(file.read_text()) if file.is_file() else {'missing':True}
    smoke=ROOT/'runs'/'arcade-ollaya-cli-smoke-v1'/'summary.json'
    packet={'requested_scope':'Local arcade front page, shared adapters/scoring, viewport mapping, timing/accuracy gates, metrics and task list; last-observed endpoint ledger and score goal previews. No automatic progressive execution or checkpoint resumes. Prototype release, not completion of pending features.',
            'user_authorized_push':args.authorized,'staged_files':names,'diff_stat':command(['git','diff','--cached','--stat']),
            'tests':tests,'whitespace':whitespace,'branch':branch,'remote':remote,'browser_checks':checks,
            'smoke':json.loads(smoke.read_text()) if smoke.is_file() else {'missing':True},
            'artifact_guard':{'forbidden_paths':forbidden,'exact_credential_found':secret_match},
            'known_limits':['Crackpots game-over unvalidated','Ollaya GPU/latency limits block effective real-time play','Native alternating-player mode pending','New games and vision cookbook queued','Separate game window, not inline hosted roster','Practice goals are previews only; world/wave progress and automatic execution are not calibrated'],
            'at':datetime.now(timezone.utc).isoformat()}
    browser=checks['browser-check.json'];resize=checks['resize-check.json']
    launch=browser.get('live_launch_test',{})
    browser_ok=bool(browser.get('checks')) and isinstance(launch,dict) and launch.get('launch_from_front_page') and launch.get('stop_from_front_page') and launch.get('video_saved')
    resize_ok=bool(resize.get('checks')) and len({c.get('raw_sha256') for c in resize.get('checks',[])})==1
    display=checks['display-check-v1/display-check.json'];toggle=checks['provider-toggle-check.json']
    packet['required_evidence_checks']={'browser_launch_stop_video':bool(browser_ok),'identical_source_across_sizes':bool(resize_ok),'live_requests_observed':packet['smoke'].get('metrics',{}).get('requests',0)>0,
        'rendered_alignment':display.get('passed') is True and len(display.get('checks',[]))>=8 and all(c['max_error_css_pixels']<=2 for c in display.get('checks',[])),
        'provider_toggle_no_inference':toggle.get('no_inference_on_load_or_toggle') is True and toggle.get('live',{}).get('active_provider_pinned_on_toggle') is True and toggle.get('live',{}).get('video_saved') is True}
    progress=checks['progress-check.json']
    packet['required_evidence_checks']['practice_tracking_preview']=progress.get('endpoint_visible') is True and progress.get('no_recommendation_inference') is True and progress.get('endpoint',{}).get('capture_interval') is not None
    deterministic_ok=bool(names) and not forbidden and not secret_match and tests['returncode']==0 and whitespace['returncode']==0 and branch!='main' and remote=='https://github.com/jessenaiman/PlayJev.git' and args.authorized and all(packet['required_evidence_checks'].values())
    packet['deterministic_checks_pass']=deterministic_ok
    # Exact full evidence is retained locally. Give the verifier a bounded summary
    # of actual checks instead of feeding it every unrelated legacy config field.
    review_state={k:packet[k] for k in ('requested_scope','user_authorized_push','staged_files','branch','remote','artifact_guard','known_limits','deterministic_checks_pass','required_evidence_checks')}
    review_state['tests']={'returncode':tests['returncode'],'output':tests['stderr']}
    review_state['local_smoke']={k:packet['smoke'].get(k) for k in ('status','game_frames','metrics','score','score_verified')}
    review_state['summary_limit']='Reviews check evidence and disclosed scope, not every code line. Full packet is saved alongside this exact request.'
    body={'model':'jev-latest','state':review_state,'questions':{
        'readiness':{'type':'choice','instructions':'Does this evidence support an explicitly scoped prototype check-in and feature-branch push? Evaluate the shown tests, scope, artifact guard and disclosed limits. Ready does not certify code correctness or finish queued features. Missing evidence or failed checks requires hold.','criteria':{'ready':'Evidence supports this limited prototype check-in','hold_tests':'Tests or deterministic checks failed','hold_scope':'Wrong branch, remote, unauthorized work or excluded artifacts','hold_evidence':'Required evidence is missing or insufficient'}},
        'limits_disclosed':{'type':'noul','instructions':'Does this packet explicitly disclose unvalidated game over, blocked Ollaya and queued games/vision work rather than claiming them complete?'}}}
    model,transport=inference(args.provider,args.model)
    body['model']=model
    player=JevPlayer(model=model,transport=transport)
    try:
        response=await player.request(body)
        answer=player.validate_choice(response['answers']['readiness'],body['questions']['readiness']['criteria'])
    except Exception as exc:
        response={'error':f'{type(exc).__name__}: {exc}'}
        answer={'choice':'hold_evidence'}
    result={'packet':packet,'request':body,'response':response,'deterministic_checks_pass':deterministic_ok,
            'review_choice':answer['choice'],'ready_for_explicit_git_commands':deterministic_ok and answer['choice']=='ready',
            'provider':args.provider,'note':'Selected typed model reviews provided evidence; code ran tests. This program does not execute commit or push.'}
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in ('packet','request','response')},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--authorized',action='store_true')
    parser.add_argument('--out',type=Path,default=ROOT/'runs'/'arcade-processes'/'checkin-review.json')
    parser.add_argument('--provider',choices=('ollaya','jev'),default='ollaya');parser.add_argument('--model')
    asyncio.run(review(parser.parse_args()))
