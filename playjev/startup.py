"""Startup-only Ollaya recipe. Never part of an action-policy request."""
import asyncio
import json
from .challenge import ROOT, JevPlayer
from .transports import inference, RecordedTransport, safety_report


async def check(directory,summary,events=None):
    proof=summary['participation']
    result={'recipe':'playjev/recipes/startup.json','passed':False,
            'code_input_effect_verified':proof['verified'],'baseline_score':proof['observations'][0]['score']}
    if not proof['verified']:return {**result,'reason':'native control/start evidence failed; no inference'}
    provider=summary['config']['provider'];model,transport=inference(provider,summary['config']['model'])
    logged=RecordedTransport(transport,directory/'startup-inference.jsonl',events);logged.context={'phase':'startup-check'}
    positions={r['choice']:(r['player_box'][0]+r['player_box'][2])/2 for r in proof['observations'] if r.get('player_box')}
    movement={'right_input_moved_player_right_pixels':positions['right']-positions['noop'],
              'left_input_moved_player_left_pixels':positions['noop']-positions['left']}
    body={'model':model,'state':{'input_effect_verified':proof['verified'],'resumed':proof['resumed'],
          'measured_control_response':movement,'game':proof['game'],
          'probe_contract':'Each input starts from the same restored state. Compare movement against no input. An edge can block one direction; the opposite direction still demonstrates control.',
          'initial_score':result['baseline_score'],'native_playable_screen_verified':True},
          'questions':json.loads((ROOT/'playjev/recipes/startup.json').read_text())}
    try:
        response=await asyncio.wait_for(logged.request(body),12)
        answer=JevPlayer.validate_choice(response['answers']['session'],body['questions']['session']['criteria'])
        result.update(answer=answer,passed=answer['choice']=='active',reason='native proof AND typed startup classification')
    except Exception as exc:result.update(error=safety_report(exc),reason='startup classification unavailable; no silent fallback')
    return result
