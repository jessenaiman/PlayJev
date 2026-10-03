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


def request_for(grids, font=FONT):
    distances=[{digit:sum(a!=b for row,example in zip(grid,pattern) for a,b in zip(row,example)) for digit,pattern in font.items()} for grid in grids]
    state = {'glyphs':grids,'examples':font,'pixel_mismatch_counts':distances,'legend':'# = observed score foreground pixel; . = background. Each glyph is a row-major text grid, left to right. Blank glyphs are leading spaces. Mismatch counts are exact cell comparisons, not model predictions; zero is an exact match.'}
    criteria = {**{k:'Digit '+k for k in font},'blank':'All cells dark, leading space','unknown':'Damaged, ambiguous or not a numeral'}
    questions = {f'digit_{i}':{'type':'choice','instructions':f'Read only `glyphs[{i}]` and `pixel_mismatch_counts[{i}]`. Select the unique digit with zero mismatches, blank if all cells are dark, or unknown if no exact template matches. Do not choose a nonzero mismatch or infer from gameplay.','criteria':criteria} for i in range(len(grids))}
    return {'model':'jev-latest','state':state,'questions':questions}


def assemble(grids, result, font=FONT):
    from .challenge import JevPlayer
    answers = [JevPlayer.validate_choice(result['answers'][f'digit_{i}'],request_for(grids,font)['questions'][f'digit_{i}']['criteria']) for i in range(len(grids))]
    digits = [a['choice'] for a in answers]
    # Exact pixel agreement gates acceptance; model confidence is not evidence.
    valid = all((d in font and grids[i]==font[d]) or
                (d=='blank' and all(set(row)=={'.'} for row in grids[i])) for i,d in enumerate(digits))
    text = ''.join(' ' if d=='blank' else d for d in digits)
    valid = valid and text.strip().isdigit() and ' ' not in text.strip()
    return {'value':int(text.strip()) if valid else None,'accepted':valid,'digits':digits,'answers':answers}


def exact_answers(grids,font=FONT):
    """Literal lookup needs no semantic inference; damaged glyphs stay unknown."""
    options=request_for(grids,font)['questions']
    answers={}
    for i,grid in enumerate(grids):
        matches=[digit for digit,pattern in font.items() if grid==pattern]
        selected='blank' if all(set(row)=={'.'} for row in grid) else matches[0] if len(matches)==1 else 'unknown'
        answers[f'digit_{i}']={'type':'choice','choice':selected,'confidence':1,
            'probabilities':{k:float(k==selected) for k in options[f'digit_{i}']['criteria']},
            'source':'deterministic-exact-font-lookup; confidence denotes lookup certainty, not game completion'}
    return answers


def read_score(game, frame):
    """Single-frame literal candidate; callers still require independent repeats."""
    if game=='space-invaders':extractor,font=digit_grids,FONT
    elif game=='crackpots':
        from .crackpots_score import digit_grids as extractor, FONT as font
    else:return None
    grids=extractor(frame)
    return assemble(grids,{'answers':exact_answers(grids,font)},font)['value']


