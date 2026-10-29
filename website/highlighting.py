"""Shiki tokens become static, CSP-compatible code HTML and scoped CSS."""

from functools import lru_cache
import html
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
BLOCK = re.compile(r'<pre><code class="language-([A-Za-z0-9_+.-]+)">(.*?)</code></pre>', re.S)
LANGUAGES = {
    'sh': 'bash', 'bash': 'bash', 'shell': 'bash', 'shellscript': 'bash',
    'powershell': 'powershell', 'ps1': 'powershell', 'ini': 'ini',
    'nrpe': 'nrpe', 'nrpe.cfg': 'nrpe', 'python': 'python', 'py': 'python',
    'yaml': 'yaml', 'yml': 'yaml', 'json': 'json', 'dockerfile': 'dockerfile', 'diff': 'diff',
}
LABELS = {'sh': 'Shell', 'bash': 'Shell', 'powershell': 'PowerShell', 'ini': 'INI',
          'nrpe': 'NRPE config', 'python': 'Python', 'yaml': 'YAML', 'json': 'JSON',
          'dockerfile': 'Dockerfile', 'diff': 'Diff'}


def color(value):
    if not isinstance(value, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', value):
        raise RuntimeError('Shiki returned an unsupported theme color')
    return value.lower()


@lru_cache(maxsize=256)
def tokenize(requests):
    node = shutil.which('node')
    if not node:
        raise RuntimeError('Website syntax highlighting needs Node.js 24 and npm ci --prefix website --ignore-scripts')
    try:
        result = subprocess.run([node, str(ROOT / 'shiki.mjs')],
                                input=json.dumps(requests, ensure_ascii=False),
                                capture_output=True, text=True, encoding='utf-8',
                                cwd=ROOT, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError('Shiki did not complete; check the Node.js 24 website build setup') from exc
    if result.returncode:
        raise RuntimeError('Shiki failed. Use Node.js 24 and install pinned dependencies with '
                           'npm ci --prefix website --ignore-scripts.\n' + result.stderr[-2000:])
    response = json.loads(result.stdout)
    if len(response['blocks']) != len(requests):
        raise RuntimeError('Shiki returned an unexpected number of code blocks')
    return response


def colorize(content):
    matches = list(BLOCK.finditer(content))
    requests = tuple((LANGUAGES[match[1].lower()], html.unescape(match[2]))
                     for match in matches if match[1].lower() in LANGUAGES)
    if not requests:
        return content
    blocks = iter(tokenize(requests)['blocks'])

    def block(match):
        language = LANGUAGES.get(match[1].lower())
        if language is None:
            return match[0]
        lines, actual = [], []
        for line in next(blocks):
            rendered, text = [], []
            for token in line:
                token_text = token['content']
                text.append(token_text)
                classes = ['syntax-fg-' + color(token['color'])[1:]]
                if token.get('bgColor'):
                    classes.append('syntax-bg-' + color(token['bgColor'])[1:])
                for mask, name in ((1, 'italic'), (2, 'bold'), (4, 'underline')):
                    if token.get('fontStyle', 0) & mask:
                        classes.append('syntax-' + name)
                rendered.append('<span class="' + ' '.join(classes) + '">' + html.escape(token_text) + '</span>')
            lines.append(''.join(rendered))
            actual.append(''.join(text))
        if '\n'.join(actual) != html.unescape(match[2]):
            raise RuntimeError('Shiki changed code text; refusing to publish changed commands')
        label = LABELS.get(match[1].lower(), LABELS.get(language, language))
        return (f'<pre class="syntax-block" data-language="{html.escape(label)}">'
                f'<code class="language-{match[1]}">' + '\n'.join(lines) + '</code></pre>')
    return BLOCK.sub(block, content)


def stylesheet():
    theme = tokenize(())
    lines = [f'.prose pre.syntax-block {{ background: {color(theme["bg"])}; color: {color(theme["fg"])}; }}']
    for value in sorted({color(value) for value in theme['palette']}):
        lines.append(f'.prose pre code .syntax-fg-{value[1:]} {{ color: {value}; }}')
        lines.append(f'.prose pre code .syntax-bg-{value[1:]} {{ background-color: {value}; }}')
    lines += ['.prose pre code .syntax-italic { font-style: italic; }',
              '.prose pre code .syntax-bold { font-weight: bold; }',
              '.prose pre code .syntax-underline { text-decoration: underline; }']
    return '\n'.join(lines) + '\n'
