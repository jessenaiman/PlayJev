"""Deterministic target-to-input conversion and fresh-frame execution guard."""
from .crackpots import guard, interception


def command(player_x,target_x,drop_authorized):
    error=target_x-player_x if target_x is not None and player_x is not None else 0
    direction='left' if error<-3 else 'right' if error>3 else ''
    fire=bool(drop_authorized and player_x is not None)
    controls=([direction] if direction else [])+(['fire'] if fire else [])
    return {
        'choice':'+'.join(controls) or 'noop',
        'movement_frames':min(26,max(1,round(abs(error)/0.7))) if direction else 30,
        'drop_authorized':fire,
        'rest_choice':'noop',
        'target_x':target_x,
    }


def prepare(current,decision):
    choice=decision['choice'];duration=decision.get('movement_frames',30)
    if current['player'] and decision.get('target_x') is not None:
        px=(current['player']['box'][0]+current['player']['box'][2])/2
        _,lanes=interception(current)
        # A previous model reply never authorizes a stale drop.
        trigger=decision.get('drop_authorized',decision.get('components',{}).get('drop',{}).get('choice')=='fire')
        fresh=command(px,decision['target_x'],trigger and any(lane['ready_to_drop'] for lane in lanes))
        choice,duration=fresh['choice'],fresh['movement_frames']
    return choice,duration,bool(guard(current,choice))
