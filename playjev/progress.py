"""Evidence-bound endpoints and practice goals; no reset/resume/launch authority."""
import json
from datetime import datetime, timezone
from pathlib import Path
from .scoreboard import score_supported


def endpoint(game,current,stamp,origin,evidence_sha256):
    interval=None
    if stamp is not None:
        if stamp.sha256!=evidence_sha256:
            raise ValueError('Endpoint frame/hash mismatch')
        interval={'before':stamp.before,'after':stamp.after,
                  'game_before':stamp.before-origin,'game_after':stamp.after-origin}
    player=current.get('player')
    return {'game':game,'evidence':'final.png','evidence_sha256':evidence_sha256,
            'capture_interval':interval,'player_box':player.get('box') if player else None,
            'observed_targets':len(current.get('aliens',current.get('bugs',[]))),
            'pot_row':current.get('pot_row'),'coordinates':current.get('coordinates'),
            'wave':None,'terminal_verified':False,
            'note':'Last captured native-screen position, not an exact death location or verified world/wave progress. Setup-only captures have no gameplay interval.'}


def save(directory):
    """Finalize the ledger after the shared scorer has reviewed the run."""
    directory=Path(directory)
    summary=json.loads((directory/'summary.json').read_text())
    observed=summary.get('endpoint')
    if not observed:return None
    row={'schema':'atari-progress-v1','game':summary['game'],'challenge_id':summary['challenge_id'],
         'run':directory.name,'status':summary['status'],'stop_reason':summary.get('stop_reason','unknown'),
         'game_frames':summary['game_frames'],'endpoint':observed,
         'highest_supported_score':summary.get('score') if score_supported(directory,summary) else None,
         'recorded_at':datetime.now(timezone.utc).isoformat()}
    temp=directory/'progress.tmp';temp.write_text(json.dumps(row,indent=2));temp.replace(directory/'progress.json')
    return row


def load(runs):
    """Group by immutable challenge; changed evidence cannot seed practice goals."""
    groups={}
    for directory in runs:
        directory=Path(directory)
        try:
            summary=json.loads((directory/'summary.json').read_text())
            key=(summary['game'],summary['challenge_id'])
            entry=groups.setdefault(key,{'game':key[0],'challenge_id':key[1],'best_supported_score':None,'latest':None})
            if score_supported(directory,summary):
                score=summary['score'];best=entry['best_supported_score']
                entry['best_supported_score']=score if best is None else max(best,score)
            file=directory/'progress.json'
            if not file.is_file():continue
            row=json.loads(file.read_text())
            # Progress is derived evidence too, not a trusted second score channel.
            evidence=directory/row['endpoint']['evidence']
            from .challenge import digest
            if evidence.name!='final.png' or not evidence.resolve().is_relative_to(directory.resolve()) or digest(evidence.read_bytes())!=row['endpoint']['evidence_sha256']:continue
            if entry['latest'] is None or row['recorded_at']>entry['latest']['recorded_at']:
                entry['latest']=row
        except (OSError,ValueError,KeyError,TypeError):continue
    return list(groups.values())


def next_target(progress,increment,metric='score'):
    if isinstance(increment,bool) or not isinstance(increment,int) or not 1<=increment<=100000:
        raise ValueError('Practice increment must be an integer from 1 to 100000')
    if metric!='score':raise ValueError('Only supported HUD score targets are calibrated; waves/distance are still unknown')
    base=progress['best_supported_score']
    return {'game':progress['game'],'challenge_id':progress['challenge_id'],'metric':metric,
            'previous_best':base,'increment':increment,'target':None if base is None else base+increment,
            'kind':'practice-goal-preview','launches_attempt':False,'changes_budget':False,
            'note':'Unknown baseline stays unknown. Repeated failed attempts retain the same best+X goal. This preview does not resume a checkpoint or declare a completed game.'}
