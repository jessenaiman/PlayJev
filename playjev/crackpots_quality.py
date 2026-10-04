"""Code shortlists opportunities; independent Score judgments rank pursuit evidence."""
import json
from pathlib import Path
from .judgments import score_answer


class QualityTactics:
    composition='crackpots-shortlist/model-Score-ranking/code-fresh-drop-v1'
    recipe='recipes/crackpots-quality.json'
    include_interception_evidence=True

    def __init__(self):
        self.questions=json.loads((Path(__file__).parent/self.recipe).read_text())

    def questions_for(self,evidence):
        # Known geometry/numeric eligibility stays in code, not in model arithmetic.
        viable=[(label,pot) for label,pot in evidence['pots'].items()
                if pot['catchable_bugs']>0 and pot['arrival_frames'] is not None]
        viable.sort(key=lambda pair:(-pair[1]['catchable_bugs'],pair[1]['arrival_frames'],pair[0]))
        evidence['candidates']={slot:{'pot':label,**pot}
            for slot,(label,pot) in zip(('primary','secondary'),viable[:2])}
        evidence['candidate_scope']='At most two geometry-shortlisted opportunities; unavailable and zero-catch pots are excluded by code. Scores cannot restore omitted candidates.'
        return {slot+'_quality':self.questions[slot+'_quality'] for slot in evidence['candidates']}

    def model_state(self,evidence):
        relevant={hit['bug'] for candidate in evidence['candidates'].values()
                  for hit in candidate.get('intercepts',[])}
        return {'player_x':evidence['player_x'],'candidates':evidence['candidates'],
                'bugs':[bug for bug in evidence.get('bugs',[]) if bug['id'] in relevant],
                'estimates':'Predicted intercepts, not guaranteed catches. Unmeasured tracks use fallback motion.'}

    def select(self,evidence,answers,questions):
        if set(answers)!=set(questions):raise ValueError('Candidate Score set mismatch')
        components={key:score_answer(answers[key],question['criteria']) for key,question in questions.items()}
        ranking=[]
        for slot,candidate in evidence['candidates'].items():
            answer=components[slot+'_quality']
            ranking.append({'pot':candidate['pot'],'score':answer['score'],
                'normalized_score':answer['score']/(len(questions[slot+'_quality']['criteria'])-1),
                'arrival_frames':candidate['arrival_frames'],'slot':slot})
        ranking.sort(key=lambda row:(-row['normalized_score'],row['arrival_frames'],row['pot']))
        label=ranking[0]['pot'] if ranking else 'scan' if evidence.get('bugs') else 'hold'
        return {'selected_target':label,'selection_source':'code-ranked-model-Scores' if ranking else 'code-no-estimated-intercept',
                'confidence':components[ranking[0]['slot']+'_quality']['confidence'] if ranking else 0,
                'components':components,'candidate_ranking':ranking}
