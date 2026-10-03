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
from .execution import FrameStamp, DecisionEnvelope
from .transports import inference, ollaya_manifest
from .progress import endpoint, save as save_progress


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
    load_dotenv(ROOT.parent/'.env',override=False)
    args.out.mkdir(parents=True,exist_ok=False)
    write_phase(args.out,'starting')
    provider=getattr(args,'provider','ollaya')
    model,transport=inference(provider,getattr(args,'model',None))
    player=profile.player_factory(model=model,transport=transport)
    pending=None
    records=[]
    elapsed=0
    terminal_samples=0
    sample=0
    metrics=Metrics(game.id);clock=DecisionClock()
    summary={'schema':'jev-live-v1','game':game.id,'challenge_id':metadata['challenge_id'],
             'status':'incomplete','score':None,'score_verified':False,'budget_frames':None,
               'config':{'player':'jev-gates','provider':provider,'model':model,'policy_version':profile.policy_version,'timing_gate':'bounded-cycle-v1','score_reader':'exact-templates+independent-frame-repeat-v1'},
              'playback_mode':'continuous','game_completed':False}
    summary['terminal_detection']=profile.terminal_note
    if provider=='ollaya':
        summary['config']['model_manifest']=await ollaya_manifest(model)
    summary['config']['source_sha256']={name:digest((ROOT/'playjev'/name).read_bytes())
        for name in ('live.py','hud.py','runtime.py','transports.py','execution.py','timing.py','spatial.py','progress.py',profile.source)}
    summary['config']['display_sha256']={name:digest((ROOT/'games/emulatorjs'/name).read_bytes())
        for name in ('index.html','live-controls.js')}
    async with EmulatorSession(assets,rom,True,args.out/'video',1,responsive=True) as env:
        frame=None
        async def raw_capture():
            # DOM overlays are for the viewer, never input to perception/OCR.
            # WebGL canvas.toDataURL can be black once its buffer is discarded.
            # EmulatorJS exposes a read-only framebuffer PNG via the core.
            captured=await env.page.evaluate('''async()=>{
                const gm=EJS_emulator.gameManager,before=gm.getFrameNum();
                let timer;
                try {
                    const data=await Promise.race([gm.screenshot(),new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Error('Framebuffer screenshot timed out')),3000);})]);
                    return {data:Array.from(data),before,after:gm.getFrameNum()};
                } finally {clearTimeout(timer);}
            }''')
            data=bytes(captured['data'])
            return data,FrameStamp(captured['before'],captured['after'],digest(data))
        try:
            await env.frames([],40,slow=False)
            await env.restore_matching(snapshot,metadata['ready_state_sha256'])
            # The initial observation also uses the raw core, not a window-sized
            # screenshot. Exactly one setup frame processes the screenshot command.
            await env.page.evaluate('()=>{window.initialCapture=EJS_emulator.gameManager.screenshot();}')
            await env.frames([],1,slow=False)
            initial=bytes(await env.page.evaluate('async()=>Array.from(await window.initialCapture)'))
            summary['observation_setup_frames']=1
            summary['initial_frame_sha256']=digest(initial)
            frame=initial
            (args.out/'start.png').write_bytes(initial)
            await env.page.evaluate('window.installLiveControls()')
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
            origin=await env.page.evaluate('EJS_emulator.gameManager.getFrameNum()')
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
                    frame,stamp=await raw_capture()
                    number=stamp.after
                    elapsed=number-origin
                    current=profile.observe(frame)
                    profile.track(previous,current,max(1,number-previous_frame))
                    await env.page.evaluate('o=>window.drawTracking(o)',{**profile.overlay(current),'capture_frame':stamp.before,'source_size':[160,210]})
                    # Three consecutive non-black observations, never a missing
                    # player sprite, are a stop candidate; not a verified death.
                    terminal_samples=terminal_samples+1 if profile.terminal_candidate(current) else 0
                    if terminal_samples>=3:
                        summary['game_over_candidate']={'game_frame':elapsed,'reason':'three-background-color-observations','verified':False}
                        summary['stop_reason']='suspected-game-over'
                        break
                    if args.seconds and time.monotonic()-started>=args.seconds:
                        summary['stop_reason']='explicit-smoke-test-cap'
                        break
                    state={'game':summary['game'],'game_frame':elapsed,'action_frames':30,'current':current,'previous':previous,'emulator_paused_during_inference':False}
                    if pending and pending.done():
                        try:
                            decision=pending.result()
                        except Exception:
                            metrics.failed+=1
                            raise
                        age=elapsed-request_frame
                        rejection=envelope.reject_reason(number,args.out.name,0)
                        applied=rejection is None and not current.get('life_indicator_visible',False)
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
                        execution_frame=execution.get('frame',number)
                        age=execution_frame-envelope.source.before
                        record={'step':len(records),'game_frame':request_frame,'applied_at_frame':execution_frame-origin,
                                 'age_frames':age,'applied':applied,'collision_veto':veto,'proposed_choice':choice,'executed_choice':choice if applied else 'noop','decision':decision,
                                 'envelope':envelope.json(),'execution':execution,
                                'latency_s':time.monotonic()-request_started,
                                'video_time_s':request_video,'action_video_time_s':time.monotonic()-env.started_wall}
                        cycle=decision['response']['answers']['cycle']
                        record['accuracy_checks']={key:decision['response']['answers'][key] for key in ('perception_check','projection_check')}
                        decision.setdefault('components',{})['cycle']=clock.restart(elapsed,cycle)
                        metrics.record(record)
                        records.append(record);log.write(json.dumps(record)+'\n');log.flush()
                        pending=None
                    if pending is None and clock.due(elapsed):
                        envelope=DecisionEnvelope(args.out.name,len(records),stamp)
                        request_frame=stamp.before-origin;request_video=time.monotonic()-env.started_wall
                        request_started=time.monotonic();player.decision_timing=clock.state(elapsed)
                        transform=await env.page.evaluate('window.trackingTransform()')
                        if transform is None:
                            raise ValueError('Renderer viewport unavailable; projection cannot be verified')
                        player.accuracy_evidence=spatial_evidence(current,transform['canvas_rect'],content=transform['content_rect'])
                        pending=asyncio.create_task(player.decide(state,game))
                        metrics.start_request()
                    (args.out/f'frame-{sample:04}.png').write_bytes(frame)
                    frame_log.write(json.dumps({'evidence':f'frame-{sample:04}.png','before':stamp.before,'after':stamp.after,'sha256':stamp.sha256})+'\n');frame_log.flush()
                    sample+=1
                    snapshot=metrics.snapshot(current,elapsed,pending is not None,clock)
                    metrics.write(args.out,snapshot)
                    await env.page.evaluate('text=>{const panel=document.getElementById("metrics");if(panel)panel.textContent=text;}',snapshot['ascii'])
                    previous,previous_frame=current,number
                    await asyncio.sleep(0.1)
            finally:
                log.close();frame_log.close()
            summary['status']='stopped'
            summary.setdefault('stop_reason','user-stop')
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
            if not env.page.is_closed():
                with suppress(BrowserError):
                    await env.page.evaluate('()=>{window.releaseLive?.();EJS_emulator.pause();}')
            if pending:
                if not pending.done():
                    metrics.cancelled+=1
                    pending.cancel()
                await asyncio.gather(pending,return_exceptions=True)
            if frame is not None:
                (args.out/'final.png').write_bytes(frame)
                summary['endpoint']=endpoint(game.id,profile.observe(frame),stamp if 'stamp' in locals() else None,
                                             origin if 'origin' in locals() else 0,digest(frame))
            summary['game_frames']=elapsed
            summary['decisions']=len(records)
            summary['metrics']=metrics.counters()
            metrics.write(args.out,metrics.snapshot(previous if 'previous' in locals() else {},elapsed,False,clock))
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
            (args.out/'summary.json').write_text(json.dumps(summary,indent=2))
            write_phase(args.out,'failed',error=summary['score_error'])
            raise
    write_phase(args.out,'failed' if summary.get('error') else 'saved',error=summary.get('error'))
    save_progress(args.out)
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
    args=p.parse_args()
    # Counters belong inside the coroutine's local scope.
    asyncio.run(play(args))
