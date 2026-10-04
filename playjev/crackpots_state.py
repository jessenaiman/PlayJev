"""Model-facing observations; no question definitions, inference or controller inputs."""
from .crackpots import interception


def tactical_state(current,previous_target_x,*,include_pursuit_evidence=True,include_interception_evidence=False):
    px,lanes=interception(current)
    evidence={
        'player_x':px,
        'previous_target_x':previous_target_x,
        'drop_ready':any(lane['ready_to_drop'] for lane in lanes),
        'estimates':'Code supplies bounded, estimated interception candidates; not guaranteed catches.',
        'pots':{lane['id']:{key:lane[key] for key in
            ('x','catchable_bugs','arrival_frames','ready_to_drop')} for lane in lanes},
    }
    if include_pursuit_evidence:
        evidence['bugs']=[{key:bug[key] for key in ('x','y','vx','vy')}
                          for bug in current.get('bug_tracks',[])[:6]]
        for pot in evidence['pots'].values():
            pot['needed_direction']=('unknown' if px is None else
                'left' if pot['x']<px-3 else 'right' if pot['x']>px+3 else 'aligned')
    if include_interception_evidence:
        evidence['bugs']=[{key:bug[key] for key in ('id','x','y','vx','vy')}
                          for bug in current.get('bug_tracks',[])[:6]]
        for lane in lanes:
            matching=[hit for hit in lane['intercepts'] if hit['horizontal_miss']<=8 and hit['before_window']]
            evidence['pots'][lane['id']]['intercepts']=matching[:2]
        evidence['interception_scope']='Up to two predicted encounters per pot; motion_measured=false means fallback motion, not an observed trajectory.'
    return evidence
