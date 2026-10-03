import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from playjev import savepoint as s


class SavepointTests(unittest.TestCase):
    def test_source_scope_excludes_credentials_artifacts_and_external_paths(self):
        for name in ('playjev/metrics.py','tests/test_savepoint.py','docs/DIG-DUG.md','scripts/check-in','ATARI2600.md'):
            self.assertTrue(s.allowed(name),name)
        for name in ('','.env','docs/.env.local','runs/replay.webm','games/rom.a26','data/a.json','../other.py','/other.py','oauth.json'):
            self.assertFalse(s.allowed(name),name)

    def test_guard_checks_known_keys_and_never_echoes_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'secret.py').write_text('value = "private-value"')
            with patch.dict('os.environ',{'OPENROUTER_API_KEY':'private-value'}):
                with self.assertRaises(s.SavepointError) as caught:s.secret_guard(root,['secret.py'])
            self.assertNotIn('private-value',str(caught.exception))

    def test_procedure_commits_pushes_and_verifies_only_fixed_fork(self):
        calls=[]
        def git(root,*args,**kwargs):
            calls.append(args)
            if args[:2]==('rev-parse','--show-toplevel'):return str(root)+'\n'
            if args[0]=='branch':return s.BRANCH+'\n'
            if args[0]=='remote':return s.REMOTE+'\n'
            if args[0]=='status':return ' M docs/a.md\0?? runs/ignored.txt\0'
            if args[:3]==('diff','--cached','--name-only'):return 'docs/a.md\0'
            if args[:2]==('diff','--cached'):return 'source diff'
            if args[:2]==('rev-parse','HEAD'):return 'abc123\n'
            if args[0]=='ls-remote':return 'abc123\trefs/heads/'+s.BRANCH+'\n'
            return ''
        with tempfile.TemporaryDirectory() as tmp,patch.object(s,'git',git),patch.object(s,'secret_guard'),patch.object(s,'advisory'),patch.object(s.subprocess,'run',return_value=SimpleNamespace(returncode=0)):
            s.save(Path(tmp),'Refresh docs')
        self.assertIn(('add','-A','--','docs/a.md'),calls)
        self.assertIn(('commit','-m','Refresh docs'),calls)
        self.assertIn(('push','fork','HEAD:refs/heads/'+s.BRANCH),calls)
        self.assertFalse(any('runs/ignored.txt' in call for call in calls))
        self.assertFalse(any(call[0] in ('merge','checkout','switch','reset') for call in calls))

    def test_bad_branch_and_staged_artifact_fail_before_staging(self):
        for bad_branch,artifact in ((True,False),(False,True)):
            calls=[]
            def git(root,*args,**kwargs):
                calls.append(args)
                if args[:2]==('rev-parse','--show-toplevel'):return str(root)
                if args[0]=='branch':return 'main' if bad_branch else s.BRANCH
                if args[0]=='remote':return s.REMOTE
                if args[0]=='status':return 'A  runs/artifact.json\0' if artifact else ''
                return ''
            with patch.object(s,'git',git),self.assertRaises(s.SavepointError):s.save(Path('/project'),'Save')
            self.assertFalse(any(call[0] in ('add','commit','push') for call in calls))

    def test_optional_advisory_failure_does_not_require_hosted_or_block(self):
        import asyncio
        with patch.object(s,'git',return_value='.git/review.jsonl'),patch.object(s,'RecordedTransport') as recorded:
            recorded.return_value.request.side_effect=RuntimeError('offline')
            asyncio.run(s.advisory(Path('/project'),'Save',['docs/a.md'],'kev:0.8b'))

    def test_security_advisory_is_local_bounded_and_prioritizes_code(self):
        import asyncio
        request=AsyncMock(return_value={'answers':{name:{'type':'noul','noul':0.4} for name in ('security_risk','substantive')}})
        diff='diff --git a/docs/a.md b/docs/a.md\n'+'docs '*2000+'\ndiff --git a/playjev/example.py b/playjev/example.py\n+safe code\n'
        with patch.object(s,'git',return_value='.git/review.jsonl'),patch.object(s,'RecordedTransport') as recorded:
            recorded.return_value.request=request
            asyncio.run(s.advisory(Path('/project'),'Save',['docs/a.md','playjev/example.py'],'kev:0.8b',diff))
        body=request.call_args.args[0]
        self.assertTrue(body['state']['partial_diff'])
        self.assertTrue(body['state']['diff_excerpt'].startswith('diff --git a/playjev/'))
        self.assertLessEqual(len(body['state']['diff_excerpt']),6000)
        self.assertEqual(body['model'],'kev:0.8b')
        self.assertIn('security_risk',body['questions'])

    def test_time_budget_is_shared_and_stops_expired_commands(self):
        with patch.object(s.time,'monotonic',return_value=100):
            token=s.DEADLINE.set(103)
            try:self.assertEqual(s.budget(60),3)
            finally:s.DEADLINE.reset(token)
            token=s.DEADLINE.set(99)
            try:
                with self.assertRaises(s.SavepointError):s.budget(8)
            finally:s.DEADLINE.reset(token)

    def test_real_index_handles_pre_staged_deletions_and_unstaged_renames(self):
        # Local Git only; push and inference are mocked, tests do not recurse.
        run=subprocess.run
        def execute(argv,**kwargs):
            if argv[:3]==[sys.executable,'-m','unittest']:return SimpleNamespace(returncode=0)
            return run(argv,**kwargs)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'docs').mkdir()
            def git(*args):return s.git(root,*args)
            git('init','-b',s.BRANCH)
            git('config','user.name','Offline Test');git('config','user.email','test@example.invalid')
            git('remote','add','fork',s.REMOTE)
            for name in ('deleted.md','old.md'):(root/'docs'/name).write_text('Initial source\n')
            git('add','docs');git('commit','-m','Fixture')
            git('rm','docs/deleted.md')
            (root/'docs'/'old.md').rename(root/'docs'/'renamed.md')
            (root/'runs').mkdir();(root/'runs'/'evidence.json').write_text('{}')
            with patch.object(s.subprocess,'run',side_effect=execute),patch.object(s,'advisory',new=AsyncMock()) as review,patch.object(s,'push') as push:
                s.save(root,'Rename source and retain local evidence')
            review.assert_awaited_once();push.assert_called_once_with(root)
            self.assertEqual(git('ls-files').splitlines(),['docs/renamed.md'])
            self.assertTrue((root/'runs'/'evidence.json').exists())
            self.assertEqual(git('log','-1','--format=%s').strip(),'Rename source and retain local evidence')

    def test_check_only_never_stages_commits_pushes_or_calls_inference(self):
        def git(root,*args,**kwargs):
            if args[:2]==('rev-parse','--show-toplevel'):return str(root)
            if args[0]=='branch':return s.BRANCH
            if args[0]=='remote':return s.REMOTE
            if args[0]=='status':return ' M docs/a.md\0'
            return ''
        with patch.object(s,'git',side_effect=git) as command,patch.object(s,'secret_guard'),patch.object(s,'advisory') as review,patch.object(s.subprocess,'run',return_value=SimpleNamespace(returncode=0)):
            s.save(Path('/project'),'Preview',check_only=True)
        review.assert_not_called()
        self.assertFalse(any(call.args[1] in ('add','commit','push') for call in command.call_args_list))
