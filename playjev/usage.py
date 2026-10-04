"""Evidence-derived attempt tokens. Missing usage is never a free zero-token run."""
import json
from pathlib import Path


def player_identity(config):
    model=config.get('model')
    if config.get('player')=='human':return {'kind':'human','name':config.get('arcade_name','YOU'),'model':None,'provider':'human'}
    if model:
        provider=config.get('provider') or ('jev' if model.startswith('jev-') else 'unknown')
        return {'kind':'llm','name':model.upper().replace(':','-'),'model':model,'provider':provider}
    return {'kind':'code','name':config.get('player','UNKNOWN').upper(),'model':None,'provider':'code'}


def token_usage(directory,summary):
    """Count replies once, separated into startup, gameplay, completion and review."""
    directory=Path(directory);counts={'input_tokens':0,'output_tokens':0};known=0;complete=True;notes=[];phases={}
    def count(response):
        nonlocal known,complete
        usage=response.get('usage') if isinstance(response,dict) else None
        if not isinstance(usage,dict) or any(type(usage.get(k)) is not int or usage[k]<0 for k in counts):
            complete=False;return
        for key in counts:counts[key]+=usage[key]
        known+=1
    def rows(path):
        nonlocal complete
        with path.open() as file:
            for line in file:
                try:
                    row=json.loads(line)
                    if not isinstance(row,dict):raise ValueError('Invalid usage row')
                    yield row
                except (ValueError,TypeError):complete=False
    inference=directory/'inference.jsonl'
    def logged_requests(path):
        nonlocal complete
        started=set();finished=set()
        for row in rows(path):
            key=row.get('sequence')
            if row.get('event')=='started':started.add(key)
            elif row.get('event')=='completed':
                if key in finished:complete=False;continue
                finished.add(key);count(row.get('response'))
            elif row.get('event') in ('failed','cancelled'):complete=False
        if started!=finished:complete=False
    def phase(label,operation):
        nonlocal complete
        before=dict(counts);old_known=known;prior=complete;complete=True
        operation()
        phases[label]={**{k:counts[k]-before[k] if known>old_known else None for k in counts},
                       'total_tokens':sum(counts[k]-before[k] for k in counts) if known>old_known else None,
                       'known_requests':known-old_known,'complete':complete}
        complete=prior and complete
    try:
        if inference.is_file():
            phase('gameplay',lambda:logged_requests(inference))
            if inference.stat().st_size==0:phases['gameplay'].update(input_tokens=0,output_tokens=0,total_tokens=0)
            coverage='logical-request log'
        else:
            records=directory/'decisions.jsonl'
            if records.is_file():
                for row in rows(records):
                    decision=row.get('decision')
                    count(decision.get('response') if isinstance(decision,dict) else None)
            # Legacy logs cannot prove that failed/cancelled requests were captured.
            complete=False;coverage='legacy recorded replies only'
        for label in ('startup','completion','review'):
            path=directory/(label+'-inference.jsonl')
            if path.is_file():phase(label,lambda:logged_requests(path))
        report=directory/'hud-jev.json'
        if report.is_file():
            hud=json.loads(report.read_text())
            if not isinstance(hud,dict):raise ValueError('Invalid HUD usage evidence')
            if hud.get('unique_requests',0):count(hud.get('response'))
        elif summary.get('score_review',{}).get('provider') in ('jev','ollaya'):
            complete=False;notes.append('HUD inference usage unavailable')
    except (OSError,ValueError,KeyError,TypeError):complete=False;notes.append('Usage evidence unreadable')
    if not complete:notes.append('Unreported/unfinished requests may have consumed additional tokens')
    return {**{k:counts[k] if known else None for k in counts},
            'total_tokens':sum(counts.values()) if known else None,'known_requests':known,
            'complete':complete,'coverage':coverage if 'coverage' in locals() else 'unavailable','by_phase':phases,
            'scope':'This attempt startup + gameplay + HUD + completion + improvement review; excludes development, discovery and game-selection calls',
            'notes':notes,'money':None,'money_note':'Tokens are not dollars; local inference still uses machine resources.'}
