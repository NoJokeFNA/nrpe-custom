import unittest
from unittest.mock import patch

from scripts.check_git_policy import (DEPENDABOT_AUTHOR, check_author, check_route,
                                     dependabot_permissions)


class GitPolicyTests(unittest.TestCase):
    def proposal(self):
        return {'pull_request': {
            'user': {'login': 'dependabot[bot]', 'id': 49699333, 'type': 'Bot'},
            'base': {'ref': 'develop', 'sha': 'a' * 40, 'repo': {'full_name': 'owner/repo'}},
            'head': {'ref': 'dependabot/pip/develop/group', 'sha': 'b' * 40,
                     'repo': {'full_name': 'owner/repo'}}}}

    def permissions(self, event):
        return dependabot_permissions('develop', 'dependabot/pip/develop/group',
                                      'a' * 40, 'b' * 40, event, 'owner/repo')

    def test_only_github_identified_same_repository_dependabot_proposals_get_exception(self):
        self.assertEqual(self.permissions(self.proposal()), (True, True))
        for field, value in [('user.login', 'someone'), ('user.id', 123), ('user.type', 'User'),
                             ('head.repo.full_name', 'fork/repo'), ('base.ref', 'master'),
                             ('head.sha', 'c' * 40), ('head.ref', 'fix/example')]:
            event = self.proposal()
            current = event['pull_request']
            *parents, key = field.split('.')
            for parent in parents:
                current = current[parent]
            current[key] = value
            with self.subTest(field=field):
                self.assertEqual(self.permissions(event), (False, False))
        self.assertEqual(self.permissions({}), (False, False))

    def test_bot_commits_can_be_promoted_after_integration_without_allowing_new_bot_routes(self):
        event = self.proposal()
        event['pull_request']['base']['ref'] = 'master'
        event['pull_request']['head']['ref'] = 'develop'
        self.assertEqual(dependabot_permissions('master', 'develop', 'a' * 40, 'b' * 40,
                                               event, 'owner/repo'), (False, True))

    def test_dependabot_route_and_exact_identity_are_narrow_exceptions(self):
        with self.assertRaises(ValueError):
            check_route('develop', 'dependabot/pip/develop/group')
        check_route('develop', 'dependabot/pip/develop/group', allow_dependabot=True)
        with self.assertRaises(ValueError):
            check_route('master', 'dependabot/pip/develop/group', allow_dependabot=True)
        check_author(*DEPENDABOT_AUTHOR, 'build(deps): update reviewed dependencies', allow_dependabot=True)
        for name, email, message in [
                ('dependabot[bot]', 'spoof@example.test', 'fix: update'),
                ('github-actions[bot]', 'actions@example.test', 'fix: update'),
                ('Codex', 'codex@example.test', 'fix: update'),
                (*DEPENDABOT_AUTHOR, 'fix: update\n\nCo-authored-by: AI <ai@example.test>')]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                check_author(name, email, message, allow_dependabot=True)

    def test_only_topic_integration_and_develop_promotion_routes_are_allowed(self):
        with patch('scripts.check_git_policy.subprocess.run'):
            for prefix in ('feat', 'fix', 'refactor', 'remove'):
                check_route('develop', prefix + '/example')
        check_route('master', 'develop')
        for base, head in [('master', 'feat/example'), ('develop', 'master'),
                           ('develop', 'develop'), ('other', 'fix/example')]:
            with self.subTest(base=base, head=head), self.assertRaises(ValueError):
                check_route(base, head)

    def test_human_identity_and_attribution_rules(self):
        check_author('Example Maintainer', 'maintainer@example.test', 'fix: preserve TLS checks')
        for name, email, message in [
                ('dependabot[bot]', 'bot@example.test', 'fix: update'),
                ('Codex', 'codex@example.test', 'fix: update'),
                ('Human', 'person@example.test', 'fix: update\n\nCo-authored-by: AI <ai@example.test>'),
                ('Human', 'person@example.test', 'fix: update\n\nGenerated with a tool'),
                ('', 'person@example.test', 'fix: update')]:
            with self.subTest(name=name, message=message), self.assertRaises(ValueError):
                check_author(name, email, message)
