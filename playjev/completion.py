"""Completion-only Ollaya audit; no gameplay action or improvement questions."""
import asyncio
import json
from .challenge import ROOT, JevPlayer
from .transports import inference, RecordedTransport, safety_report


async def check(directory,summary,state,events=None):
    checks=state['checks']
    expected='progressed' if checks['score_increased'] else 'no_gain' if checks['started'] else 'not_started'
    result={'recipe':'playjev/recipes/completion.json','passed':False,'expected_class':expected,
            'ending':state['ending'],'loss_verified':state['loss_verified'],
            'game_completed':False,'checks':checks}
    if summary.get('safety_fallback') or summary.get('score_error'):
        return {**result,'reason':'Gameplay inference failed; preserve evidence without an extra inference call'}
    model,transport=inference(summary['config'].get('provider','ollaya'),summary['config'].get('model'))
    logged=RecordedTransport(transport,directory/'completion-inference.jsonl',events);logged.context={'phase':'completion-check'}
    body={'model':model,'state':{'checks':checks,'ending':state['ending'],'loss_verified':state['loss_verified']},
          'questions':json.loads((ROOT/'playjev/recipes/completion.json').read_text())}
    try:
        response=await asyncio.wait_for(logged.request(body),12)
        answer=JevPlayer.validate_choice(response['answers']['session'],body['questions']['session']['criteria'])
        result.update(answer=answer,model_class=answer['choice'],
                      passed=expected=='progressed' and answer['choice']==expected,
                      classification_agrees=answer['choice']==expected)
    except Exception as exc:result.update(error=safety_report(exc),reason='Completion audit unavailable; no silent fallback')
    (directory/'completion-check.json').write_text(json.dumps(result,indent=2))
    return result
