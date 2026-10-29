"""Highlighted code remains literal, copyable text with scoped static colors."""
from html import escape
from html.parser import HTMLParser
import re
import unittest
from unittest.mock import patch

from website.highlighting import colorize, stylesheet, tokenize


class CodeText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.inside = False
        self.parts = []
        self.scripts = []

    def handle_starttag(self, tag, attributes):
        if tag == 'code':
            self.inside = True
        if tag == 'script':
            self.scripts.append(attributes)

    def handle_endtag(self, tag):
        if tag == 'code':
            self.inside = False

    def handle_data(self, text):
        if self.inside:
            self.parts.append(text)


class HighlightingTests(unittest.TestCase):
    @patch('website.highlighting.shutil.which', return_value=None)
    def test_missing_node_is_actionable_instead_of_silently_unstyled(self, node):
        with self.assertRaisesRegex(RuntimeError, 'Node.js 24.*npm ci'):
            tokenize((('bash', 'unique missing-node setup check'),))

    def test_languages_preserve_code_characters_and_whitespace(self):
        cases = {
            'sh': '# Comment\n\tprintf "%s\\n" "$HOME & <tag>"\n',
            'powershell': '$ca = "C:\\Company CA Ω\\root.cer"\nWrite-Host $ca',
            'ini': '[service]\nkey="value"\n',
            'nrpe': "# Example only\nserver_port=5666\ncommand[check_example]=@pluginsdir@/check_example -w '$ARG1$'\ninclude=@sysconfdir@/nrpe_local.cfg\n",
            'yaml': 'services:\n  nrpe:\n    enabled: true\n',
            'json': '{"enabled": true, "port": 5666}',
            'python': 'if ready:\n\tprint("café")\n',
            'diff': '--- before\n+++ after\n-old\n+new\n',
        }
        for language, source in cases.items():
            with self.subTest(language=language):
                output = colorize(f'<pre><code class="language-{language}">{escape(source)}</code></pre>')
                parsed = CodeText()
                parsed.feed(output)
                self.assertEqual(''.join(parsed.parts), source)
                self.assertIn('syntax-', output)
                self.assertIn(f'language-{language}', output)

    def test_mermaid_unknown_and_plain_text_are_unchanged(self):
        for language in ('mermaid', 'text', 'plaintext', 'not-a-real-language'):
            block = f'<pre><code class="language-{language}">A &lt; B\n</code></pre>'
            self.assertEqual(colorize(block), block)
        raw = '<pre><code>unlabelled &amp; output\n</code></pre>'
        self.assertEqual(colorize(raw), raw)

    def test_script_and_entities_stay_literal_code(self):
        source = 'print("<script>alert(1)</script> &lt; &amp;")\n'
        output = colorize('<pre><code class="language-python">' + escape(source) + '</code></pre>')
        parsed = CodeText()
        parsed.feed(output)
        self.assertEqual(parsed.scripts, [])
        self.assertEqual(''.join(parsed.parts), source)

    def test_token_css_does_not_restyle_other_page_elements(self):
        rules = stylesheet().splitlines()
        self.assertTrue(rules)
        self.assertTrue(rules[0].startswith('.prose pre.syntax-block {'))
        self.assertTrue(all(rule.startswith('.prose pre code .syntax-') for rule in rules[1:]))
        self.assertNotIn('style=', colorize('<pre><code class="language-python">True\n</code></pre>'))

    def test_shell_commands_options_and_nrpe_keys_have_distinct_theme_colors(self):
        requests = (('bash', 'python3 nrpe.py --ca-cert "root.pem"'),
                    ('nrpe', "command[check_example]=@pluginsdir@/check_example -w '$ARG1$'"))
        response = tokenize(requests)
        shell = {token['content']: token['color'] for line in response['blocks'][0] for token in line}
        self.assertNotEqual(shell['python3'], shell['--ca-cert'])
        self.assertNotEqual(shell['python3'], shell['"root.pem"'])
        nrpe = {token['content']: token['color'] for line in response['blocks'][1] for token in line}
        self.assertNotEqual(nrpe['command'], nrpe['check_example'])
        self.assertIn('@pluginsdir@', nrpe)
        self.assertIn('$ARG1$', nrpe)

    def test_nrpe_hash_values_and_metacharacters_are_not_inline_comments(self):
        source = "nasty_metachars=|;&><'\\[]{};#\n# Full-line comment\n"
        result = tokenize((('nrpe', source),))['blocks'][0]
        self.assertTrue(any('#' in token['content'] and token['color'].lower() != '#8b949e'
                            for token in result[0]))
        self.assertEqual(result[1][0]['color'].lower(), '#8b949e')

    def test_representative_token_pairs_have_readable_contrast(self):
        def luminance(color):
            rgb = [int(color[index:index+2],16)/255 for index in (1,3,5)]
            linear = [value/12.92 if value<=0.04045 else ((value+0.055)/1.055)**2.4 for value in rgb]
            return sum(value*weight for value,weight in zip(linear,(0.2126,0.7152,0.0722)))
        response = tokenize((('bash', '# Build\npython3 nrpe.py --ca-cert "root.pem"\n'),
                             ('nrpe', '# Config\ncommand[example]=@pluginsdir@/check_example -w $ARG1$\n')))
        for block in response['blocks']:
            for line in block:
                for token in line:
                    background = luminance(token.get('bgColor') or response['bg'])
                    foreground = luminance(token['color'])
                    self.assertGreaterEqual((max(background,foreground)+0.05)/(min(background,foreground)+0.05),4.5)
