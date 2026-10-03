"""One raw framebuffer capture contract for live play and paused diagnostics."""
from .challenge import digest
from .execution import FrameStamp


async def capture(env, paused=False):
    # Do NOT return the screenshot Promise here: paused cores require a measured
    # setup callback before the command can complete. Native PNGs exclude overlays.
    await env.page.evaluate('''()=>{
        const gm=EJS_emulator.gameManager;
        window.nativeProbe={before:gm.getFrameNum(),image:gm.screenshot()};
    }''')
    if paused:await env.frames([],1,slow=False)
    result=await env.page.evaluate('''async()=>{
        let timer;
        try {
            const data=await Promise.race([window.nativeProbe.image,new Promise((_,reject)=>{
                timer=setTimeout(()=>reject(new Error('Framebuffer screenshot timed out')),3000);
            })]);
            return {data:Array.from(data),before:window.nativeProbe.before,after:EJS_emulator.gameManager.getFrameNum()};
        } finally {clearTimeout(timer);delete window.nativeProbe;}
    }''')
    data=bytes(result['data'])
    return data,FrameStamp(result['before'],result['after'],digest(data))
