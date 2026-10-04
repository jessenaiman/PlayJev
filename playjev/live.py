"""Continuous Atari adapters, one pending Jev request; Start/Stop in browser."""
import argparse
import asyncio
import json
import time
from contextlib import suppress
from pathlib import Path
from dotenv import load_dotenv
from playwright.async_api import Error as BrowserError
from .challenge import EmulatorSession, GAMES, ROOT, digest
from .runtime import registry
from .metrics import Metrics, write_phase
from .timing import DecisionClock
from .spatial import evidence as spatial_evidence
from .execution import DecisionEnvelope
from .transports import inference, ollaya_manifest, RecordedTransport, SafetyHold, safety_report
from .progress import endpoint, save as save_progress
from .practice import Goal, validate as validate_practice
from .checkpoints import capture as capture_checkpoint
from .hud import read_score, LiveScore
from .native import capture as native_capture
from .events import EventLog, action_class
from .usage import token_usage, player_identity
from .participation import probe_control


async def play(args):
    metadata = json.loads((args.challenge/'challenge.json').read_text())
    profiles=registry()
    if metadata['game'] not in profiles:
        raise ValueError('Game does not have a continuous adapter')
    game=GAMES[metadata['game']]
    profile=profiles[game.id]
    rom, assets = Path(metadata['rom_path']), Path(metadata['assets_path'])
    from .challenge import asset_digest
    snapshot=(args.challenge/'start.state').read_bytes()
    if digest(rom.read_bytes())!=metadata['rom_sha256'] or asset_digest(assets)!=metadata['assets_sha256'] or digest(snapshot)!=metadata['state_sha256']:
        raise ValueError('Challenge bytes changed')
    practice=None;goal=None
    if getattr(args,'practice_plan',None):
        practice=validate_practice(json.loads(args.practice_plan.read_text()),metadata)
        goal=Goal(practice)
    expected=metadata['ready_state_sha256']
    if practice and practice['resume_from']:
        snapshot=(Path(practice['resume_from'])/'checkpoint.state').read_bytes()
        expected=practice['checkpoint']['ready_state_sha256']
    load_dotenv(ROOT.parent/'.env',override=False)
    args.out.mkdir(parents=True,exist_ok=False)
    write_phase(args.out,'starting')
    provider=getattr(args,'provider','ollaya')
    model,transport=inference(provider,getattr(args,'model',None))
    events=EventLog(args.out/'events.jsonl',{'kind':'llm','provider':provider,'model':model})
    transport=RecordedTransport(transport,args.out/'inference.jsonl',events)
    (args.out/'inference.jsonl').touch()
    player=profile.player_factory(model=model,transport=transport)
    auxiliary=getattr(player,'auxiliary_questions',True)
    if goal:player.practice_context=goal.context()
    pending=None
    records=[]
    elapsed=0
    terminal_samples=0
    sample=0
    metrics=Metrics(game.id);clock=DecisionClock()
    hud=LiveScore();score_state={}
    summary={'schema':'jev-live-v1','game':game.id,'challenge_id':metadata['challenge_id'],
             'status':'incomplete','score':None,'score_verified':False,'budget_frames':None,
               'config':{'player':'jev-gates','provider':provider,'model':model,'policy_version':profile.policy_version,'timing_gate':'bounded-cycle-v1','score_reader':'exact-templates+independent-frame-repeat-v1'},
              'playback_mode':'continuous','game_completed':False}
    summary['terminal_detection']=profile.terminal_note
    summary['config']['auxiliary_model_questions']=auxiliary
    summary['config']['decision_cycle']='model-choice' if auxiliary else 'code-fixed-normal-18-frames'
    summary['participant']=player_identity(summary['config'])
    summary['event_stream']='events.jsonl'
    summary['participation_required']=True
    if practice:
        summary['practice']=practice
        summary['playback_mode']='continuous-practice-resumed' if practice['resume_from'] else 'continuous-practice-fresh'
        (args.out/'practice-plan.json').write_text(json.dumps(practice,indent=2))
    if provider=='ollaya':
        summary['config']['model_manifest']=await ollaya_manifest(model)
    summary['config']['source_sha256']={name:digest((ROOT/'playjev'/name).read_bytes())
        for name in ('live.py','hud.py','runtime.py','transports.py','execution.py','timing.py','spatial.py','progress.py','practice.py','checkpoints.py','native.py','events.py','usage.py','digdug_score.py','participation.py','loss_review.py','startup.py','completion.py','recipes/startup.json','recipes/completion.json',profile.source)}
    if game.id=='crackpots':
        for name in ('crackpots_state.py','crackpots_player.py','crackpots_control.py',
                     'policies/crackpots.json','recipes/crackpots-lane.json'):
            summary['config']['source_sha256'][name]=digest((ROOT/'playjev'/name).read_bytes())
    summary['config']['display_sha256']={name:digest((ROOT/'games/emulatorjs'/name).read_bytes())
        for name in ('index.html','live-controls.js')}
    summary['config']['display_sha256']['atari-controller.js']=digest((ROOT/'games/arcade/atari-controller.js').read_bytes())
    async with EmulatorSession(assets,rom,True,args.out/'video',1,responsive=True) as env:
        frame=None
        try:
            await env.frames([],40,slow=False)
            _,setup=await env.restore_matching(snapshot,expected)
            summary['restore_setup_callbacks']=setup
            summary['canonical_restore_verified']=True
            summary['restored_state_sha256']=expected
            summary['participation']=await probe_control(env,snapshot,expected,args.out,game.id,
                resumed=bool(practice and practice['resume_from']))
            events.write('participation','session.control-verified' if summary['participation']['verified'] else 'session.unverified',proof=summary['participation'])
            from .startup import check as startup_check
            summary['startup_check']=await startup_check(args.out,summary,events=events)
            if not summary['startup_check']['passed']:
                summary['stop_reason']='unverified-player-control'
                raise ValueError('Native input-effect/start-mode check failed; no gameplay inference or score attribution')
            # The initial observation also uses the raw core, not a window-sized
            # screenshot. Exactly one setup frame processes the screenshot command.
            initial,_=await native_capture(env,paused=True)
            summary['observation_setup_frames']=1
            summary['initial_frame_sha256']=digest(initial)
            frame=initial
            (args.out/'start.png').write_bytes(initial)
            label=('RESUMED practice from '+Path(practice['resume_from']).name if practice and practice['resume_from'] else 'FRESH-START practice') if practice else None
            await env.page.evaluate('options=>window.installLiveControls(options)',{'frame_cap':practice['segment_frames'] if practice else None,'label':label})
            await env.page.evaluate('game=>{document.title="Jev Atari — "+game;}',game.id)
            print('Browser ready. Click Start Jev; Stop & save ends this single attempt.',flush=True)
            write_phase(args.out,'waiting-for-start')
            external_stop=getattr(args,'stop_file',None)
            if external_stop and external_stop.exists():
                await env.page.evaluate('window.liveStopped=true')
                summary['stop_reason']='front-page-user-stop'
            elif args.autostart:
                await env.page.get_by_role('button',name='Start Jev',exact=True).click()
            await env.page.wait_for_function('window.liveRunning || window.liveStopped',timeout=0)
            write_phase(args.out,'playing')
            origin=await env.page.evaluate('window.liveOriginFrame??EJS_emulator.gameManager.getFrameNum()')
            previous=profile.observe(initial)
            previous_frame=origin
            started=time.monotonic()
            log=(args.out/'decisions.jsonl').open('w')
            frame_log=(args.out/'frames.jsonl').open('w')
            try:
                while not await env.page.evaluate('window.liveStopped'):
                    if (args.out/'stop.request').exists() or (external_stop and external_stop.exists()):
                        summary['stop_reason']='front-page-user-stop'
                        break
                    frame,stamp=await native_capture(env)
                    number=stamp.after
                    elapsed=number-origin
                    current=profile.observe(frame)
                    profile.track(previous,current,max(1,number-previous_frame))
                    evidence=f'frame-{sample:04}.png'
                    (args.out/evidence).write_bytes(frame)
                    frame_log.write(json.dumps({'evidence':evidence,'before':stamp.before,'after':stamp.after,'sha256':stamp.sha256})+'\n');frame_log.flush()
                    sample+=1
                    score_state=hud.observe(read_score(game.id,frame),stamp,evidence)
                    events.write('native-observation','hud.supported' if score_state['score'] is not None else 'hud.unknown',
                                 source={'before':stamp.before,'after':stamp.after,'sha256':stamp.sha256,'evidence':evidence},hud=score_state)
                    if goal and goal.observe(read_score(game.id,frame),stamp,evidence,elapsed):
                        summary['stop_reason']='practice-target-achieved'
                        break
                    await env.page.evaluate('o=>window.drawTracking(o)',{**profile.overlay(current),'capture_frame':stamp.before,'source_size':[160,210]})
                    # Three profile-specific terminal candidates, never just a
                    # flickering player sprite, stop without claiming verified death.
                    terminal_samples=terminal_samples+1 if profile.terminal_candidate(current) else 0
                    if terminal_samples>=3:
                        summary['game_over_candidate']={'game_frame':elapsed,'reason':profile.terminal_reason,'verified':False}
                        summary['stop_reason']='suspected-game-over'
                        break
                    if args.seconds and time.monotonic()-started>=args.seconds:
                        summary['stop_reason']='explicit-smoke-test-cap'
                        break
                    state={'game':summary['game'],'game_frame':elapsed,'action_frames':30,'current':current,'previous':previous,'emulator_paused_during_inference':False}
                    if pending and pending.done():
                        try:
                            decision=pending.result()
                        except Exception as exc:
                            summary['safety_fallback']=exc.report if isinstance(exc,SafetyHold) else safety_report(exc)
                            metrics.finish_request('failed',summary['safety_fallback']['kind'])
                            summary['stop_reason']='inference-safety-hold'
                            await env.page.evaluate('()=>{window.releaseLive();EJS_emulator.pause();}')
                            raise
                        age=elapsed-request_frame
                        rejection=envelope.reject_reason(number,args.out.name,0)
                        applied=rejection is None and not current.get('life_indicator_visible',False)
                        await env.page.evaluate('choice=>window.lastLiveProposal=choice',decision.get('choice'))
                        choice,duration,veto=profile.prepare(current,decision)
                        if veto:
                            applied=False
                        if applied:
                            execution=await env.page.evaluate('window.applyLive',{'buttons':game.actions[choice],
                                'rest':game.actions.get(decision.get('rest_choice','noop'),[]),
                                'frames':duration,'deadline':envelope.deadline,'policy_generation':envelope.policy_generation})
                            applied=execution['applied']
                            rejection=execution.get('reason')
                        else:
                            await env.page.evaluate('window.releaseLive()')
                            execution={'applied':False,'reason':rejection or ('safety-veto' if veto else 'life-indicator')}
                            await env.page.evaluate('reason=>window.lastLiveControlReason="rejected: "+reason',execution['reason'])
                        execution_frame=execution.get('frame',number)
                        age=execution_frame-envelope.source.before
                        record={'step':len(records),'game_frame':request_frame,'applied_at_frame':execution_frame-origin,
                                 'age_frames':age,'applied':applied,'collision_veto':veto,'proposed_choice':choice,'executed_choice':choice if applied else 'noop','decision':decision,
                                 'envelope':envelope.json(),'execution':execution,
                                'latency_s':time.monotonic()-request_started,
                                'video_time_s':request_video,'action_video_time_s':time.monotonic()-env.started_wall}
                        answers=decision['response']['answers']
                        record['accuracy_checks']={key:answers[key] for key in ('perception_check','projection_check') if key in answers}
                        if auxiliary:
                            decision.setdefault('components',{})['cycle']=clock.restart(elapsed,answers['cycle'])
                        else:
                            record['cycle']=clock.restart_code(elapsed)
                        metrics.record(record)
                        records.append(record);log.write(json.dumps(record)+'\n');log.flush()
                        events.write('control','control.'+('applied.'+action_class(game.id,choice) if applied else 'rejected.'+execution['reason']),
                                     context=envelope.json(),record=record)
                        pending=None
                    ready=profile.inference_ready(current)
                    if not ready:
                        await env.page.evaluate('window.releaseLive()')
                    if pending is None and clock.due(elapsed) and ready:
                        envelope=DecisionEnvelope(args.out.name,len(records),stamp)
                        transport.context=envelope.json()
                        request_frame=stamp.before-origin;request_video=time.monotonic()-env.started_wall
                        request_started=time.monotonic();player.decision_timing=clock.state(elapsed)
                        transform=await env.page.evaluate('window.trackingTransform()')
                        if transform is None:
                            raise ValueError('Renderer viewport unavailable; projection cannot be verified')
                        player.accuracy_evidence=spatial_evidence(current,transform['canvas_rect'],content=transform['content_rect'])
                        pending=asyncio.create_task(player.decide(state,game))
                        metrics.start_request(envelope.json(),request_started)
                    buttons=await env.page.evaluate('()=>Array.isArray(window.liveButtons)?[...window.liveButtons]:null')
                    snapshot=metrics.snapshot({**current,**score_state},elapsed,pending is not None,clock,emulator_frame=number,buttons=buttons)
                    metrics.write(args.out,snapshot)
                    await env.page.evaluate('text=>{const panel=document.getElementById("metrics");if(panel)panel.textContent=text;}',snapshot['ascii'])
                    previous,previous_frame=current,number
                    await asyncio.sleep(0.1)
            finally:
                log.close();frame_log.close()
            summary['status']='stopped'
            summary.setdefault('stop_reason',await env.page.evaluate('window.liveStopReason||"user-stop"'))
        except BrowserError as exc:
            if env.page.is_closed():
                summary['status']='stopped'
                summary['stop_reason']='browser-closed; last captured frame only'
            else:
                summary['status']='incomplete'
                summary['error']=str(exc)
        except Exception as exc:
            summary['status']='incomplete'
            summary['error']=f'{type(exc).__name__}: {exc}'
        finally:
            write_phase(args.out,'stopping')
            buttons=None
            if not env.page.is_closed():
                with suppress(BrowserError):
                    await env.page.evaluate('()=>{window.releaseLive?.();EJS_emulator.pause();}')
                    buttons=await env.page.evaluate('()=>Array.isArray(window.liveButtons)?[...window.liveButtons]:null')
                    if 'origin' in locals():
                        elapsed=await env.page.evaluate('EJS_emulator.gameManager.getFrameNum()')-origin
            if pending:
                if not pending.done():
                    metrics.finish_request('cancelled','stop cancelled pending request')
                    pending.cancel()
                await asyncio.gather(pending,return_exceptions=True)
            if frame is not None:
                (args.out/'final.png').write_bytes(frame)
                summary['endpoint']=endpoint(game.id,profile.observe(frame),stamp if 'stamp' in locals() else None,
                                             origin if 'origin' in locals() else 0,digest(frame))
            summary['game_frames']=elapsed
            summary['decisions']=len(records)
            summary['metrics']=metrics.counters()
            if goal:summary['practice_result']=goal.finish(elapsed)
            if not env.page.is_closed() and summary['status']=='stopped' and not summary.get('game_over_candidate'):
                try:
                    summary['checkpoint']=await capture_checkpoint(env,args.out,metadata,origin,
                        (practice['base_frames']+summary['observation_setup_frames']) if practice and practice['resume_from'] else 0)
                except Exception as exc:
                    summary['checkpoint_error']=f'{type(exc).__name__}: {exc}'
            snapshot=metrics.snapshot({**(profile.observe(frame) if frame is not None else {}),**score_state},elapsed,False,clock,
                                      buttons=buttons,phase=summary['status'])
            metrics.write(args.out,snapshot)
            if not env.page.is_closed():
                with suppress(BrowserError):
                    await env.page.evaluate('text=>{const panel=document.getElementById("metrics");if(panel)panel.textContent=text;}',snapshot['ascii'])
            (args.out/'summary.json').write_text(json.dumps(summary,indent=2))
            write_phase(args.out,'recording')
    videos=list((args.out/'video').glob('*.webm'))
    if videos:videos[0].rename(args.out/'replay.webm')
    from .challenge import replay_html
    replay_html(args.out,summary,records)
    save_progress(args.out)  # retain endpoint even if subsequent HUD review fails
    if (args.out/'final.png').exists():
        write_phase(args.out,'scoring')
        try:
            await profile.score_collector(args.out)
        except Exception as exc:
            summary=json.loads((args.out/'summary.json').read_text())
            summary['score_error']=f'{type(exc).__name__}: {exc}'
            summary.update(score=None,score_verified=False,attribution_hold='Score verification failed')
            (args.out/'summary.json').write_text(json.dumps(summary,indent=2))
            write_phase(args.out,'failed',error=summary['score_error'])
    write_phase(args.out,'failed' if summary.get('error') else 'saved',error=summary.get('error'))
    summary=json.loads((args.out/'summary.json').read_text())
    from .loss_review import review
    write_phase(args.out,'reviewing')
    try:
        await review(args.out,events=events)
    except Exception as exc:
        summary=json.loads((args.out/'summary.json').read_text())
        summary['loss_review_error']=f'{type(exc).__name__}: {exc}'
        summary['completion_check']={'passed':False,'reason':'End evidence/review could not be validated'}
        summary['evaluation_outcome']='failed-validation'
        (args.out/'improvement.md').write_text('# End-of-attempt validation failure\n\nNo gameplay recommendation is accepted.\n\n1. Recheck the saved native-frame hashes and capture intervals; do not alter or delete evidence.\n2. Return this report to the parent to repair the specific lifecycle/score reader, not scan the project.\n')
        summary['loss_review']={'status':'unavailable','document':'improvement.md','route':'parent'}
        (args.out/'summary.json').write_text(json.dumps(summary,indent=2))
    summary=json.loads((args.out/'summary.json').read_text())
    summary['token_usage']=token_usage(args.out,summary)
    (args.out/'summary.json').write_text(json.dumps(summary,indent=2))
    events.write('saved','attempt.incomplete' if summary.get('error') else 'attempt.saved',
                 score=summary.get('score'),token_usage=summary['token_usage'],stop_reason=summary.get('stop_reason'))
    replay_html(args.out,summary,records)
    save_progress(args.out)
    write_phase(args.out,'failed' if summary.get('error') or summary.get('score_error') else 'saved',error=summary.get('error') or summary.get('score_error'))
    if summary.get('error'):
        raise RuntimeError(summary['error'])


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('challenge',type=Path)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--seconds',type=float,help='Optional wall-time smoke-test cap; default has no time limit')
    p.add_argument('--autostart',action='store_true',help='For smoke checks; default waits for your click')
    p.add_argument('--stop-file',type=Path,help='Front-page cooperative Stop & save marker')
    p.add_argument('--provider',choices=('ollaya','jev'),default='ollaya',help='Default is local Ollaya CLI; hosted Jev requires explicit selection')
    p.add_argument('--model',help='Provider model name (default kev:0.8b or jev-latest)')
    p.add_argument('--practice-plan',type=Path,help='Explicit single-segment practice plan; resumes are verified and unranked')
    args=p.parse_args()
    # Counters belong inside the coroutine's local scope.
    asyncio.run(play(args))
