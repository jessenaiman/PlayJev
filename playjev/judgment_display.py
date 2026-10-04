"""Read-only typed answer formatting; never selects or activates controls."""


def answer_lines(name,answer):
    if answer.get('type')=='score':
        heading=f'{name}: rating={answer["score"]:.2f} c={answer["confidence"]:.2f} (not HUD points)'
    elif answer.get('type')=='noul':
        return [f'{name}: p(yes)={answer["noul"]:.2f}']
    else:
        heading=f'{name}: {answer["choice"]} c={answer["confidence"]:.2f}'
    top=sorted(answer.get('probabilities',{}).items(),key=lambda item:-item[1])[:2]
    return [heading,'  '+' '.join(f'{key}:{value:.2f}' for key,value in top)]
