import unittest
from pathlib import Path


class RunbookTests(unittest.TestCase):
    def test_atari2600_runbook_stays_within_100_lines(self):
        runbook=Path(__file__).resolve().parents[1]/'ATARI2600.md'
        lines=runbook.read_text().splitlines()
        self.assertGreater(len(lines),0)
        self.assertLessEqual(len(lines),100,'Keep detailed reference material in docs/, not the compact runbook')

    def test_task_list_contains_only_open_tasks(self):
        root=Path(__file__).resolve().parents[1]
        tasks=(root/'docs'/'ATARI-TASKS.md').read_text()
        self.assertIn('## Gameplay milestones',tasks)
        self.assertIn('- [ ]',tasks)
        self.assertNotRegex(tasks,r'(?im)^\s*-\s*\[[xX]\]')
        self.assertNotRegex(tasks,r'(?im)^#{1,6}\s+.*(?:latest evidence|review checkpoint|completed tasks|work log)')

    def test_no_links_to_retired_history_pages(self):
        root=Path(__file__).resolve().parents[1]
        retired=('ARCADE-CHECKPOINT.md','ATARI-CHECKPOINT.md','RESUME-DISCOVERY-CHECKPOINT.md')
        for file in [root/'README.md',root/'ATARI2600.md',*(root/'docs').glob('*.md')]:
            with self.subTest(file=file.name):
                self.assertFalse(any(name in file.read_text() for name in retired))

    def test_operating_docs_use_the_project_save_script_not_an_external_tool(self):
        root=Path(__file__).resolve().parents[1]
        for name in ('ATARI2600.md','docs/CHECK-IN.md','docs/ARCADE.md'):
            text=(root/name).read_text()
            self.assertIn('./scripts/check-in',text)
            self.assertNotIn('jev-commit check',text)
        guide=(root/'docs/CHECK-IN.md').read_text()
        self.assertIn('115-second',guide)
        self.assertIn('atari-continuous-jev',guide)

    def test_current_guides_do_not_archive_test_counts_or_work_logs(self):
        root=Path(__file__).resolve().parents[1]
        for name in ('ARCADE.md','TESTING-ATARI.md','ASCII-REPORTING-REVIEW.md','ATARI-RESULTS.md','REFACTOR-REVIEW.md'):
            with self.subTest(file=name):
                text=(root/'docs'/name).read_text()
                self.assertNotRegex(text,r'(?i)\b\d+ tests passed\b|Latest recorded|Read-only delegated review|## Recorded checks')
