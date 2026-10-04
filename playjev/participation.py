"""Native input-effect evidence, distinct from sprites, HUDs and issued inputs."""
import json
from pathlib import Path
from .challenge import digest
from .native import capture


async def probe_control(env,snapshot,expected,directory,game,*,resumed=False):
    """Setup-only counterfactual branches; restore the challenge before actual play."""
    from .runtime import registry
    profile=registry()[game]
    from .hud import read_score
    rows=[];callbacks=0
    for choice,buttons in (('noop',[]),('right',[7]),('left',[6])):
        _,setup=await env.restore_matching(snapshot,expected);callbacks+=setup
        await env.page.evaluate('()=>{for(const b of [0,4,5,6,7])EJS_emulator.gameManager.simulateInput(0,b,0);}')
        await env.frames(buttons,12,slow=False);callbacks+=12
        frame,stamp=await capture(env,paused=True);callbacks+=1
        name='control-'+choice+'.png';(directory/name).write_bytes(frame)
        current=profile.observe(frame)
        rows.append({'choice':choice,'evidence':name,'sha256':digest(frame),
                     'before':stamp.before,'after':stamp.after,
                     'player_box':current['player']['box'] if current['player'] else None,
                     'score':read_score(game,frame),'pot_row':current.get('pot_row')})
    _,setup=await env.restore_matching(snapshot,expected);callbacks+=setup
    proof={'schema':'native-control-probe-v1','game':game,'resumed':resumed,
           'observations':rows,'setup_callbacks':callbacks,
           'note':'Setup branches are not LLM moves or score gains. Original state restored; no in-game restart.'}
    proof['verified']=probe_valid(directory,proof)
    (directory/'control-probe.json').write_text(json.dumps(proof,indent=2))
    return proof


def probe_valid(directory,proof):
    """Recheck native evidence, not a trusted model/summary boolean."""
    from .runtime import registry
    from .hud import read_score
    try:
        if proof.get('schema')!='native-control-probe-v1' or proof.get('game') not in registry():return False
        game=proof['game'];profile=registry()[game]
        samples={}
        for row in proof['observations']:
            file=(Path(directory)/row['evidence']).resolve()
            if not file.is_relative_to(Path(directory).resolve()):return False
            frame=file.read_bytes()
            if digest(frame)!=row['sha256']:return False
            current=profile.observe(frame)
            if not profile.inference_ready(current) or profile.terminal_candidate(current) or not current['player']:return False
            if not proof.get('resumed') and read_score(game,frame)!=0:return False
            if game=='crackpots' and not proof.get('resumed') and current['pot_row']!=46:return False
            samples[row['choice']]=(current['player']['box'][0]+current['player']['box'][2])/2
        return set(samples)=={'noop','left','right'} and (
            samples['right']-samples['noop']>=5 or samples['noop']-samples['left']>=5)
    except (OSError,ValueError,KeyError,TypeError):return False


def score_attributable(directory,summary):
    if summary.get('attribution_hold'):return False
    if summary.get('participation_required') and not summary.get('startup_check',{}).get('passed'):return False
    if summary.get('game')!='crackpots' and not summary.get('participation_required'):return True  # Legacy contracts disclosed separately.
    return probe_valid(directory,summary.get('participation',{}))
