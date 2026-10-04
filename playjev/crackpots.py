"""Read-only Crackpots raster geometry and short-horizon interception."""
import io
import json
from pathlib import Path
from PIL import Image
from .invaders import components
from .challenge import JevPlayer


def geometry(frame):
    im=Image.open(io.BytesIO(frame)).convert('RGB').resize((160,210),Image.Resampling.NEAREST)
    yellow=[];green=[];bugs={k:[] for k in ('black','blue','red','green')}
    for y in range(20,156):
        for x in range(9,159):
            r,g,b=im.getpixel((x,y))
            if r>200 and 150<g<200 and 60<b<110:yellow.append((x,y))
            if g>r+40 and g>b+40:green.append((x,y))
    people=components(yellow)
    head=max(people,key=lambda p:p['pixels'],default=None)
    player=None
    if head:
        parts=[p for p in people if abs(p['box'][0]-head['box'][0])<8 and abs(p['box'][1]-head['box'][1])<22]
        player={'box':[min(p['box'][0] for p in parts),min(p['box'][1] for p in parts),max(p['box'][2] for p in parts),max(p['box'][3] for p in parts)],'pixels':sum(p['pixels'] for p in parts)}
    plants=components(green)
    expected_row=player['box'][3]+6 if player else 46
    plant_row=min((p['box'][1] for p in plants if p['pixels']>=5 and abs(p['box'][1]-expected_row)<=6),default=expected_row)
    pots=[p for p in plants if abs(p['box'][1]-plant_row)<=2]
    for y in range(plant_row+12,156):
        for x in range(9,159):
            r,g,b=im.getpixel((x,y))
            color='black' if max(r,g,b)<15 else 'blue' if b>r+65 and b>g+65 else 'red' if r>g+65 and r>b+65 else 'green' if g>r+45 and g>b+45 else None
            if color:bugs[color].append((x,y))
    objects=[]
    for color,mask in bugs.items():
        for obj in components(mask):
            x,y,x2,y2=obj['box']
            # Windows/brick marks are tall rectangles or small solid blocks.
            if 4<=x2-x+1<=12 and 3<=y2-y+1<=9 and 8<=obj['pixels']<=65:
                if obj['pixels']==(x2-x+1)*(y2-y+1):continue
                objects.append({**obj,'color':color})
    # Native initial roof = 46; each lost building layer lowers it by eight.
    # Six losses reach 94. A candidate stops play; it is not model-certified death.
    active=bool(player and pots and 46<=plant_row<94)
    return {'coordinates':'160x210; x right, y down','player':player,'pots':pots,'bugs':objects,
            'active_play_evidence':active,'final_building_loss_candidate':bool(player and pots and plant_row>=94),
            'pot_row':plant_row,'window_y':plant_row+30,'background_black':False,
            'role_hint':'ROM-specific visual estimates. Gardener is gold; six roof pots have green foliage. Bugs climb; windows and bricks are not bugs. Missing gardener may be flicker. Building layers can collapse, moving the roof downward.'}


def tracks(previous,current,frames):
    remaining=list(previous.get('bugs',[]));result=[]
    for bug in current['bugs']:
        x=(bug['box'][0]+bug['box'][2])/2;y=(bug['box'][1]+bug['box'][3])/2
        candidates=[o for o in remaining if o['color']==bug['color'] and abs((o['box'][0]+o['box'][2])/2-x)<=max(8,frames) and abs((o['box'][1]+o['box'][3])/2-y)<=max(8,frames)]
        old=min(candidates,key=lambda o:abs((o['box'][0]+o['box'][2])/2-x)+abs((o['box'][1]+o['box'][3])/2-y),default=None)
        if old:remaining.remove(old)
        vx=(x-(old['box'][0]+old['box'][2])/2)/frames if old else None
        vy=(y-(old['box'][1]+old['box'][3])/2)/frames if old else None
        result.append({'id':f'bug_{len(result)}','x':x,'y':y,'vx':vx,'vy':vy,'color':bug['color'],'box':bug['box']})
    return result


