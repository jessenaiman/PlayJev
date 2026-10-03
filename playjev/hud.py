"""Space Invaders HUD pixels -> small text grids -> hosted Jev choices.

No RAM reads, screenshot vision API, or guessed OCR numbers. ROM-specific layout.
"""
import hashlib
import io
import json
from pathlib import Path
from PIL import Image

# Three-column, five-row numeral examples, including Atari's sloped '1'.
FONT = {
    '0':['###','#.#','#.#','#.#','###'],
    '1':['.#.','##.','.#.','.#.','###'],
    '2':['###','..#','###','#..','###'],
    '3':['###','..#','###','..#','###'],
    '4':['#.#','#.#','###','..#','..#'],
    '5':['###','#..','###','..#','###'],
    '6':['#..','#..','###','#.#','###'],
    '7':['###','..#','..#','..#','..#'],
    '8':['###','#.#','###','#.#','###'],
    '9':['###','#.#','###','..#','..#'],
}


def digit_grids(frame):
    source = Image.open(io.BytesIO(frame)).convert('RGB')
    mask=Image.new('L',source.size)
    for y in range(min(source.height,round(source.height*0.12))):
        for x in range(round(source.width*0.43)):
            r,g,b=source.getpixel((x,y))
            if g>r+20 and g>b+20:mask.putpixel((x,y),255)
    grids=[]
    for left in (4,20,36,52):
        xs=[round((left+2+col*4)*source.width/160) for col in range(3)]
        rows=[y for y in range(round(source.height*0.02),round(source.height*0.11))
              if any(mask.getpixel((x,y)) for x in xs)]
        if not rows:
            grids.append(['...']*5);continue
        top,bottom=min(rows),max(rows)+1
        # Each digit can be vertically staggered by the Atari raster. Work on
        # native pixels rather than nearest-neighbor shrinking thin scanlines.
        grids.append([''.join('#' if any(mask.getpixel((x,y)) for y in range(
                         round(top+(bottom-top)*row/5),round(top+(bottom-top)*(row+1)/5))) else '.'
                         for x in xs) for row in range(5)])
    return grids


def request_for(grids):
    distances=[{digit:sum(a!=b for row,example in zip(grid,pattern) for a,b in zip(row,example)) for digit,pattern in FONT.items()} for grid in grids]
    state = {'glyphs':grids,'examples':FONT,'pixel_mismatch_counts':distances,'legend':'# = lit green player-one HUD pixel; . = background. Each glyph is 3 columns by 5 rows, left to right. Blank glyphs are leading spaces. Mismatch counts are exact cell comparisons, not model predictions; zero is an exact match.'}
    criteria = {**{k:'Digit '+k for k in FONT},'blank':'All cells dark, leading space','unknown':'Damaged, ambiguous or not a numeral'}
    questions = {f'digit_{i}':{'type':'choice','instructions':f'Read only `glyphs[{i}]` and `pixel_mismatch_counts[{i}]`. Select the unique digit with zero mismatches, blank if all cells are dark, or unknown if no exact template matches. Do not choose a nonzero mismatch or infer from gameplay.','criteria':criteria} for i in range(len(grids))}
    return {'model':'jev-latest','state':state,'questions':questions}


def assemble(grids, result):
    from .challenge import JevPlayer
    answers = [JevPlayer.validate_choice(result['answers'][f'digit_{i}'],request_for(grids)['questions'][f'digit_{i}']['criteria']) for i in range(4)]
    digits = [a['choice'] for a in answers]
    # Exact pixel agreement gates acceptance; model confidence is not evidence.
    valid = all((d in FONT and grids[i]==FONT[d]) or
                (d=='blank' and all(row=='...' for row in grids[i])) for i,d in enumerate(digits))
    text = ''.join(' ' if d=='blank' else d for d in digits)
    valid = valid and text.strip().isdigit() and ' ' not in text.strip()
    return {'value':int(text.strip()) if valid else None,'accepted':valid,'digits':digits,'answers':answers}


async def collect(directory):
    from .challenge import JevPlayer, ROOT, digest, replay_html
    from dotenv import load_dotenv
    load_dotenv(ROOT.parent/'.env',override=False)
    directory = Path(directory)
    summary = json.loads((directory/'summary.json').read_text())
    if summary['game']!='space-invaders':
        raise ValueError('HUD layout currently supports Space Invaders only')
    cache, observations = {}, []
    player = JevPlayer()
    files = sorted(directory.glob('frame-*.png')) + [directory/'final.png']
    unique = list({tuple(g) for file in files for g in digit_grids(file.read_bytes())})
    body=request_for([list(g) for g in unique])
    result=await player.request(body)
    glyph_answers={g:result['answers'][f'digit_{i}'] for i,g in enumerate(unique)}
    # Reuse identical glyph decisions rather than infer on every screenshot.
    for file in files:
        frame = file.read_bytes()
        grids = digit_grids(frame)
        key = json.dumps(grids)
        if key not in cache:
            assembled={'answers':{f'digit_{i}':glyph_answers[tuple(g)] for i,g in enumerate(grids)}}
            cache[key] = {**assemble(grids,assembled)}
        observations.append({'evidence':file.name,'sha256':digest(frame),**cache[key]})
    accepted = [r for r in observations if r['accepted']]
    visible = [r for r in observations if any(d!='blank' for d in r['digits'])]
    # A repeat at the end or adjacent saved frames is required for recording.
    supported = [r for i,r in enumerate(observations) if r['accepted'] and
                 ((i>0 and observations[i-1]['value']==r['value']) or
                  (i+1<len(observations) and observations[i+1]['value']==r['value']))]
    best = max(supported,key=lambda r:r['value'],default=None)
    report = {'schema':'jev-hud-v1','unique_requests':1,'unique_glyphs':len(unique),'request':body,'response':result,'observations':observations,
              'accepted_frames':len(accepted),'highest_supported_score':best['value'] if best else None,
              'visible_hud_frames':len(visible),
              'note':'Jev digit choices checked against literal glyph templates and repeated HUD evidence. Not human confirmation; not a game-over judgment.'}
    (directory/'hud-jev.json').write_text(json.dumps(report,indent=2))
    summary['jev_hud'] = {k:v for k,v in report.items() if k not in ('observations','request','response')}
    if best and summary['status'] in ('complete','stopped') and len(accepted)==len(visible):
        if summary.get('score_verified'):
            summary.setdefault('prior_score_reviews',[]).append({'score':summary['score'],'review':summary.get('score_review')})
        summary.update(score=best['value'],score_verified=True,score_review={
            'method':'jev-digit-choices+exact-pixel-template+temporal-repeat',
            'reviewer':'jev-pipeline','evidence':best['evidence'],'evidence_sha256':best['sha256'],
            'report':'hud-jev.json','note':report['note']})
    (directory/'summary.json').write_text(json.dumps(summary,indent=2))
    records = [json.loads(l) for l in (directory/'decisions.jsonl').read_text().splitlines()]
    replay_html(directory,summary,records)
    print(f'{directory}: Jev HUD score {report["highest_supported_score"]}; 1 batched request, {len(unique)} glyphs; {len(accepted)}/{len(files)} accepted frames')


if __name__=='__main__':
    import argparse, asyncio
    parser = argparse.ArgumentParser()
    parser.add_argument('runs',nargs='+',type=Path)
    args = parser.parse_args()
    async def main():
        for directory in args.runs:
            await collect(directory)
    asyncio.run(main())
