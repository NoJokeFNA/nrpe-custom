import unittest
from unittest.mock import patch

from scripts.check_git_policy import check_author, check_route


class GitPolicyTests(unittest.TestCase):
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
