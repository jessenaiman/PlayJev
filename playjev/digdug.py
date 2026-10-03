"""Experimental Dig Dug native-pixel estimates; no RAM or inferred score truth."""
import io
import json
from pathlib import Path
from PIL import Image
from .invaders import components
from .challenge import JevPlayer, replay_html


def geometry(frame):
    im=Image.open(io.BytesIO(frame)).convert('RGB').resize((160,210),Image.Resampling.NEAREST)
    purple=[];pooka=[];fygar=[];brown=[]
    for y in range(3,188):
        for x in range(12,148):
            r,g,b=im.getpixel((x,y))
            if b>220 and r>160 and 110<g<180:purple.append((x,y))
            if r>220 and 120<g<170 and 60<b<120 and y<178:pooka.append((x,y))
            if g>r+30 and g>b+60 and y<178:fygar.append((x,y))
            if 180<r<215 and 90<g<120 and 40<b<80 and y>=179:brown.append((x,y))
    parts=components(purple)
    player=None
    if parts:
        box=[min(p['box'][0] for p in parts),min(p['box'][1] for p in parts),
             max(p['box'][2] for p in parts),max(p['box'][3] for p in parts)]
        if box[2]-box[0]<=14 and box[3]-box[1]<=18:
            player={'box':box,'pixels':sum(p['pixels'] for p in parts)}
    enemies=[]
    for kind,mask in (('pooka',pooka),('fygar',fygar)):
        for obj in components(mask):
            x,y,x2,y2=obj['box']
            if 3<=x2-x<=16 and 3<=y2-y<=20 and obj['pixels']>=12:
                enemies.append({**obj,'kind':kind})
    terrain=[]
    for y in range(24,176,8):
        row=''
        for x in range(16,144,8):
            soil=sum(1 for yy in range(y,y+8) for xx in range(x,x+8)
                     if (lambda c:140<c[0]<225 and 30<c[1]<180 and c[2]<100)(im.getpixel((xx,yy))))
            row+='.' if soil>=12 else 'T'
        terrain.append(row)
    lives=[p for p in components(brown) if p['pixels']==28 and p['box'][2]-p['box'][0]==3]
    active=bool(player and 22<=player['box'][1] and player['box'][3]<178 and lives)
    return {'coordinates':'160x210; x right, y down','player':player,'enemies':enemies,
            'terrain':{'grid':terrain,'origin':[16,24],'cell_size':[8,8],
                       'legend':'T = low-soil candidate tunnel; . = soil. Coarse pixel estimate, not navigability proof.'},
            'remaining_life_blocks':len(lives),'active_play_evidence':active,'facing':'unknown',
            'score':None,'wave':None,'rocks':None,
            'role_hint':'Purple miner, peach Pooka, green Fygar are ROM palette estimates. Ghosts, fire and rocks are not calibrated. Missing/ambiguous miner stays unknown; intro/title/respawn must not trigger fire.'}


def center(obj):
    return [(obj['box'][0]+obj['box'][2])/2,(obj['box'][1]+obj['box'][3])/2]


def track(previous,current,frames):
    if previous.get('player') and current.get('player'):
        a,b=center(previous['player']),center(current['player'])
        dx,dy=b[0]-a[0],b[1]-a[1]
        if abs(dx)>abs(dy) and abs(dx)>0.5:current['facing']='right' if dx>0 else 'left'
        elif abs(dy)>0.5:current['facing']='down' if dy>0 else 'up'
        else:current['facing']=previous.get('facing','unknown')
        current['player_motion']={'vx':dx/max(1,frames),'vy':dy/max(1,frames)}


