"""Replay a bounded input trace twice from a checkpoint, without inference."""
import argparse
import asyncio
import json
from pathlib import Path
from .challenge import EmulatorSession, asset_digest, digest
from .checkpoints import verify
from .runtime import registry
from .native import capture


async def check(challenge, source, out, visible=False):
    metadata=json.loads((challenge/'challenge.json').read_text())
    checkpoint=verify(source,metadata)
    rom,assets=Path(metadata['rom_path']),Path(metadata['assets_path'])
    if digest(rom.read_bytes())!=metadata['rom_sha256'] or asset_digest(assets)!=metadata['assets_sha256']:
        raise ValueError('Challenge ROM/assets changed')
    out.mkdir(parents=True,exist_ok=False)
    profile=registry()[metadata['game']]
    # This is a deliberately fixed calibration trace, NOT a successful AI policy.
    trace=[[],[6],[5],[7],[4],[0],[]]
    attempts=[]
    for repeat in range(2):
        directory=out/f'repeat-{repeat}';directory.mkdir()
        async with EmulatorSession(assets,rom,visible,directory/'video',speed=1) as env:
            await env.frames([],40,slow=False)
            _,callbacks=await env.restore_matching((source/'checkpoint.state').read_bytes(),checkpoint['ready_state_sha256'])
            rows=[]
            for step,buttons in enumerate(trace):
                await env.frames(buttons,14,slow=False)
                image,_=await capture(env,paused=True)
                ready=await env.save();name=f'frame-{step:02}.png';(directory/name).write_bytes(image)
                rows.append({'buttons':buttons,'action_frames':14,'capture_setup_frames':1,
                             'image_sha256':digest(image),'state_sha256':digest(ready),
                             'observation':profile.observe(image)})
            attempts.append({'restore_setup_callbacks':callbacks,'rows':rows})
    checks=[{'step':i,'buttons':trace[i],
             'image_equal':attempts[0]['rows'][i]['image_sha256']==attempts[1]['rows'][i]['image_sha256'],
             'state_equal':attempts[0]['rows'][i]['state_sha256']==attempts[1]['rows'][i]['state_sha256']}
            for i in range(len(trace))]
    result={'schema':'atari-resume-check-v1','source':str(source),'checkpoint':checkpoint,
            'attempts':attempts,'checks':checks,'passed':all(c['image_equal'] and c['state_equal'] for c in checks),
            'inference_requests':0,'note':'Paused fixed-input control/restore calibration, not continuous LLM gameplay, a score or a completion claim.'}
    (out/'resume-check.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({'passed':result['passed'],'paired_checks':len(checks),'inference_requests':0},indent=2))
    if not result['passed']:raise RuntimeError('Resume input trace was not replayable')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('challenge',type=Path);parser.add_argument('source',type=Path)
    parser.add_argument('--out',type=Path,required=True);parser.add_argument('--visible',action='store_true')
    args=parser.parse_args();asyncio.run(check(args.challenge,args.source,args.out,args.visible))
