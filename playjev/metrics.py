"""Measured process counters and a compact inferred-object ASCII display."""
import json
from datetime import datetime, timezone


def write_phase(directory,phase,**details):
    path=directory/'process.json';temp=directory/'process.tmp'
    temp.write_text(json.dumps({'phase':phase,'updated_at':datetime.now(timezone.utc).isoformat(),**details},indent=2))
    temp.replace(path)


class Metrics:
    def __init__(self,game):
        self.game=game;self.requests=0;self.applied=0;self.vetoes=0;self.stale=0
        self.input_tokens=0;self.output_tokens=0;self.latest=None;self.latency_ms=0
        self.completed=0;self.failed=0;self.cancelled=0

    def start_request(self):
        self.requests+=1

    def counters(self):
        return {k:getattr(self,k) for k in ('requests','completed','failed','cancelled','applied','vetoes','stale','input_tokens','output_tokens')}

    def record(self,record):
        self.completed+=1;self.applied+=int(record['applied']);self.vetoes+=int(record['collision_veto'])
        self.stale+=int(record['age_frames']>60 or record.get('execution',{}).get('reason')=='stale');self.latest=record
        self.latency_ms=round(record.get('latency_s',0)*1000)
        usage=record['decision'].get('response',{}).get('usage',{})
        self.input_tokens+=usage.get('input_tokens',0);self.output_tokens+=usage.get('output_tokens',0)

    def snapshot(self,current,frame,pending,clock):
        width,height=32,12;grid=[[' ']*width for _ in range(height)]
        def mark(box,char):
            x=(box[0]+box[2])/2;y=(box[1]+box[3])/2
            grid[min(height-1,max(0,int(y/210*height)))][min(width-1,max(0,int(x/160*width)))]=char
        for obj in current.get('aliens',current.get('bugs',current.get('enemies',[]))):mark(obj['box'],'b' if self.game=='crackpots' else 'a')
        for obj in current.get('pots',[]):mark(obj['box'],'v')
        for obj in current.get('projectiles',[]):mark(obj['box'],'|')
        if current.get('player'):mark(current['player']['box'],'P')
        latest=self.latest or {};decision=latest.get('decision',{})
        lines=[f'[{self.game.upper()}]  {frame/60:7.2f}s',
               f'cycle: {clock.interval:7} pending: {str(pending):5}',
                f'calls {self.requests:4}  applied {self.applied:4}',
                f'done {self.completed:4} fail {self.failed:3} cancel {self.cancelled:3}',
               f'veto {self.vetoes:4}  stale {self.stale:4}',
               f'latency {self.latency_ms:4}ms age {latest.get("age_frames",0):3}f',
               f'tokens in {self.input_tokens} out {self.output_tokens}',
                f'action: {latest.get("executed_choice","waiting") if latest.get("applied") else "released / waiting"}',
               '+'+'-'*width+'+']+['|'+''.join(row)+'|' for row in grid]+['+'+'-'*width+'+','P player  a/b inferred target','v available pot  | projectile','']
        for name,answer in decision.get('components',{}).items():
            lines.append(f'{name:8} {answer["choice"]:12} c={answer["confidence"]:.2f}')
            top=sorted(answer.get('probabilities',{}).items(),key=lambda item:-item[1])[:2]
            lines.append('  '+' '.join(f'{key}:{value:.2f}' for key,value in top))
        for name,answer in latest.get('accuracy_checks',{}).items():
            value=answer.get('noul')
            lines.append(f'{name}: {value:.2f}' if isinstance(value,(int,float)) else f'{name}: unknown')
        return {**self.counters(),'game':self.game,'game_frame':frame,'pending':pending,'requests':self.requests,'applied':self.applied,
                'vetoes':self.vetoes,'stale':self.stale,'input_tokens':self.input_tokens,'output_tokens':self.output_tokens,
                'latency_ms':self.latency_ms,'clock':clock.state(frame),'ascii':'\n'.join(lines),
                'updated_at':datetime.now(timezone.utc).isoformat(),'note':'Counters measured; ASCII objects inferred; confidence not proof.'}

    def write(self,directory,snapshot):
        path=directory/'metrics.json';temp=directory/'metrics.tmp'
        temp.write_text(json.dumps(snapshot,indent=2));temp.replace(path)
