"""Paused restored-state pixel checks for the emulator display transform.

This is a diagnostic, not a gameplay attempt or leaderboard entry.
"""
import argparse
import asyncio
import io
import json
from pathlib import Path

from PIL import Image
from .challenge import EmulatorSession, digest
from .crackpots import geometry, overlay
from .spatial import evidence
from .native import capture


def gold_box(image, expected, margin=12):
    """Locate gardener-colored pixels near the expected rendered player."""
    x,y,x2,y2=expected
    pixels=[]
    for py in range(max(0,int(y)-margin),min(image.height,int(y2)+margin+1)):
        for px in range(max(0,int(x)-margin),min(image.width,int(x2)+margin+1)):
            r,g,b=image.getpixel((px,py))[:3]
            if r>200 and 150<g<200 and 60<b<110:
                pixels.append((px,py))
    if not pixels:
        raise AssertionError('No rendered gardener-colored pixels near projection')
    return [min(p[0] for p in pixels),min(p[1] for p in pixels),
            max(p[0] for p in pixels)+1,max(p[1] for p in pixels)+1]


async def check(args):
    metadata=json.loads((args.challenge/'challenge.json').read_text())
    if metadata['game']!='crackpots':
        raise ValueError('This pixel probe is calibrated for Crackpots gardener colors')
    snapshot=(args.challenge/'start.state').read_bytes()
    args.out.mkdir(parents=True,exist_ok=True)
    checks=[]
    for dpr in (1,2):
        async with EmulatorSession(Path(metadata['assets_path']),Path(metadata['rom_path']),
                                   speed=1,device_scale_factor=dpr) as env:
            await env.frames([],40,slow=False)
            for width,height in ((640,480),(960,540),(390,844),(1440,900)):
                await env.page.set_viewport_size({'width':width,'height':height})
                await env.restore_matching(snapshot,metadata['ready_state_sha256'])
                raw,_=await capture(env,paused=True)
                current=geometry(raw)
                await env.page.evaluate('o=>window.drawTracking(o)',overlay(current))
                # Let renderer and ResizeObserver settle at this paused state.
                await env.page.evaluate('()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
                transform=await env.page.evaluate('window.trackingTransform()')
                assert transform is not None
                ev=evidence(current,transform['canvas_rect'],content=transform['content_rect'])
                assert ev['code_bounds_valid']
                await env.page.evaluate('document.getElementById("tracking").style.visibility="hidden"')
                clean=await env.page.locator('canvas.ejs_canvas').screenshot()
                image=Image.open(io.BytesIO(clean)).convert('RGB')
                canvas=transform['canvas_rect']
                # Locator PNG coordinates start at the canvas and use device pixels.
                expected=[(v-canvas['left' if i%2==0 else 'top'])*dpr
                          for i,v in enumerate(ev['projected_player_box'])]
                actual=gold_box(image,expected,margin=12*dpr)
                error=max(abs(a-b)/dpr for a,b in zip(actual,expected))
                assert error<=2,(width,height,dpr,actual,expected,error)
                await env.page.evaluate('document.getElementById("tracking").style.visibility="visible"')
                name=f'{width}x{height}-dpr{dpr}'
                await env.page.screenshot(path=str(args.out/f'{name}.png'))
                checks.append({'viewport':[width,height],'dpr':dpr,'raw_sha256':digest(raw),
                               'transform':transform,'expected_device_box':expected,
                               'actual_device_box':actual,'max_error_css_pixels':error})
    assert len({c['raw_sha256'] for c in checks})==1
    result={'kind':'paused-display-diagnostic','checks':checks,'passed':True,
            'limitations':'Restored-frame gardener pixel alignment; not full gameplay tracking accuracy or an actual Omarchy tiling/fullscreen interaction test.'}
    (args.out/'display-check.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({'checks':len(checks),'passed':True,'max_error_css_pixels':max(c['max_error_css_pixels'] for c in checks)},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('challenge',type=Path)
    parser.add_argument('--out',type=Path,required=True)
    asyncio.run(check(parser.parse_args()))
