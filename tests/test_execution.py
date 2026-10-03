import unittest
from pathlib import Path
from playwright.async_api import async_playwright
from playjev.execution import FrameStamp, DecisionEnvelope
from playjev.runtime import crackpots_prepare


class ExecutionTests(unittest.TestCase):
    def test_capture_interval_and_deadline(self):
        with self.assertRaises(ValueError):FrameStamp(12,10,'hash')
        e=DecisionEnvelope('attempt',1,FrameStamp(100,103,'hash'))
        self.assertEqual(e.deadline,160)
        self.assertIsNone(e.reject_reason(160,'attempt',0))
        self.assertEqual(e.reject_reason(161,'attempt',0),'stale')
        self.assertEqual(e.reject_reason(110,'other',0),'wrong-attempt')
        self.assertEqual(e.reject_reason(110,'attempt',1),'changed-policy')
        self.assertEqual(e.reject_reason(99,'attempt',0),'frame-clock-regressed')

    def test_drop_rechecked_after_target_disappears(self):
        current={'player':{'box':[30,24,36,40]},'pots':[],'pot_row':46,'window_y':76,'bug_tracks':[]}
        decision={'choice':'fire','target_x':33,'components':{'drop':{'choice':'fire'}}}
        self.assertEqual(crackpots_prepare(current,decision),('noop',30,False))


class BrowserControlsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.pw=await async_playwright().start()
        self.browser=await self.pw.chromium.launch()
        self.page=await self.browser.new_page()
        await self.page.set_content('<div id="status"></div>')
        await self.page.evaluate('''()=>{
            window.frame=100;window.events=[];
            window.EJS_emulator={pause(){},play(){},gameManager:{getFrameNum:()=>window.frame,simulateInput:(p,b,v)=>events.push([b,v])}};
        }''')
        await self.page.add_script_tag(path=str(Path(__file__).resolve().parents[1]/'games/emulatorjs/live-controls.js'))
        await self.page.evaluate('()=>{installLiveControls();window.liveRunning=true;}')

    async def asyncTearDown(self):
        await self.browser.close();await self.pw.stop()

    async def apply(self,**changes):
        plan={'buttons':[7],'rest':[0],'frames':6,'deadline':160,'policy_generation':0,**changes}
        return await self.page.evaluate('window.applyLive',plan)

    async def test_stale_execution_releases_previous_input(self):
        self.assertTrue((await self.apply())['applied'])
        await self.page.evaluate('window.frame=161')
        result=await self.apply()
        self.assertEqual(result['reason'],'stale')
        self.assertEqual(await self.page.evaluate('window.liveButtons'),[])
        self.assertIn([7,0],await self.page.evaluate('window.events'))

    async def test_frame_duration_rest_and_expiry(self):
        result=await self.apply()
        self.assertEqual(result['end_frame'],106)
        await self.page.evaluate('window.frame=106')
        await self.page.wait_for_function('window.liveButtons.length===1&&window.liveButtons[0]===0')
        await self.page.evaluate('window.frame=136')
        await self.page.wait_for_function('window.liveButtons.length===0')

    async def test_stop_policy_and_invalid_plan(self):
        self.assertEqual((await self.apply(policy_generation=1))['reason'],'changed-policy')
        self.assertEqual((await self.apply(buttons=[3]))['reason'],'invalid-buttons')
        self.assertEqual((await self.apply(frames=31))['reason'],'invalid-duration')
        await self.page.evaluate('window.liveStopped=true')
        self.assertEqual((await self.apply())['reason'],'stopped')
