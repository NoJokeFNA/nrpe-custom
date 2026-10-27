import unittest
from unittest.mock import Mock

from scripts.delete_merged_topic import cleanup


class BranchCleanupTests(unittest.TestCase):
    def event(self):
        return {'pull_request': {'merged': True,
            'base': {'ref': 'develop', 'repo': {'full_name': 'owner/repo'}},
            'head': {'ref': 'feat/example', 'sha': 'a' * 40, 'repo': {'full_name': 'owner/repo'}}}}

    def test_long_lived_unmerged_wrong_base_and_external_branches_never_reach_git(self):
        for field, value in [('head.ref', 'master'), ('head.ref', 'develop'),
                             ('head.ref', 'work'), ('base.ref', 'master'),
                             ('merged', False), ('head.repo.full_name', 'external/repo')]:
            event = self.event()
            current = event['pull_request']
            *parents, key = field.split('.')
            for name in parents:
                current = current[name]
            current[key] = value
            call = Mock()
            with self.subTest(field=field, value=value):
                self.assertFalse(cleanup(event, 'owner/repo', call))
                call.assert_not_called()

    def test_changed_absent_or_still_needed_branch_is_retained(self):
        for responses in [('', '[{"id":1}]'), ('', '[]', ''), ('', '[]', 'b' * 40 + '\trefs/heads/feat/example')]:
            call = Mock(side_effect=responses)
            self.assertFalse(cleanup(self.event(), 'owner/repo', call))
            self.assertFalse(any(c.args[0][:2] == ['git', 'push'] for c in call.call_args_list))

    def test_deletion_uses_expected_sha_lease(self):
        call = Mock(side_effect=['', '[]', 'a' * 40 + '\trefs/heads/feat/example', ''])
        self.assertTrue(cleanup(self.event(), 'owner/repo', call))
        self.assertEqual(call.call_args.args[0], ['git', 'push',
            '--force-with-lease=refs/heads/feat/example:' + 'a' * 40, 'origin', ':refs/heads/feat/example'])
