"""No-inference regressions through the unmodified upstream game harness."""
import hashlib
import unittest
from playjev.env import VecGame


class UpstreamHarnessTests(unittest.IsolatedAsyncioTestCase):
    async def test_invaders_identical_seed_actions_and_pixel_frames(self):
        async with VecGame('invaders',n=2) as env:
            observations=await env.reset([5000,5000])
            self.assertEqual([a['name'] for a in env.actions],['left','right','noop'])
            for step in range(40):
                a,b=observations
                self.assertFalse(a.get('errors'));self.assertFalse(b.get('errors'))
                for key in ('score','done','t'):
                    self.assertEqual(a[key],b[key],(step,key))
                self.assertEqual(hashlib.sha256(a['frame']).hexdigest(),hashlib.sha256(b['frame']).hexdigest(),step)
                if a['done']:break
                observations=await env.step([step%3,step%3])
            self.assertGreater(observations[0]['t'],0)
