"""Continuous-game hooks. New games register here, not in the rendering loop."""
from dataclasses import dataclass
from typing import Callable
from .challenge import GatedJevPlayer
from .hud import collect
from .invaders import geometry, motion


def invaders_track(previous,current,frames):
    current['projectile_motion']=motion(previous,current,frames)


def invaders_prepare(current,decision):
    choice=decision['choice'];player=current['player']
    px=(player['box'][0]+player['box'][2])/2 if player else None
    direction='left' if choice.startswith('left') else 'right' if choice.startswith('right') else 'stay'
    speed={'left':-0.5,'right':0.5,'stay':0}[direction]
    veto=px is None or (direction=='left' and px<=14) or (direction=='right' and px>=146)
    for laser in current.get('projectile_motion',[]):
        if laser['direction']=='up':continue
        vy=laser['vy'] if laser['direction']=='down' else 0.4
        impact=max(0,(183-laser['y'])/vy) if vy and vy>0 else float('inf')
        future=max(12,min(148,px+speed*min(impact,18))) if px is not None else None
        if impact<=42 and future is not None and abs(future-laser['x'])<=6:veto=True
    return choice,min(30,decision.get('movement_frames',30)),bool(veto)


@dataclass(frozen=True)
class LiveGame:
    id: str
    policy_version: str
    observe: Callable
    track: Callable
    overlay: Callable
    prepare: Callable
    terminal_candidate: Callable
    player_factory: Callable
    score_collector: Callable
    source: str
    terminal_note: str


def crackpots_track(previous,current,frames):
    from .crackpots import tracks
    current['bug_tracks']=tracks(previous,current,frames)


def crackpots_prepare(current,decision):
    from .crackpots import guard, interception
    choice=decision['choice'];duration=decision.get('movement_frames',30)
    if current['player'] and decision.get('target_x') is not None:
        px=(current['player']['box'][0]+current['player']['box'][2])/2
        error=decision['target_x']-px
        direction='left' if error<-3 else 'right' if error>3 else ''
        # An old fire judgment is not enough: the current frame must still
        # contain an aligned pot with a predicted interception opportunity.
        _,lanes=interception(current)
        fire=decision['components']['drop']['choice']=='fire' and any(l['ready_to_drop'] for l in lanes)
        choice='+'.join(([direction] if direction else [])+(['fire'] if fire else [])) or 'noop'
        duration=min(26,max(1,round(abs(error)/0.7))) if direction else 30
    return choice,duration,bool(guard(current,choice))


def registry():
    from .crackpots import geometry as crackpots_geometry, overlay, CrackpotsPlayer
    from .crackpots_score import collect as crackpots_collect
    return {
        'space-invaders':LiveGame('space-invaders','continuous-compact-v1',geometry,invaders_track,
            lambda current:current,invaders_prepare,lambda current:not current['background_black'],
            GatedJevPlayer,collect,'invaders.py','background-color candidate; not verified game over'),
        'crackpots':LiveGame('crackpots','crackpots-interception-v2',crackpots_geometry,crackpots_track,
            overlay,crackpots_prepare,lambda current:False,CrackpotsPlayer,crackpots_collect,
            'crackpots.py','not-yet-validated; use Stop & save'),
    }
