"""Build-time syntax colors, preserving code text and language classes."""

import html
import re

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.style import Style
from pygments.token import Comment, Error, Generic, Keyword, Literal, Name, Number, Operator, String, Token
from pygments.util import ClassNotFound


class DocumentationStyle(Style):
    background_color = '#122b32'
    styles = {
        Token: '#e1ece1', Comment: '#a5b9b2', Keyword: '#c4afff',
        Name: '#add3ef', Name.Builtin: '#88d5e8', Name.Function: '#91d9ca',
        Name.Attribute: '#9de3b8', Name.Tag: '#9de3b8',
        Literal: '#e9cb8e', String: '#e9cb8e', Number: '#f4b79c',
        Operator: '#88d5e8', Error: '#ffb5b5',
        Generic.Deleted: '#ffb5b5', Generic.Inserted: '#9de3b8',
        Generic.Heading: 'bold #add3ef', Generic.Subheading: 'bold #add3ef',
    }


FORMATTER = HtmlFormatter(nowrap=True, classprefix='syntax-', style=DocumentationStyle)
BLOCK = re.compile(r'<pre><code class="language-([A-Za-z0-9_+.-]+)">(.*?)</code></pre>', re.S)
LABELS = {'sh': 'Shell', 'bash': 'Bash', 'powershell': 'PowerShell', 'ps1': 'PowerShell',
          'ini': 'INI / config', 'python': 'Python', 'yaml': 'YAML', 'json': 'JSON',
          'dockerfile': 'Dockerfile', 'diff': 'Diff'}


def colorize(content):
    def block(match):
        language, escaped = match.groups()
        if language.lower() in ('text', 'plaintext', 'mermaid'):
            return match[0]
        try:
            lexer = get_lexer_by_name(language, stripnl=False, ensurenl=False, tabsize=0)
        except ClassNotFound:
            return match[0]
        source = html.unescape(escaped)
        # HTML formatting terminates the final line; omit only that added LF.
        colored = highlight(source, lexer, FORMATTER)
        if not source.endswith('\n') and colored.endswith('\n'):
            colored = colored[:-1]
        label = html.escape(LABELS.get(language.lower(), language), quote=True)
        return (f'<pre class="syntax-block" data-language="{label}">'
                f'<code class="language-{language}">{colored}</code></pre>')
    return BLOCK.sub(block, content)


def stylesheet():
    # Omit formatter-wide pre/line-number rules; colors belong only to code tokens.
    return '\n'.join(FORMATTER.get_token_style_defs('.prose pre code')) + '\n'
