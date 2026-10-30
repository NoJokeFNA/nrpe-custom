"""Mermaid is rendered at build time, not silently left as a code block."""
import unittest
from unittest.mock import patch
from website.diagrams import render_diagrams, validate_svg


class DiagramTests(unittest.TestCase):
    def test_diagram_becomes_an_image_with_accessible_source_and_stable_asset(self):
        data=b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 40"><text>Example</text></svg>'
        with patch('website.diagrams.svg',return_value=data):
            assets={}
            html=render_diagrams('<h2>Connection map</h2><pre><code class="language-mermaid">flowchart LR\nA--&gt;B\n</code></pre>','/nrpe-custom',assets,'Network')
        self.assertEqual(len(assets),1)
        self.assertIn('alt="Connection map diagram"',html)
        self.assertIn('<img ',html)
        self.assertIn('width="100" height="40"',html)
        self.assertIn('Open full size',html)
        self.assertIn('View diagram source',html)
        self.assertIn('A--&gt;B',html)
        self.assertIn('tabindex="0"',html)

    def test_diagram_dimensions_must_be_finite_and_positive(self):
        for viewbox in ('', '0 0 0 40', '0 0 100 NaN', '0 0 -10 40'):
            data = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="' + viewbox + '"/>').encode()
            with self.subTest(viewbox=viewbox), patch('website.diagrams.svg', return_value=data):
                with self.assertRaisesRegex(ValueError, 'viewBox dimensions'):
                    render_diagrams('<pre><code class="language-mermaid">flowchart TD</code></pre>',
                                    '/nrpe-custom', {}, 'Example')

    def test_active_and_external_svg_content_is_rejected(self):
        for body in ('<script>alert(1)</script>','<foreignObject/>','<image href="https://example.com/a.png"/>',
                     '<a href="javascript:alert(1)"/>','<text onclick="alert(1)"/>',
                     '<style>@import "https://example.com/a.css";</style>',
                     '<path style="fill:url(https://example.com/fill.svg)"/>'):
            with self.subTest(body=body),self.assertRaises(ValueError):
                validate_svg(('<svg xmlns="http://www.w3.org/2000/svg">'+body+'</svg>').encode())

    def test_internal_marker_references_are_allowed(self):
        data=b'<svg xmlns="http://www.w3.org/2000/svg"><style>.line{marker-end:url(\"#arrow\")}</style><path marker-end="url(#arrow)"/></svg>'
        self.assertEqual(validate_svg(data),data)
