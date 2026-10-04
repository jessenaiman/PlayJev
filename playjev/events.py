"""One local stream for judgments, native observations and code execution outcomes."""
import json
from datetime import datetime, timezone


class EventLog:
    def __init__(self,path,actor=None):
        self.path=path;self.actor=actor;self.sequence=0
        if path.is_file():
            with path.open() as file:
                for line in file:
                    row=json.loads(line);self.sequence=max(self.sequence,row['event_id']+1)

    def write(self,event,classification,**fields):
        row={'schema':'jev-game-event-v1','event_id':self.sequence,'event':event,
             'classification':classification,'classified_by':'code-event-taxonomy; no extra inference',
             'actor':self.actor,'at':datetime.now(timezone.utc).isoformat(),**fields}
        self.sequence+=1
        with self.path.open('a') as file:file.write(json.dumps(row)+'\n')


def action_class(game,choice):
    if 'fire' in choice:return 'pump' if game=='dig-dug' else 'drop' if game=='crackpots' else 'shoot'
    return 'abstain' if choice=='noop' else 'move'
