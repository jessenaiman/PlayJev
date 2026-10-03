"""Continuous Space Invaders, one pending Jev request; Start/Stop in browser."""
import argparse
import asyncio
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from .challenge import EmulatorSession, GatedJevPlayer, GAMES, ROOT, digest
from .invaders import geometry, motion
from .hud import collect


async def play(args):
    metadata = json.loads((args.challenge/'challenge.json').read_text())
    if metadata['game']!='space-invaders':
        raise ValueError('Continuous tracking currently supports Space Invaders')
    rom, assets = Path(metadata['rom_path']), Path(metadata['assets_path'])
    from .challenge import asset_digest
    snapshot=(args.challenge/'start.state').read_bytes()
    if digest(rom.read_bytes())!=metadata['rom_sha256'] or asset_digest(assets)!=metadata['assets_sha256'] or digest(snapshot)!=metadata['state_sha256']:
        raise ValueError('Challenge bytes changed')
    load_dotenv(ROOT.parent/'.env',override=False)
    args.out.mkdir(parents=True,exist_ok=False)
    player=GatedJevPlayer()
    pending=None
    records=[]
    elapsed=0
    terminal_samples=0
    sample=0
    summary={'schema':'jev-live-v1','game':'space-invaders','challenge_id':metadata['challenge_id'],
             'status':'incomplete','score':None,'score_verified':False,'budget_frames':None,
             'config':{'player':'jev-gates','model':'jev-latest','policy_version':'continuous-compact-v1'},
             'playback_mode':'continuous','game_completed':False}
    async with EmulatorSession(assets,rom,True,args.out/'video',1) as env:
        async def raw_capture():
            # DOM overlays are for the viewer, never input to perception/OCR.
            # WebGL canvas.toDataURL can be black once its buffer is discarded.
            # EmulatorJS exposes a read-only framebuffer PNG via the core.
            data=await env.page.evaluate("async()=>Array.from(await Promise.race([EJS_emulator.gameManager.screenshot(),new Promise((_,reject)=>setTimeout(()=>reject(new Error('Framebuffer screenshot timed out')),3000))]))")
            return bytes(data)
        try:
            await env.frames([],40,slow=False)
            await env.restore_matching(snapshot,metadata['ready_state_sha256'])
            initial=await env.capture()  # setup is paused and overlay is empty
            frame=initial
            (args.out/'start.png').write_bytes(initial)
            await env.page.evaluate('''() => {
                window.liveRunning=false;window.liveStopped=false;window.liveButtons=[];
                const status=document.getElementById('status');status.textContent='Continuous mode — Start plays one attempt. Boxes are pixel estimates; dashed lines are predicted laser motion.';
                const start=document.createElement('button');start.textContent='Start Jev';
                const stop=document.createElement('button');stop.textContent='Stop & save';
                const full=document.createElement('button');full.textContent='Fullscreen';
                full.onclick=async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else await document.documentElement.requestFullscreen();}catch(error){full.textContent='Fullscreen unavailable';}};
                status.append(start,stop,full);
                window.releaseLive=()=>{clearTimeout(window.liveTimer);for(const b of window.liveButtons)EJS_emulator.gameManager.simulateInput(0,b,0);window.liveButtons=[];};
                start.onclick=()=>{if(window.liveRunning||window.liveStopped)return;window.liveRunning=true;EJS_emulator.play();};
                stop.onclick=()=>{window.releaseLive();EJS_emulator.pause();window.liveStopped=true;};
                window.applyLive=({buttons,rest,frames})=>{
                    window.releaseLive();const gm=EJS_emulator.gameManager;
                    window.liveButtons=buttons;for(const b of buttons)gm.simulateInput(0,b,1);
                    const end=gm.getFrameNum()+frames;
                    const tick=()=>{
                        if(window.liveStopped)return;
                        if(gm.getFrameNum()<end){window.liveTimer=setTimeout(tick,8);return;}
                        window.releaseLive();window.liveButtons=rest;for(const b of rest)gm.simulateInput(0,b,1);
                        window.liveTimer=setTimeout(window.releaseLive,500);
                    };tick();
                };
            }''')
            print('Browser ready. Click Start Jev; Stop & save ends this single attempt.',flush=True)
            if args.autostart:
                await env.page.get_by_role('button',name='Start Jev',exact=True).click()
            await env.page.wait_for_function('window.liveRunning || window.liveStopped',timeout=0)
            origin=await env.page.evaluate('EJS_emulator.gameManager.getFrameNum()')
            previous=geometry(initial)
            previous_frame=origin
            started=time.monotonic()
            log=(args.out/'decisions.jsonl').open('w')
            try:
                while not await env.page.evaluate('window.liveStopped'):
                    number=await env.page.evaluate('EJS_emulator.gameManager.getFrameNum()')
                    elapsed=number-origin
                    frame=await raw_capture()
                    current=geometry(frame)
                    current['projectile_motion']=motion(previous,current, max(1,number-previous_frame))
                    await env.page.evaluate('o=>window.drawTracking(o)',current)
                    # Three consecutive non-black observations, never a missing
                    # player sprite, are a stop candidate; not a verified death.
                    terminal_samples=terminal_samples+1 if not current['background_black'] else 0
                    if terminal_samples>=3:
                        summary['game_over_candidate']={'game_frame':elapsed,'reason':'three-background-color-observations','verified':False}
                        summary['stop_reason']='suspected-game-over'
                        break
                    if args.seconds and time.monotonic()-started>=args.seconds:
                        summary['stop_reason']='explicit-smoke-test-cap'
                        break
                    state={'game':summary['game'],'game_frame':elapsed,'action_frames':30,'current':current,'previous':previous,'emulator_paused_during_inference':False}
                    if pending and pending.done():
                        decision=pending.result()
                        age=elapsed-request_frame
                        applied=age<=60 and not current['life_indicator_visible']
                        choice=decision['choice']
                        # Revalidate motion against the latest geometry. These
                        # are observed-state predictions, not savestate rollouts.
                        px=(current['player']['box'][0]+current['player']['box'][2])/2 if current['player'] else None
                        direction='left' if choice.startswith('left') else 'right' if choice.startswith('right') else 'stay'
                        speed={'left':-0.5,'right':0.5,'stay':0}[direction]
                        veto=px is None or (direction=='left' and px<=14) or (direction=='right' and px>=146)
                        for laser in current['projectile_motion']:
                            if laser['direction']=='up':continue
                            vy=laser['vy'] if laser['direction']=='down' else 0.4
                            impact=max(0,(183-laser['y'])/vy) if vy and vy>0 else float('inf')
                            future=max(12,min(148,px+speed*min(impact,18))) if px is not None else None
                            if impact<=42 and future is not None and abs(future-laser['x'])<=6:veto=True
                        if veto or px is None:
                            applied=False
                        if applied:
                            await env.page.evaluate('window.applyLive',{'buttons':GAMES['space-invaders'].actions[choice],
                                'rest':GAMES['space-invaders'].actions.get(decision.get('rest_choice','noop'),[]),
                                'frames':min(30,decision.get('movement_frames',30))})
                        record={'step':len(records),'game_frame':request_frame,'applied_at_frame':elapsed,
                                'age_frames':age,'applied':applied,'collision_veto':veto,'decision':decision,
                                'video_time_s':request_video,'action_video_time_s':time.monotonic()-env.started_wall}
                        records.append(record);log.write(json.dumps(record)+'\n');log.flush()
                        pending=None
                    if pending is None:
                        request_frame=elapsed;request_video=time.monotonic()-env.started_wall
                        pending=asyncio.create_task(player.decide(state,GAMES['space-invaders']))
                    (args.out/f'frame-{sample:04}.png').write_bytes(frame)
                    sample+=1
                    previous,previous_frame=current,number
                    await asyncio.sleep(0.1)
            finally:
                log.close()
            summary['status']='stopped'
            summary.setdefault('stop_reason','user-stop')
        finally:
            if pending:
                pending.cancel()
            if not env.page.is_closed():
                await env.page.evaluate('()=>{window.releaseLive?.();EJS_emulator.pause();}')
                (args.out/'final.png').write_bytes(frame)
            summary['game_frames']=elapsed
            summary['decisions']=len(records)
            (args.out/'summary.json').write_text(json.dumps(summary,indent=2))
    videos=list((args.out/'video').glob('*.webm'))
    if videos:videos[0].rename(args.out/'replay.webm')
    from .challenge import replay_html
    replay_html(args.out,summary,records)
    await collect(args.out)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('challenge',type=Path)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--seconds',type=float,help='Optional wall-time smoke-test cap; default has no time limit')
    p.add_argument('--autostart',action='store_true',help='For smoke checks; default waits for your click')
    args=p.parse_args()
    # Counters belong inside the coroutine's local scope.
    asyncio.run(play(args))
