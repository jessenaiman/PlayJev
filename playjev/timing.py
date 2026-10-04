"""Code measures the clock; a typed Jev gate selects the next bounded cycle."""
INTERVALS={'urgent':6,'normal':18,'wait':30,'patient':60}
QUESTION={'type':'choice','instructions':'When should the next gameplay decision cycle start? Use `decision_clock` and the observed threats/intercepts. urgent: imminent collision or short interception; normal: active tracking; wait: waiting for an object/animation; patient: empty scene or a long wait. This does not restart the game. Code measures/enforces the frame clock and expires stale controls.','criteria':{
    'urgent':'Restart decision cycle after 6 game frames',
    'normal':'Restart decision cycle after 18 game frames',
    'wait':'Wait 30 game frames before restarting the decision cycle',
    'patient':'Wait 60 game frames before restarting the decision cycle'}}


class DecisionClock:
    def __init__(self):
        self.started_frame=0;self.next_frame=0;self.interval='normal'

    def state(self,frame):
        return {'elapsed_frames':max(0,frame-self.started_frame),'next_cycle_frame':self.next_frame,
                'due':frame>=self.next_frame,'last_interval':self.interval,
                'meaning':'Clock for model decision cycles, not a game reset or game-over timer'}

    def due(self,frame):return frame>=self.next_frame

    def restart(self,frame,answer):
        from .challenge import JevPlayer
        validated=JevPlayer.validate_choice(answer,INTERVALS)
        self.interval=validated['choice'];self.started_frame=frame
        self.next_frame=frame+INTERVALS[self.interval]
        return validated

    def restart_code(self,frame,interval='normal'):
        if interval not in INTERVALS:raise ValueError('Invalid code-owned cycle')
        self.interval=interval;self.started_frame=frame
        self.next_frame=frame+INTERVALS[interval]
        return {'source':'code-fixed-cycle','interval':interval,'frames':INTERVALS[interval]}
