"""Thin gameplay orchestrator: observations -> JSON questions -> typed answer -> target."""
import json
from pathlib import Path
from .challenge import JevPlayer
from .crackpots_control import command
from .crackpots_state import tactical_state


class CrackpotsPlayer(JevPlayer):
    auxiliary_questions=False

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.last_target=None
        source=Path(__file__).parent
        self.policy=json.loads((source/'policies'/'crackpots.json').read_text())
        self.questions=json.loads((source/'recipes'/'crackpots-lane.json').read_text())

    def request_for(self,current):
        evidence=tactical_state(current,self.last_target,
            include_pursuit_evidence=self.policy['include_pursuit_evidence'])
        definition=self.questions['lane']
        available=(*evidence['pots'],'hold','scan')
        criteria={key:definition['criteria'][key] for key in available}
        return {'model':self.model,'state':evidence,
                'questions':{'lane':{**definition,'criteria':criteria}}}

    async def decide(self,state,game):
        body=self.request_for(state['current'])
        response=await self.request(body)
        answer=self.validate_choice(response['answers']['lane'],body['questions']['lane']['criteria'])
        evidence=body['state'];label=answer['choice']
        if label in evidence['pots']:target=evidence['pots'][label]['x']
        elif label=='scan':target=80
        else:target=evidence['player_x']
        self.last_target=target
        controls=command(evidence['player_x'],target,evidence['drop_ready'])
        return {
            'request':body,'response':response,'components':{'lane':answer},
            'confidence':answer['confidence'],**controls,
            'composition':'crackpots-model-lane/code-fresh-interception-trigger-v3',
        }
