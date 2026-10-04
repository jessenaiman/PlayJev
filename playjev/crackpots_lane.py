"""Baseline single-Choice tactics; the player owns orchestration, not this rubric."""
import json
from pathlib import Path
from .challenge import JevPlayer


class LaneTactics:
    composition='crackpots-model-lane/code-fresh-interception-trigger-v3'
    recipe='recipes/crackpots-lane.json'
    include_interception_evidence=False

    def __init__(self):
        self.questions=json.loads((Path(__file__).parent/self.recipe).read_text())

    def questions_for(self,evidence):
        definition=self.questions['lane']
        criteria={key:definition['criteria'][key] for key in (*evidence['pots'],'hold','scan')}
        return {'lane':{**definition,'criteria':criteria}}

    def model_state(self,evidence):
        return evidence

    def select(self,evidence,answers,questions):
        answer=JevPlayer.validate_choice(answers['lane'],questions['lane']['criteria'])
        return {'selected_target':answer['choice'],'selection_source':'model-Choice',
                'confidence':answer['confidence'],'components':{'lane':answer}}
