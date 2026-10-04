import json
import subprocess
import unittest
from pathlib import Path


class ControllerTests(unittest.TestCase):
    def test_pure_ascii_states_follow_held_inputs_not_proposals(self):
        module=Path('games/arcade/atari-controller.js').resolve()
        code=f"const c=require({json.dumps(str(module))});console.log(JSON.stringify([null,[],[6],[7,0],[4,6],[5]].map(b=>c.snapshot(b))))"
        result=subprocess.run(['node','-e',code],capture_output=True,text=True,check=True)
        unknown,center,left,right,diagonal,down=json.loads(result.stdout)
        self.assertEqual(unknown['direction'],'unknown');self.assertEqual(center['direction'],'center')
        self.assertEqual(left['direction'],'left');self.assertFalse(left['fire'])
        self.assertEqual(right['direction'],'right');self.assertTrue(right['fire']);self.assertIn('(@@@)',right['frame'])
        self.assertEqual(diagonal['direction'],'up-left');self.assertEqual(down['direction'],'down')
        self.assertNotEqual(left['frame'],right['frame'])
