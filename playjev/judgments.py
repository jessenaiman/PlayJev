"""Validate typed judgments without turning model confidence into evidence."""
import math


def finite_number(value,low,high):
    return type(value) in (int,float) and math.isfinite(value) and low<=value<=high


def score_answer(answer,levels):
    keys={str(i) for i in range(len(levels))}
    probabilities=answer.get('probabilities',{})
    if (answer.get('type')!='score' or set(probabilities)!=keys or
            any(not finite_number(value,0,1) for value in probabilities.values()) or
            abs(sum(probabilities.values())-1)>0.02):
        raise ValueError('Invalid Score distribution')
    if not finite_number(answer.get('score'),0,len(levels)-1):
        raise ValueError('Invalid Score position')
    if not finite_number(answer.get('confidence'),0,1):
        raise ValueError('Invalid Score confidence')
    if answer.get('legend')!={str(i):level for i,level in enumerate(levels)}:
        raise ValueError('Score legend differs from supplied levels')
    mean=sum(int(key)*value for key,value in probabilities.items())
    # Hosted answers display probabilities and scores rounded to two decimals.
    # Bound the accumulated rounding error; retain every returned value unchanged.
    rounding_bound=0.005*(sum(range(len(levels)))+1)+1e-9
    if abs(mean-answer['score'])>max(0.02,rounding_bound):
        raise ValueError('Score differs from its probability-weighted position')
    return answer
