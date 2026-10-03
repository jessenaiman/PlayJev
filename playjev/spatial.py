"""Native pixels -> normalized coordinates -> canvas-local display projection."""
import math


def evidence(current,canvas,source=(160,210),content=None):
    content=content or canvas
    player=current.get('player');box=player['box'] if player else None
    normalized=[(v+(1 if i>=2 else 0))/source[i%2] for i,v in enumerate(box)] if box else None
    projected=[content['left']+normalized[0]*content['width'],content['top']+normalized[1]*content['height'],
               content['left']+normalized[2]*content['width'],content['top']+normalized[3]*content['height']] if box else None
    valid=all(math.isfinite(v) for rect in (canvas,content) for v in rect.values()) and all(rect[k]>0 for rect in (canvas,content) for k in ('width','height'))
    valid=valid and content['left']>=canvas['left'] and content['top']>=canvas['top'] and content['left']+content['width']<=canvas['left']+canvas['width']+1e-6 and content['top']+content['height']<=canvas['top']+canvas['height']+1e-6
    valid=valid and (normalized is None or all(math.isfinite(v) and 0<=v<=1 for v in normalized) and box[0]<=box[2] and box[1]<=box[3])
    return {'source_coordinates':list(source),'canvas_rect':canvas,'content_rect':content,'native_player_box':box,
            'normalized_player_box':normalized,'projected_player_box':projected,
            'code_bounds_valid':valid,'player_observed':player is not None,
            'target_count':len(current.get('aliens',current.get('bugs',[]))),
            'note':'Native coordinates normalized inside the rendered content rectangle, excluding canvas letterboxing. Missing player is unknown, not game over.'}


QUESTIONS={
    'perception_check':{'type':'noul','instructions':'Does `accuracy_evidence` support a usable observed player location in native source coordinates? An absent player or out-of-bounds source box means no. This checks provided evidence, not unseen screenshot pixels.'},
    'projection_check':{'type':'noul','instructions':'Does `accuracy_evidence` describe a consistent mapping from native_player_box through normalized_player_box to projected_player_box within content_rect, excluding canvas letterboxing? Respect code_bounds_valid. No observed player means the current player projection is unknown, so answer no. This is a diagnostic judgment, not proof that a rendered overlay matches pixels.'},
}
