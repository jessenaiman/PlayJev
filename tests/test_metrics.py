import unittest
from playjev.metrics import Metrics
from playjev.timing import DecisionClock


class MetricsTests(unittest.TestCase):
    def test_missing_reply_is_not_zero_and_pending_has_own_clock(self):
        m=Metrics('dig-dug');m.start_request({'source':{'before':100}},now=10)
        s=m.snapshot({},20,True,DecisionClock(),emulator_frame=112,now=10.25)
        self.assertIsNone(s['latency_ms'])
        self.assertEqual((s['pending_wait_ms'],s['pending_age_frames']),(250,12))
        self.assertIn('last reply: none yet',s['analytics'])
        self.assertIn('held inputs: unknown',s['analytics'])

    def test_last_issued_action_does_not_claim_current_buttons(self):
        m=Metrics('dig-dug');m.start_request(now=0)
        m.record({'applied':True,'collision_veto':False,'age_frames':8,'latency_s':0.1,
                  'executed_choice':'left','decision':{},'execution':{'expiry_frame':60}})
        s=m.snapshot({},100,False,DecisionClock(),buttons=[])
        self.assertIn('held inputs: released',s['analytics'])
        self.assertIn('last issued: left',s['ascii'])
        self.assertEqual(s['last_result']['outcome'],'accepted')

    def test_rejection_failure_cancellation_and_map_width(self):
        m=Metrics('dig-dug');m.start_request(now=0)
        m.record({'applied':False,'collision_veto':False,'age_frames':215,'latency_s':3.5,
                  'executed_choice':'noop','decision':{},'execution':{'reason':'stale'}})
        s=m.snapshot({},600,False,DecisionClock())
        self.assertEqual((s['rejected'],s['stale']),(1,1))
        self.assertIn('last result: stale',s['analytics'])
        self.assertTrue(all(len(line)==32 for line in s['ascii'].splitlines() if line.startswith(('+','|'))))
        m.start_request(now=1);m.finish_request('failed','allocation-limit')
        self.assertIn('last result: allocation-limit',m.snapshot({},0,False,DecisionClock())['analytics'])
        m.start_request(now=2);m.finish_request('cancelled')
        self.assertEqual((m.failed,m.cancelled),(1,1))
        self.assertIsNone(m.pending_request)
