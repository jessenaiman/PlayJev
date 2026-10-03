"""Frame provenance and stale-policy guards shared by asynchronous controllers."""
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class FrameStamp:
    before: int
    after: int
    sha256: str

    def __post_init__(self):
        if self.before<0 or self.after<self.before:
            raise ValueError('Invalid capture frame interval')


@dataclass(frozen=True)
class DecisionEnvelope:
    attempt_id: str
    request_id: int
    source: FrameStamp
    policy_generation: int = 0
    max_age_frames: int = 60

    @property
    def deadline(self):
        # Use the earliest possible capture frame, not inference completion.
        return self.source.before+self.max_age_frames

    def reject_reason(self,now,attempt_id,policy_generation):
        if attempt_id!=self.attempt_id:return 'wrong-attempt'
        if policy_generation!=self.policy_generation:return 'changed-policy'
        if now<self.source.before:return 'frame-clock-regressed'
        if now>self.deadline:return 'stale'
        return None

    def json(self):
        return asdict(self)