def candidates(current):
    directions={'up':(0,-1),'down':(0,1),'left':(-1,0),'right':(1,0)}
    result={'noop':{'permitted':True,'reason':'Release inputs; no restart permission'}}
    if not current.get('active_play_evidence') or not current.get('player'):return result
    px,py=center(current['player'])
    terrain=current['terrain']
    for direction,(dx,dy) in directions.items():
        nx,ny=px+dx*6,py+dy*6
        if not (16<=nx<=142 and 24<=ny<=174):continue
        hazards=[e for e in current['enemies'] if abs(center(e)[0]-nx)+abs(center(e)[1]-ny)<12]
        col=max(0,min(15,int((nx-16)/8)));row=max(0,min(18,int((ny-24)/8)))
        result[direction]={'permitted':not hazards,'near_contact':bool(hazards),
                           'terrain':terrain['grid'][row][col], 'action':'Dig/move '+direction}
        aligned=[]
        for enemy in current['enemies']:
            ex,ey=center(enemy);along=(ex-px)*dx+(ey-py)*dy
            cross=abs(ey-py) if dx else abs(ex-px)
            if not (0<along<=24 and cross<=5):continue
            cells=[]
            for t in range(4,int(along),4):
                cx=max(0,min(15,int((px+dx*t-16)/8)));cy=max(0,min(18,int((py+dy*t-24)/8)))
                cells.append(terrain['grid'][cy][cx])
            if all(cell=='T' for cell in cells):aligned.append(enemy['kind'])
        if aligned:
            result[direction+'+fire']={'permitted':True,'aligned_enemy_candidates':aligned,
                                      'action':'Face '+direction+' and pump briefly in candidate tunnel'}
            if current.get('facing')==direction:result['fire']={'permitted':True,'aligned_enemy_candidates':aligned}
    return result


def prepare(current,decision):
    option=candidates(current).get(decision['choice'])
    veto=option is None or not option['permitted']
    return decision['choice'],min(14,max(1,decision.get('movement_frames',14))),veto


def overlay(current):
    return {'player':current['player'],'aliens':current['enemies'],'projectiles':[],
            'labels':{'alien':'monster estimate','player':'miner estimate'}}


class DigDugPlayer(JevPlayer):
    async def decide(self,state,game):
        current=state['current'];options=candidates(current)
        evidence={'game':game.id,'player':current['player'],'enemies':current['enemies'],
                  'active_play_evidence':current['active_play_evidence'],'facing':current['facing'],
                  'terrain':current['terrain'],'candidates':options,
                  'uncalibrated':['rocks','ghosts','fire','score','terminal state']}
        # Include only calculated bounded actions; noop is an explicit abstention.
        criteria={k:v for k,v in options.items() if v['permitted']}
        if len(criteria)==1:
            # No inference can confer restart permission when geometry is unknown.
            criteria['wait']='Release inputs; wait for reliable active-play evidence'
        body={'model':self.model,'state':evidence,'questions':{'move':{
            'type':'choice','instructions':'Choose the next short Dig Dug action from candidates. Avoid near_contact. Dig a route toward a monster, then face it and pump only with aligned_enemy_candidates in a candidate tunnel. Soil cannot be pumped through. Unknown rocks/ghosts are not proven safe. During intro/title/respawn or missing miner choose noop/wait; never restart a game. Practice context is a goal, not current geometry or reset authority.',
            'criteria':criteria}}}
        response=await self.request(body)
        answer=self.validate_choice(response['answers']['move'],criteria)
        selected=answer['choice'] if answer['choice']!='wait' else 'noop'
        return {'request':body,'response':response,'choice':selected,'confidence':answer['confidence'],
                'movement_frames':14,'rest_choice':'noop','components':{'move':answer},
                'composition':'experimental-digdug-native-candidates-v1'}


async def collect(directory):
    directory=Path(directory);summary=json.loads((directory/'summary.json').read_text())
    summary['score_candidate']=None
    summary['score_verified']=False;summary['score']=None
    summary['score_note']='Dig Dug bottom-right HUD glyph layout is not calibrated. Score remains unknown; no inference called.'
    (directory/'summary.json').write_text(json.dumps(summary,indent=2))
    records=[json.loads(line) for line in (directory/'decisions.jsonl').read_text().splitlines()]
    replay_html(directory,summary,records)
