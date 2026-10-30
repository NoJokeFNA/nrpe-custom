"""FAQ navigation preserves shared links and keeps canonical answers available."""

from pathlib import Path
import sys
import unittest

import markdown

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from website.faq import render_faq


class FaqTests(unittest.TestCase):
    def setUp(self):
        source = (ROOT / 'docs/faq.md').read_text()
        self.content = render_faq(markdown.markdown(source, extensions=['toc', 'fenced_code']))

    def test_existing_question_and_diagnostic_links_remain_available(self):
        anchors = ('which-sles-version-does-this-project-target',
                   'nrpe-checks-on-sles-services-first-then-ssltls',
                   'does-a-separate-nrpe-agent-also-need-nagios-core-locally',
                   'when-do-i-actually-need-a-custom-build',
                   'which-services-must-run-on-a-combined-nagios-and-nrpe-server',
                   'why-does-the-old-sles-12-nrpe-daemon-fail-its-ssl-handshake')
        for anchor in anchors:
            with self.subTest(anchor=anchor):
                self.assertEqual(self.content.count('id="' + anchor + '"'), 1)
        self.assertEqual(self.content.count('class="question-link"'), 4)

    def test_answers_and_commands_are_present_without_expand_controls_or_javascript(self):
        self.assertNotIn('<details', self.content)
        self.assertEqual(self.content.count('class="faq-group"'), 3)
        self.assertIn('sudo systemctl enable --now nrpe.service', self.content)
        self.assertIn('TLS 1.3 requires a newer TLS library', self.content)
        self.assertEqual(self.content.count('Starting Nagios alone does not start'), 1)
        self.assertIn('class="faq-tools" hidden', self.content)
        self.assertIn('aria-label="Questions by topic"', self.content)


if __name__ == '__main__':
    unittest.main()
