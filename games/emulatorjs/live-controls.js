// Code owns frame deadlines and button release. No model can reset the game.
window.installLiveControls = () => {
    window.liveRunning=false;window.liveStopped=false;window.liveButtons=[];
    window.livePolicyGeneration=0;
    const status=document.getElementById('status');
    status.textContent='Continuous mode — one attempt. Boxes are observed pixel estimates; dashed paths are predictions.';
    const start=document.createElement('button');start.textContent='Start Jev';
    const stop=document.createElement('button');stop.textContent='Stop & save';
    const full=document.createElement('button');full.textContent='Fullscreen';
    full.onclick=async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else await document.documentElement.requestFullscreen();}catch(error){full.textContent='Fullscreen unavailable';}};
    status.append(start,stop,full);
    window.releaseLive=()=>{
        clearTimeout(window.liveTimer);
        for(const b of window.liveButtons)EJS_emulator.gameManager.simulateInput(0,b,0);
        window.liveButtons=[];
    };
    start.onclick=()=>{if(window.liveRunning||window.liveStopped)return;window.liveRunning=true;EJS_emulator.play();};
    stop.onclick=()=>{window.releaseLive();EJS_emulator.pause();window.liveStopped=true;};
    window.applyLive=({buttons,rest,frames,deadline,policy_generation})=>{
        window.releaseLive();
        const gm=EJS_emulator.gameManager,now=gm.getFrameNum();
        const reject=reason=>({applied:false,reason,frame:now});
        if(window.liveStopped||!window.liveRunning)return reject('stopped');
        if(policy_generation!==window.livePolicyGeneration)return reject('changed-policy');
        if(!Number.isFinite(deadline)||now>deadline)return reject('stale');
        if(!Number.isInteger(frames)||frames<1||frames>30)return reject('invalid-duration');
        const permitted=new Set([0,4,5,6,7]);
        if(!Array.isArray(buttons)||!Array.isArray(rest)||[...buttons,...rest].some(b=>!permitted.has(b)))return reject('invalid-buttons');
        window.liveButtons=buttons;for(const b of buttons)gm.simulateInput(0,b,1);
        const end=now+frames,expiry=end+30;
        let resting=false;
        const tick=()=>{
            if(window.liveStopped||window.livePolicyGeneration!==policy_generation){window.releaseLive();return;}
            const frame=gm.getFrameNum();
            if(frame>=expiry){window.releaseLive();return;}
            if(frame>=end&&!resting){
                window.releaseLive();resting=true;window.liveButtons=rest;
                for(const b of rest)gm.simulateInput(0,b,1);
            }
            // A wall-clock watchdog only RELEASES controls if frame progress stalls.
            if(performance.now()-started>1500){window.releaseLive();return;}
            window.liveTimer=setTimeout(tick,8);
        };
        const started=performance.now();tick();
        return {applied:true,frame:now,end_frame:end,expiry_frame:expiry};
    };
};
