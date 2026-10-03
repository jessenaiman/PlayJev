"""Constrained OCR + Jev consensus for Crackpots; candidates until calibrated."""
import asyncio
import io
import json
import subprocess
from pathlib import Path
from PIL import Image, ImageOps
from .challenge import JevPlayer, digest, replay_html

# Activision's six-column, eight-row glyphs, calibrated against the raw v3
# recording. OCR disagreed even on 0/50/70/80/290/690, so it is not authoritative.
FONT={
    '0':['.####.']+['##..##']*6+['.####.'],
    '1':['..##..','.###..','..##..','..##..','..##..','..##..','..##..','.####.'],
    '2':['.####.','#...##','....##','....##','.####.','##....','##....','######'],
    '3':['.####.','#...##','....##','...##.','...##.','....##','#...##','.####.'],
    '4':['...##.','..###.','.#.##.','#..##.','######','...##.','...##.','...##.'],
    '5':['######','##....','##....','#####.','....##','....##','#...##','#####.'],
    '6':['.####.','##...#','##....','#####.','##..##','##..##','##..##','.####.'],
    '7':['######','#....#','....##','...##.','..##..','..##..','..##..','..##..'],
    '8':['.####.','##..##','##..##','.####.','.####.','##..##','##..##','.####.'],
    '9':['.####.','##..##','##..##','##..##','.#####','....##','#...##','.####.'],
}


def digit_grids(frame):
    im=Image.open(io.BytesIO(frame)).convert('RGB').resize((160,210),Image.Resampling.NEAREST)
    return [[''.join('#' if min(im.getpixel((x,y)))>180 else '.' for x in range(left,left+6))
             for y in range(11,19)] for left in (59,67,75,83,91,99)]


async def collect(directory):
    from .hud import collect as collect_glyphs
    path=Path(directory)/'hud-jev.json'
    if path.exists() and json.loads(path.read_text()).get('schema')=='crackpots-jev-ocr-v1':
        (Path(directory)/'hud-ocr.json').write_bytes(path.read_bytes())
    await collect_glyphs(directory)


def crop(frame):
    im=Image.open(io.BytesIO(frame)).convert('RGB').resize((160,210),Image.Resampling.NEAREST)
    region=im.crop((16,8,112,20)).convert('L').point(lambda v:255 if v>180 else 0)
    return region


def readings(region):
    im=ImageOps.expand(ImageOps.invert(region).resize((1152,144),Image.Resampling.NEAREST),border=24,fill=255)
    buf=io.BytesIO();im.save(buf,'PNG');results=[]
    for psm in (7,8,13):
        proc=subprocess.run(['tesseract','stdin','stdout','--psm',str(psm),'-c','tessedit_char_whitelist=0123456789'],input=buf.getvalue(),capture_output=True,timeout=15)
        text=proc.stdout.decode().strip()
        results.append({'psm':psm,'text':text,'value':int(text) if proc.returncode==0 and text.isdigit() else None})
    points=[(x,y) for y in range(region.height) for x in range(region.width) if region.getpixel((x,y))]
    if points:
        xs,ys=zip(*points);box=region.crop((min(xs),min(ys),max(xs)+1,max(ys)+1))
        grid=[''.join('#' if box.getpixel((x,y)) else '.' for x in range(box.width)) for y in range(box.height)]
        if grid==['.####.']+['##..##']*6+['.####.']:
            results.append({'method':'literal-zero-template','text':'0','value':0})
    return results


async def collect_ocr(directory):
    directory=Path(directory);summary=json.loads((directory/'summary.json').read_text())
    files=sorted(directory.glob('frame-*.png'))+[directory/'final.png']
    cache={};observations=[]
    for file in files:
        frame=file.read_bytes();region=crop(frame);key=digest(region.tobytes())
        if key not in cache:cache[key]=await asyncio.to_thread(readings,region)
        observations.append({'evidence':file.name,'sha256':digest(frame),'crop_id':key})
    questions={};state={}
    for i,(key,values) in enumerate(cache.items()):
        qid=f'hud_{i}';state[qid]={'readings':values}
        choices={str(v['value']):'Literal score candidate produced by constrained HUD OCR' for v in values if v['value'] is not None and v['value']%10==0}
        choices['unknown']='OCR disagreement, missing digits, or insufficient evidence'
        if len(choices)==1:choices['unreadable']='No numerical score is readable'
        questions[qid]={'type':'choice','instructions':f'Select a score from `{qid}.readings` only if at least two OCR configurations agree on its integer value. Otherwise select unknown. These are visible score readings, not model quality ratings. Never invent or extrapolate a score.','criteria':choices}
    body={'model':'jev-latest','state':state,'questions':questions};player=JevPlayer();response=await player.request(body)
    accepted={}
    for i,(key,values) in enumerate(cache.items()):
        qid=f'hud_{i}';a=player.validate_choice(response['answers'][qid],questions[qid]['criteria'])
        choice=a['choice'];value=int(choice) if choice.isdigit() else None
        accepted[key]=value if value is not None and value%10==0 and sum(v['value']==value for v in values)>=2 else None
    for observation in observations:observation['value']=accepted[observation['crop_id']]
    supported=[r for i,r in enumerate(observations) if r['value'] is not None and i>0 and observations[i-1]['value']==r['value']]
    best=max(supported,key=lambda r:r['value'],default=None)
    report={'schema':'crackpots-jev-ocr-v1','request':body,'response':response,'ocr':cache,'observations':observations,
            'highest_supported_candidate':best['value'] if best else None,
            'note':'Experimental OCR consensus plus hosted Jev; NOT a calibrated exact-glyph decoder. Candidate only, not automatically ranked.'}
    (directory/'hud-jev.json').write_text(json.dumps(report,indent=2))
    summary['score_candidate']=report['highest_supported_candidate']
    summary['jev_hud']={'report':'hud-jev.json','method':'jev+three-OCR-configurations+temporal-repeat','usage':response.get('usage')}
    if best:summary['score_candidate_evidence']=best['evidence']
    (directory/'summary.json').write_text(json.dumps(summary,indent=2))
    records=[json.loads(l) for l in (directory/'decisions.jsonl').read_text().splitlines()]
    replay_html(directory,summary,records)
    print(f'Crackpots score candidate: {summary["score_candidate"]}; {len(cache)} distinct HUDs; see hud-jev.json',flush=True)