async def collect(directory,typed=False):
    from .challenge import JevPlayer, ROOT, digest, replay_html
    from dotenv import load_dotenv
    load_dotenv(ROOT.parent/'.env',override=False)
    directory = Path(directory)
    summary = json.loads((directory/'summary.json').read_text())
    if summary['game']=='space-invaders':
        extractor,font=digit_grids,FONT
    elif summary['game']=='crackpots':
        from .crackpots_score import digit_grids as extractor, FONT as font
    else:
        raise ValueError('HUD layout supports Space Invaders and Crackpots')
    cache, observations = {}, []
    from .transports import inference
    provider=summary.get('config',{}).get('provider','ollaya')
    model,transport=inference(provider,summary.get('config',{}).get('model') if provider=='ollaya' else None)
    player = JevPlayer(model=model,transport=transport)
    frames = sorted(directory.glob('frame-*.png'))
    final=directory/'final.png'
    # Live final.png is commonly a copy of the last sampled frame. It cannot
    # supply a second temporal observation of a newly reached score.
    duplicate_final=bool(frames and final.read_bytes()==frames[-1].read_bytes())
    files = frames + ([] if duplicate_final else [final])
    frame_index={}
    index=directory/'frames.jsonl'
    if index.is_file():
        frame_index={r['evidence']:r for r in (json.loads(line) for line in index.read_text().splitlines())}
    all_glyphs = {tuple(g) for file in files for g in extractor(file.read_bytes())}
    blank_glyphs = {g for g in all_glyphs if all(set(row)=={'.'} for row in g)}
    unique = sorted(all_glyphs-blank_glyphs)
    body=request_for([list(g) for g in unique],font)
    body['model']=model
    if typed and unique:
        result=await player.request(body)
    else:
        result={'answers':exact_answers([list(g) for g in unique],font),
                'usage':{'input_tokens':0,'output_tokens':0},'transport':'deterministic-exact-font'}
    glyph_answers={g:result['answers'][f'digit_{i}'] for i,g in enumerate(unique)}
    options={**{k:'Digit '+k for k in font},'blank':'Leading space','unknown':'Unknown'}
    for g in blank_glyphs:
        glyph_answers[g]={'type':'choice','choice':'blank','confidence':1,
                          'probabilities':{k:float(k=='blank') for k in options},
                          'source':'deterministic-all-dark-pixels; no model judgment'}
    # Reuse identical glyph decisions rather than infer on every screenshot.
    for file in files:
        frame = file.read_bytes()
        grids = extractor(frame)
        key = json.dumps(grids)
        if key not in cache:
            assembled={'answers':{f'digit_{i}':glyph_answers[tuple(g)] for i,g in enumerate(grids)}}
            cache[key] = {**assemble(grids,assembled,font)}
        provenance=frame_index.get(file.name)
        if provenance and provenance['sha256']!=digest(frame):
            raise ValueError('Frame provenance hash mismatch')
        observations.append({'evidence':file.name,'sha256':digest(frame),'frame_interval':provenance,**cache[key]})
    accepted = [r for r in observations if r['accepted']]
    visible = [r for r in observations if any(d!='blank' for d in r['digits'])]
    # A repeat at the end or adjacent saved frames is required for recording.
    def independent(a,b):
        if not a['accepted'] or not b['accepted'] or a['value']!=b['value']:return False
        p,q=a['frame_interval'],b['frame_interval']
        if index.is_file():return bool(p and q and (p['after']<q['before'] or q['after']<p['before']))
        return a['evidence']!=b['evidence']  # legacy separate sampled files
    supported = [r for i,r in enumerate(observations) if r['accepted'] and
                 ((i>0 and independent(r,observations[i-1])) or
                  (i+1<len(observations) and independent(r,observations[i+1])))]
    best = max(supported,key=lambda r:r['value'],default=None)
    scorer=provider if typed else 'exact-templates'
    report = {'schema':'jev-hud-v1','provider':scorer,'model':model if typed else None,'unique_requests':int(typed and bool(unique)),'unique_glyphs':len(unique),'resolved_blank_glyphs':len(blank_glyphs),'request':body if typed else None,'response':result,'observations':observations,
              'accepted_frames':len(accepted),'highest_supported_score':best['value'] if best else None,
               'visible_hud_frames':len(visible),'duplicate_final_excluded':duplicate_final,
               'note':'Typed digit choices checked against literal glyph templates and repeated HUD evidence. Not human confirmation; not a game-over judgment.'}
    (directory/'hud-jev.json').write_text(json.dumps(report,indent=2))
    summary['jev_hud'] = {k:v for k,v in report.items() if k not in ('observations','request','response')}
    if best and summary['status'] in ('complete','stopped') and len(accepted)==len(visible):
        if summary.get('score_verified'):
            summary.setdefault('prior_score_reviews',[]).append({'score':summary['score'],'review':summary.get('score_review')})
        summary.update(score=best['value'],score_verified=True,score_review={
            'method':'typed-digit-choices+exact-pixel-template+temporal-repeat',
            'reviewer':scorer+'-pipeline','provider':scorer,'model':result.get('model'),'evidence':best['evidence'],'evidence_sha256':best['sha256'],
            'report':'hud-jev.json','note':report['note']})
    (directory/'summary.json').write_text(json.dumps(summary,indent=2))
    records = [json.loads(l) for l in (directory/'decisions.jsonl').read_text().splitlines()]
    replay_html(directory,summary,records)
    print(f'{directory}: {scorer} HUD score {report["highest_supported_score"]}; {report["unique_requests"]} inference requests, {len(unique)} glyphs; {len(accepted)}/{len(files)} accepted frames')


if __name__=='__main__':
    import argparse, asyncio
    parser = argparse.ArgumentParser()
    parser.add_argument('runs',nargs='+',type=Path)
    parser.add_argument('--typed',action='store_true',help='Explicitly invoke the recorded provider for glyph judgments instead of literal lookup')
    args = parser.parse_args()
    async def main():
        for directory in args.runs:
            await collect(directory,typed=args.typed)
    asyncio.run(main())
