"""Measured process counters and a compact inferred-object ASCII display."""
import json
import time
from datetime import datetime, timezone


def write_phase(directory,phase,**details):
    path=directory/'process.json';temp=directory/'process.tmp'
    temp.write_text(json.dumps({'phase':phase,'updated_at':datetime.now(timezone.utc).isoformat(),**details},indent=2))
    temp.replace(path)


class Metrics:
    def __init__(self,game):
        self.game=game;self.requests=0;self.applied=0;self.vetoes=0;self.stale=0
        self.input_tokens=0;self.output_tokens=0;self.latest=None;self.latency_ms=None
        self.completed=0;self.failed=0;self.cancelled=0
        self.pending_request=None;self.last_result=None

    def start_request(self,envelope=None,now=None):
        self.requests+=1
        self.pending_request={'started':time.monotonic() if now is None else now,'envelope':envelope or {}}

    def finish_request(self,outcome,reason=None):
        if outcome not in ('failed','cancelled'):raise ValueError('Invalid request outcome')
        setattr(self,outcome,getattr(self,outcome)+1)
        self.pending_request=None
        self.last_result={'outcome':outcome,'reason':reason or outcome}

    def counters(self):
        return {k:getattr(self,k) for k in ('requests','completed','failed','cancelled','applied','vetoes','stale','input_tokens','output_tokens')}

    def record(self,record):
        self.completed+=1;self.applied+=int(record['applied']);self.vetoes+=int(record['collision_veto'])
        self.stale+=int(record['age_frames']>60 or record.get('execution',{}).get('reason')=='stale');self.latest=record
        self.pending_request=None
        self.last_result={'outcome':'accepted' if record['applied'] else 'rejected',
                          'reason':record.get('execution',{}).get('reason') or ('accepted' if record['applied'] else 'safety-veto' if record['collision_veto'] else 'rejected')}
        self.latency_ms=round(record.get('latency_s',0)*1000)
        usage=record['decision'].get('response',{}).get('usage',{})
        self.input_tokens+=usage.get('input_tokens',0);self.output_tokens+=usage.get('output_tokens',0)

    def snapshot(self,current,frame,pending,clock,*,emulator_frame=None,buttons=None,now=None,phase='playing'):
        request=self.pending_request if pending else None
        wait_ms=max(0,round(((time.monotonic() if now is None else now)-request['started'])*1000)) if request else None
        source=request['envelope'].get('source',{}).get('before') if request else None
        pending_age=max(0,emulator_frame-source) if source is not None and emulator_frame is not None else None
        latest=self.latest or {};decision=latest.get('decision',{})
        held=('unknown (not sampled)' if buttons is None else
              'released' if not buttons else ','.join({0:'fire',4:'up',5:'down',6:'left',7:'right'}.get(b,str(b)) for b in buttons))
        result=self.last_result or {'outcome':'none','reason':'no result yet'}
        analytics=[f'[{self.game.upper()}] {phase}',f'frame {frame} | {frame/60:.2f}s',
                   f'score {current.get("score") if current.get("score") is not None else "unknown"} | best supported {current.get("best_supported_score") if current.get("best_supported_score") is not None else "unknown"}',
                   'stage clear: unknown | terminal: unknown',
                   f'requests {self.requests} | replies {self.completed}',
                   f'applied {self.applied} | rejected {self.completed-self.applied}',
                   f'stale {self.stale} | veto {self.vetoes}',
                   f'failed {self.failed} | cancelled {self.cancelled}',
                   ('pending: '+(f'{wait_ms}ms / {pending_age}f old' if pending_age is not None else f'{wait_ms}ms' if wait_ms is not None else 'wait unknown')) if pending else 'pending: no',
                   'last reply: '+(f'{self.latency_ms}ms / {latest["age_frames"]}f old' if self.latency_ms is not None else 'none yet'),
                   f'last result: {result["reason"]}',f'held inputs: {held}',
                   f'tokens in {self.input_tokens} / out {self.output_tokens}']
        width,height=30,10;grid=[[' ']*width for _ in range(height)]
        def mark(box,char):
            x=(box[0]+box[2])/2;y=(box[1]+box[3])/2
            grid[min(height-1,max(0,int(y/210*height)))][min(width-1,max(0,int(x/160*width)))]=char
        for obj in current.get('aliens',current.get('bugs',current.get('enemies',[]))):mark(obj['box'],'E')
        for obj in current.get('pots',[]):mark(obj['box'],'v')
        for obj in current.get('projectiles',[]):mark(obj['box'],'|')
        if current.get('player'):mark(current['player']['box'],'P')
        lines=analytics+[f'cycle: {clock.interval}',
               f'last issued: {latest.get("executed_choice","none")}' if latest.get('applied') else 'last issued: released / waiting',
               'MAP = inferred pixel objects',
               '+'+'-'*width+'+']+['|'+''.join(row)+'|' for row in grid]+['+'+'-'*width+'+','P player estimate / E target']
        if 'pots' in current:lines.append('v available pot estimate')
        if 'projectiles' in current:lines.append('| projectile estimate')
        if decision.get('selected_target') is not None:
            lines.append(f'Target: {decision["selected_target"]} ({decision["selection_source"]})')
        lines.append('Model judgments, not proof:')
        from .judgment_display import answer_lines
        for name,answer in decision.get('components',{}).items():
            lines.extend(answer_lines(name,answer))
        for name,answer in latest.get('accuracy_checks',{}).items():
            value=answer.get('noul')
            lines.append(f'{name} p(yes): {value:.2f}' if isinstance(value,(int,float)) else f'{name}: unknown')
        return {**self.counters(),'game':self.game,'game_frame':frame,'pending':pending,'requests':self.requests,'applied':self.applied,
                 'score':current.get('score'),'best_supported_score':current.get('best_supported_score'),
                 'score_status':current.get('score_status','unknown'),'score_evidence':current.get('score_evidence',[]),
                 'stage_clear':None,'terminal':None,
                 'rejected':self.completed-self.applied,'phase':phase,'pending_wait_ms':wait_ms,'pending_age_frames':pending_age,
                  'held_buttons':buttons,'last_result':self.last_result,'analytics':'\n'.join(analytics),
                  'last_proposed_choice':latest.get('decision',{}).get('choice'),
                'vetoes':self.vetoes,'stale':self.stale,'input_tokens':self.input_tokens,'output_tokens':self.output_tokens,
                'latency_ms':self.latency_ms,'clock':clock.state(frame),'ascii':'\n'.join(lines),
                'updated_at':datetime.now(timezone.utc).isoformat(),'note':'Counters measured; ASCII objects inferred; confidence not proof.'}

    def write(self,directory,snapshot):
        path=directory/'metrics.json';temp=directory/'metrics.tmp'
        temp.write_text(json.dumps(snapshot,indent=2));temp.replace(path)
