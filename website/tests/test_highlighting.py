"""Highlighted code remains literal, copyable text with scoped static colors."""
from html import escape
from html.parser import HTMLParser
import re
import unittest

from website.highlighting import DocumentationStyle, colorize, stylesheet


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
    def test_languages_preserve_code_characters_and_whitespace(self):
        cases = {
            'sh': '# Comment\n\tprintf "%s\\n" "$HOME & <tag>"\n',
            'powershell': '$ca = "C:\\Company CA Ω\\root.cer"\nWrite-Host $ca',
            'ini': '[service]\nkey="value"\n',
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
        self.assertTrue(all(rule.startswith('.prose pre code .syntax-') for rule in rules))
        self.assertNotIn('style=', colorize('<pre><code class="language-python">True\n</code></pre>'))

    def test_all_token_colors_have_readable_contrast_on_code_background(self):
        def luminance(color):
            rgb = [int(color[index:index+2],16)/255 for index in (1,3,5)]
            linear = [value/12.92 if value<=0.04045 else ((value+0.055)/1.055)**2.4 for value in rgb]
            return sum(value*weight for value,weight in zip(linear,(0.2126,0.7152,0.0722)))
        background = luminance(DocumentationStyle.background_color)
        for color in set(re.findall(r'#[0-9a-fA-F]{6}', stylesheet())):
            light = luminance(color)
            self.assertGreaterEqual((max(background,light)+0.05)/(min(background,light)+0.05),4.5,color)
