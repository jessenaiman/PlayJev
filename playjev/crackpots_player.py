"""Thin gameplay orchestrator: observations -> JSON questions -> typed answer -> target."""
import json
from pathlib import Path
from .challenge import JevPlayer
from .crackpots_control import command
from .crackpots_state import tactical_state
from .crackpots_lane import LaneTactics
from .crackpots_quality import QualityTactics


class CrackpotsPlayer(JevPlayer):
    auxiliary_questions=False

    def __init__(self,*args,tactics=None,**kwargs):
        super().__init__(*args,**kwargs)
        self.last_target=None
        source=Path(__file__).parent
        self.policy=json.loads((source/'policies'/'crackpots.json').read_text())
        implementations={'lane':LaneTactics,'quality':QualityTactics}
        self.tactics=tactics or implementations[self.policy.get('tactical_mode','lane')]()

    def request_for(self,evidence):
        questions=self.tactics.questions_for(evidence)
        return {'model':self.model,'state':self.tactics.model_state(evidence),'questions':questions}

    async def decide(self,state,game):
        evidence=tactical_state(state['current'],self.last_target,
            include_pursuit_evidence=self.policy['include_pursuit_evidence'],
            include_interception_evidence=self.tactics.include_interception_evidence)
        body=self.request_for(evidence)
        response=(await self.request(body) if body['questions'] else
                  {'model':self.model,'answers':{},'usage':{'input_tokens':0,'output_tokens':0},
                   'transport':'code-no-inference'})
        selection=self.tactics.select(evidence,response['answers'],body['questions'])
        label=selection['selected_target']
        if label in evidence['pots']:target=evidence['pots'][label]['x']
        elif label=='scan':target=80
        else:target=evidence['player_x']
        self.last_target=target
        controls=command(evidence['player_x'],target,evidence['drop_ready'])
        return {
            'request':body,'response':response,'observations':evidence,**selection,**controls,
            'composition':self.tactics.composition,
        }
