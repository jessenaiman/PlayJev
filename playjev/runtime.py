"""Continuous-game hooks. New games register here, not in the rendering loop."""
from dataclasses import dataclass
from typing import Callable
from .challenge import GatedJevPlayer
from .hud import collect
from .invaders import geometry, motion
from .crackpots_control import prepare as crackpots_prepare


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
    terminal_reason: str = 'three-background-color-observations'
    inference_ready: Callable = lambda current:True


def crackpots_track(previous,current,frames):
    from .crackpots import tracks
    current['bug_tracks']=tracks(previous,current,frames)


def registry():
    from .crackpots import geometry as crackpots_geometry, overlay
    from .crackpots_player import CrackpotsPlayer
    from .crackpots_score import collect as crackpots_collect
    from . import digdug
    return {
        'space-invaders':LiveGame('space-invaders','continuous-compact-v1',geometry,invaders_track,
            lambda current:current,invaders_prepare,lambda current:not current['background_black'],
            GatedJevPlayer,collect,'invaders.py','background-color candidate; not verified game over'),
        'crackpots':LiveGame('crackpots','crackpots-state-lane-code-trigger-v5',crackpots_geometry,crackpots_track,
            overlay,crackpots_prepare,lambda current:current.get('final_building_loss_candidate',False),CrackpotsPlayer,crackpots_collect,
            'crackpots.py','six-layer native roof-loss candidate; not verified game over',
            'three-native-captures-at-final-building-loss',
            inference_ready=lambda current:current.get('active_play_evidence',False)),
        'dig-dug':LiveGame('dig-dug','digdug-single-action-v2',digdug.geometry,digdug.track,
            digdug.overlay,digdug.prepare,lambda current:not current.get('playfield_visible',False),digdug.DigDugPlayer,digdug.collect,
            'digdug.py','partial HUD font; missing playfield stops without restart; stage/game-over proof pending',
            'three-native-captures-without-known-playfield',lambda current:current.get('active_play_evidence',False)),
    }