def interception(current):
    player=current['player'];px=(player['box'][0]+player['box'][2])/2 if player else None
    lanes=[]
    for pot in current['pots']:
        x=(pot['box'][0]+pot['box'][2])/2
        arrival=abs(x-px)/0.7 if px is not None else None
        hits=[]
        for bug in current.get('bug_tracks',[]):
            vy=bug['vy'] if bug['vy'] is not None and bug['vy']<0 else -0.15
            wait=arrival or 0
            flight=max(0,(bug['y']+vy*wait-current['pot_row'])/(1.6-vy))
            vx=bug['vx'] or 0
            future=bug['x']+vx*(wait+flight)
            hits.append({'bug':bug['id'],'predicted_x':round(future,1),'horizontal_miss':round(abs(future-x),1),
                         'flight_frames':round(flight,1),'before_window':bug['y']+vy*(wait+flight)>current['window_y'],
                         'motion_measured':bug['vy'] is not None})
        opportunities=[h for h in hits if h['horizontal_miss']<=8 and h['before_window']]
        lanes.append({'id':f'pot_{len(lanes)}','x':x,'alignment_error':round(abs(x-px),1) if px is not None else None,
                      'arrival_frames':round(arrival,1) if arrival is not None else None,'intercepts':hits,
                      'catchable_bugs':len(opportunities),'ready_to_drop':px is not None and abs(x-px)<=4 and bool(opportunities)})
    return px,lanes


def guard(current,choice):
    player=current['player']
    if not player:return True
    x=(player['box'][0]+player['box'][2])/2
    return choice.startswith('left') and x<=16 or choice.startswith('right') and x>=150


def overlay(current):
    return {'player':current['player'],'aliens':current['bugs'],'projectiles':[],
            'labels':{'alien':'bug','player':'gardener'},'targets':current['pots'],'bug_tracks':current.get('bug_tracks',[])}


class CrackpotsPlayer(JevPlayer):
    auxiliary_questions=False

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.last_target=None
        self.policy=json.loads((Path(__file__).parent/'policies'/'crackpots.json').read_text())

    async def decide(self,state,game):
        current=state['current'];px,lanes=interception(current)
        evidence={'player_x':px,'previous_target_x':self.last_target,
                  'drop_ready':any(l['ready_to_drop'] for l in lanes),
                  'estimates':'Code supplies bounded, estimated interception candidates; not guaranteed catches.'}
        criteria={lane['id']:{'action':'Align with this observed available pot','x':lane['x'],
                             'catchable_bugs':lane['catchable_bugs'],'arrival_frames':lane['arrival_frames'],
                             'ready_to_drop':lane['ready_to_drop']} for lane in lanes}
        criteria.update(hold='Wait for reliable gardener/bug observations',scan='Move toward the central pots to prepare for a new bug')
        if self.policy['include_pursuit_evidence']:
            evidence['bugs']=[{'x':b['x'],'y':b['y'],'vx':b['vx'],'vy':b['vy']} for b in current.get('bug_tracks',[])[:6]]
            for lane in lanes:
                criteria[lane['id']]['needed_direction']='unknown' if px is None else 'left' if lane['x']<px-3 else 'right' if lane['x']>px+3 else 'aligned'
        body={'model':self.model,'state':evidence,'questions':{
            'lane':{'type':'choice','instructions':self.policy['lane_instructions'], 'criteria':criteria}}}
        response=await self.request(body)
        gates={'lane':self.validate_choice(response['answers']['lane'],criteria)}
        lane=next((l for l in lanes if l['id']==gates['lane']['choice']),None)
        target=lane['x'] if lane else 80 if gates['lane']['choice']=='scan' else px
        self.last_target=target
        error=target-px if target is not None and px is not None else 0
        direction='left' if error<-3 else 'right' if error>3 else ''
        fire=bool(evidence['drop_ready'] and px is not None)
        choice='+'.join(([direction] if direction else [])+(['fire'] if fire else [])) or 'noop'
        duration=min(26,max(1,round(abs(error)/0.7))) if direction else 30
        return {'request':body,'response':response,'components':gates,'choice':choice,
                'confidence':gates['lane']['confidence'],'movement_frames':duration,'drop_authorized':fire,
                'rest_choice':'noop','target_x':target,'composition':'crackpots-model-lane/code-fresh-interception-trigger-v3'}
