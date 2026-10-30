"""Render Mermaid once at build time; visitors receive ordinary SVG images."""

from functools import lru_cache
import hashlib
import html
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
BLOCK = re.compile(r'<pre><code class="language-mermaid">(.*?)</code></pre>', re.S)


def validate_svg(data):
    if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
        raise ValueError('Diagram SVG must not contain document types or entities')
    document = ET.fromstring(data)
    if document.tag != '{http://www.w3.org/2000/svg}svg':
        raise ValueError('Diagram renderer did not return SVG')
    for item in document.iter():
        tag = item.tag.rsplit('}', 1)[-1].lower()
        if tag in ('script', 'foreignobject', 'iframe', 'image'):
            raise ValueError('Diagram SVG contains unsupported active or external content')
        for key, value in item.attrib.items():
            key = key.rsplit('}', 1)[-1].lower()
            if key.startswith('on') or (key == 'href' and not value.startswith('#')):
                raise ValueError('Diagram SVG contains an event handler or external link')
            if any(not ref.strip(' \t\r\n\'"').startswith('#')
                   for ref in re.findall(r'url\((.*?)\)', value, re.I)):
                raise ValueError('Diagram SVG contains an external style resource')
        if tag == 'style':
            text = item.text or ''
            if '@import' in text.lower() or any(not ref.strip(' \t\r\n\'"').startswith('#')
                    for ref in re.findall(r'url\((.*?)\)', text, re.I)):
                raise ValueError('Diagram SVG contains an external stylesheet resource')
    return data


@lru_cache(maxsize=32)
def svg(source):
    if '%%{' in source:
        raise ValueError('Configure Mermaid in the website builder, not diagram init directives')
    node = shutil.which('node')
    browser = os.environ.get('NRPE_WEBSITE_BROWSER') or next(
        (path for name in ('chromium', 'google-chrome', 'chromium-browser')
         if (path := shutil.which(name))), None)
    if not node or not browser:
        raise RuntimeError('Mermaid builds need Node.js 24 and Chrome/Chromium. '
                           'Set NRPE_WEBSITE_BROWSER to a local browser executable if needed.')
    settings = {'securityLevel':'strict', 'theme':'base', 'htmlLabels':False,
                'themeCSS':'.edgeLabel rect { opacity: 1 !important; fill: #ffffff !important; } '
                           '.labelBkg { background-color: #ffffff !important; }',
                'deterministicIds':True, 'deterministicIDSeed':hashlib.sha256(source.encode()).hexdigest(),
                'flowchart':{'htmlLabels':False},
                'themeVariables':{'fontFamily':'Arial, sans-serif','fontSize':'15px',
                                 'primaryColor':'#e8f1e9','primaryTextColor':'#162b35',
                                 'primaryBorderColor':'#086d5d','lineColor':'#48675b',
                                 'secondaryColor':'#f0e8db','tertiaryColor':'#ffffff',
                                 'edgeLabelBackground':'#ffffff'}}
    command = [node, str(ROOT / 'mermaid.mjs')]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                            input=json.dumps({'source':source,'config':settings,'browser':browser}),
                            encoding='utf-8', timeout=60, check=False)
    if result.returncode:
        raise RuntimeError('Mermaid rendering failed; check the diagram syntax and local '
                           'Chrome/Chromium setup.\n' + result.stderr[-2000:])
    return validate_svg(result.stdout.encode('utf-8'))


def render_diagrams(content, base, assets, title):
    def replace(match):
        source = html.unescape(match[1])
        data = svg(source)
        try:
            viewbox = [float(value) for value in ET.fromstring(data).get('viewBox', '').split()]
            if len(viewbox) != 4 or not all(math.isfinite(value) for value in viewbox) or min(viewbox[2:]) <= 0:
                raise ValueError('Invalid diagram viewBox')
            width, height = (math.ceil(value) for value in viewbox[2:])
        except (ValueError, OverflowError) as exc:
            raise ValueError('Diagram must provide finite positive viewBox dimensions') from exc
        filename = 'diagram-' + hashlib.sha256(data).hexdigest()[:20] + '.svg'
        assets[filename] = data
        headings = re.findall(r'<h[23][^>]*>(.*?)</h[23]>', content[:match.start()], re.S)
        label = html.unescape(re.sub('<[^>]+>', '', headings[-1])) if headings else title
        url = base + '/assets/' + filename
        return ('<figure class="diagram"><div class="diagram-viewport" tabindex="0" role="region" '
                'aria-label="' + html.escape(label, quote=True) + '"><a href="' + url + '">'
                '<img src="' + url + '" width="' + str(width) + '" height="' + str(height)
                + '" alt="' + html.escape(label + ' diagram', quote=True) + '"></a></div>'
                '<figcaption>' + html.escape(label) + ' · <a href="' + url + '">Open full size</a></figcaption>'
                '<details class="diagram-source"><summary>View diagram source</summary>'
                + match[0] + '</details></figure>')
    return BLOCK.sub(replace, content)
