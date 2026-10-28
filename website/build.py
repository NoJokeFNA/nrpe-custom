#!/usr/bin/env python3
"""Build a static GitHub Pages site from the project's reviewed Markdown."""

import argparse
import hashlib
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from string import Template
import tempfile
from urllib.parse import quote, unquote, urlsplit

import markdown
from markdown.treeprocessors import Treeprocessor
from markdown.extensions import Extension

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = 'NoJokeFNA/nrpe-custom'
BASE = '/nrpe-custom'
GROUPS = (
    ('Start here', ('overview', 'installation', 'workflow', 'faq')),
    ('Build and diagnose', ('sles12sp3', 'network', 'menu', 'local-cleanup', 'troubleshooting')),
    ('Deploy carefully', ('configuration-examples', 'updates-and-rollback', 'security', 'practical-validation')),
    ('Project reference', ('architecture', 'maintenance', 'releases', 'release-history',
                           'release-signing', 'release-plan', 'sles-license-review',
                           'third-party', 'contributing', 'license')),
)
LABELS = {'overview': 'Overview', 'installation': 'Install a package', 'workflow': 'Build & verify',
          'faq': 'Frequently asked questions', 'sles12sp3': 'SLES 12 SP3', 'network': 'Network & company CA',
          'menu': 'Terminal menu', 'local-cleanup': 'Local cleanup', 'troubleshooting': 'Troubleshooting',
          'configuration-examples': 'Configuration examples', 'updates-and-rollback': 'Update & rollback',
          'security': 'Security', 'practical-validation': 'Validation limits', 'architecture': 'Architecture',
          'maintenance': 'Maintenance', 'releases': 'Release workflow', 'release-history': 'Release history',
          'release-signing': 'Release signatures', 'release-plan': 'Open work',
          'sles-license-review': 'SLES license review', 'third-party': 'Third-party notices',
          'contributing': 'Contributing', 'license': 'Project license'}


def identity(root):
    try:
        sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True, stderr=subprocess.DEVNULL, timeout=10).strip()
        dirty = bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=root, text=True, stderr=subprocess.DEVNULL, timeout=10))
        return sha, dirty
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None, True


def sources(root):
    pages = {Path('README.md'): 'overview', Path('CONTRIBUTING.md'): 'contributing',
             Path('THIRD_PARTY.md'): 'third-party', Path('LICENSE'): 'license'}
    for path in sorted((root / 'docs').rglob('*.md')):
        pages[path.relative_to(root)] = path.relative_to(root / 'docs').with_suffix('').as_posix()
    pages[Path('packaging/licenses/sles12sp3/README.md')] = 'license-notices'
    for path in sorted((root / 'website/content').glob('*.md')):
        pages[path.relative_to(root)] = 'field-notes/' + path.stem
    return pages


def page_url(slug, base):
    return base + ('/' if not slug else '/' + quote(slug.strip('/'), safe='/') + '/')


class Links(Treeprocessor):
    def run(self, document):
        for element in document.iter():
            attr = 'href' if element.tag == 'a' else 'src' if element.tag == 'img' else None
            if attr and element.get(attr):
                element.set(attr, self.md.site_link(element.get(attr)))


class SiteLinks(Extension):
    def extendMarkdown(self, md):
        md.treeprocessors.register(Links(md), 'site-links', 1)


def render(root, source, pages, base, commit):
    text = (root / source).read_text(encoding='utf-8')
    title_match = re.search(r'^# (.+)$', text, re.M)
    title = title_match[1] if title_match else 'Project MIT license'
    if title_match:
        text = text[:title_match.start()] + text[title_match.end():]
    if source.name == 'LICENSE':
        text = '```text\n' + text + '\n```\n'
    def rewrite(value):
        parsed = urlsplit(value)
        if parsed.scheme or parsed.netloc or not parsed.path:
            return value
        target = Path(os.path.normpath(str(source.parent / unquote(parsed.path))))
        if target.is_absolute() or '..' in target.parts:
            raise ValueError('Link escapes the source tree: ' + value)
        suffix = ('?' + parsed.query if parsed.query else '') + ('#' + parsed.fragment if parsed.fragment else '')
        if target in pages:
            return page_url(pages[target], base) + suffix
        if target.parts[:2] == ('website', 'assets'):
            return base + '/assets/' + quote(target.relative_to('website/assets').as_posix(), safe='/') + suffix
        if target.parent == Path('packaging/licenses/sles12sp3') and target.suffix in ('.md', '.txt'):
            return base + '/notices/' + quote(target.name) + suffix
        # Build recipes and other repository-only references remain source links.
        mode = 'tree' if (root / target).is_dir() else 'blob'
        return 'https://github.com/' + REPOSITORY + '/' + mode + '/' + (commit or 'develop') + '/' + quote(target.as_posix(), safe='/') + suffix
    converter = markdown.Markdown(extensions=['tables', 'fenced_code', 'toc', 'md_in_html', SiteLinks()],
                                  extension_configs={'toc': {'toc_depth': '2-3'}}, output_format='html')
    converter.site_link = rewrite
    content = converter.convert(text)
    if pages[source] == 'faq':
        sections = re.split(r'<h2 id="([^"]+)">(.*?)</h2>', content)
        content = sections[0] + '<div class="faq-tools"><label for="faq-filter">Find an answer</label><input id="faq-filter" type="search" placeholder="Try TLS, SLES or services…"><p id="faq-count" aria-live="polite"></p></div>'
        for offset in range(1, len(sections), 3):
            content += ('<details class="faq-item" id="' + sections[offset] + '"><summary><h2>'
                        + sections[offset + 1] + '</h2></summary><div class="faq-answer">'
                        + sections[offset + 2] + '</div></details>')
    return title, content, converter.toc


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
    def handle_data(self, data):
        self.parts.append(data)


def plain(content):
    parser = Text()
    parser.feed(content)
    return ' '.join(' '.join(parser.parts).split())


def sidebar(pages, current, base):
    available = set(pages.values())
    chunks = []
    for label, slugs in GROUPS:
        expanded = label != 'Project reference' or current in slugs
        links = ''.join('<a ' + ('aria-current="page" ' if slug == current else '')
                        + 'href="' + page_url(slug, base) + '">' + html.escape(LABELS.get(slug, slug)) + '</a>'
                        for slug in slugs if slug in available)
        chunks.append('<details class="nav-group"' + (' open' if expanded else '')
                      + '><summary>' + label + '</summary>' + links + '</details>')
    return ''.join(chunks)


def template(name, **values):
    return Template((ROOT / 'website/templates' / name).read_text(encoding='utf-8')).substitute(values)


def layout(title, content, pages, slug, base, toc='', source=None, commit=None, dirty=True, home=False):
    esc = html.escape
    active = 'Field notes' if slug.startswith('field-notes') else 'FAQ' if slug == 'faq' else 'Documentation'
    nav = ''.join('<a ' + ('aria-current="page" ' if active == name and not home else '')
                  + 'href="' + page_url(path, base) + '">' + name + '</a>'
                  for name, path in (('Documentation', 'overview'), ('FAQ', 'faq'), ('Field notes', 'field-notes')))
    meta = ('Working copy' if dirty else 'Source ' + commit[:7]) if commit else 'Local preview'
    source_link = ''
    if source:
        source_link = ('<a class="source-link" href="https://github.com/' + REPOSITORY + '/blob/'
                       + (commit or 'develop') + '/' + quote(source.as_posix(), safe='/')
                       + '">View this page on GitHub ↗︎</a>')
    body = content if home else template('document.html', overview_url=page_url('overview', base),
             sidebar=sidebar(pages, slug, base), section=active, title=esc(title), content=content,
             source_link=source_link, toc=toc)
    toggle = '' if home else '<button class="docs-toggle" aria-controls="doc-nav" aria-expanded="false">Browse documentation <span>＋</span></button>'
    return template('layout.html', title=esc(title), body=body, nav=nav, meta=esc(meta), base=base, docs_toggle=toggle)


def homepage(base, root=ROOT):
    # Keep the supported-target data in the README, rather than a second table.
    readme = (root / 'README.md').read_text(encoding='utf-8')
    target_section = readme.split('## Supported targets\n', 1)[1].split('\n## ', 1)[0]
    rows = [line for line in target_section.splitlines() if line.startswith('|')]
    compact = ['| ' + ' | '.join(line.split('|')[1:4]) + ' |' for line in rows]
    supported_targets = markdown.markdown('\n'.join(compact), extensions=['tables'])
    return template('home.html', supported_targets=supported_targets, base=base,
                    **{key + '_url': page_url(slug, base) for key, slug in (
        ('overview', 'overview'), ('installation', 'installation'), ('faq', 'faq'),
        ('workflow', 'workflow'), ('menu', 'menu'), ('releases', 'releases'),
        ('contributing', 'contributing'), ('note_guide', 'field-notes/contributing-a-note'),
        ('troubleshooting', 'troubleshooting'), ('field_note', 'field-notes/sles12-handshake'),
        ('validation', 'practical-validation'))})


def build(output, root=ROOT, base=BASE):
    if not re.fullmatch(r'(?:/[A-Za-z0-9_.-]+)*', base.rstrip('/')):
        raise ValueError('Base path must be an absolute URL path without query or fragment')
    base = base.rstrip('/')
    if output.is_symlink() or (output.exists() and getattr(output.lstat(), 'st_file_attributes', 0) & 0x400):
        raise ValueError('Output must not be a symlink or reparse point')
    output = output.resolve()
    if output == root.resolve() or (root.resolve() in output.parents and
            (output.relative_to(root.resolve()).parts[:2] != ('.nrpe', 'site')
             or len(output.relative_to(root.resolve()).parts) < 3)):
        raise ValueError('Use a dedicated output under .nrpe/site/<name> or outside the source checkout')
    if output.exists() and any(output.iterdir()):
        marker = output / 'site-manifest.json'
        if not marker.is_file() or json.loads(marker.read_text()).get('generator') != 'nrpe-custom-pages':
            raise ValueError('Refusing to replace a directory not owned by this site builder')
        owned = set(json.loads(marker.read_text())['files']) | {'site-manifest.json'}
        for path in output.rglob('*'):
            info = path.lstat()
            if path.is_symlink() or getattr(info, 'st_file_attributes', 0) & 0x400:
                raise ValueError('Refusing linked files in existing output')
            if path.is_file() and path.relative_to(output).as_posix() not in owned:
                raise ValueError('Refusing to remove unknown files in existing output')
    pages = sources(root)
    commit, dirty = identity(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='nrpe-site-', dir=output.parent) as temporary:
        stage = Path(temporary) / 'site'
        stage.mkdir()
        shutil.copytree(root / 'website/assets', stage / 'assets')
        search, stories = [], []
        def write(slug, data):
            path = stage / slug / 'index.html'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(data, encoding='utf-8')
        for source, slug in pages.items():
            title, content, toc = render(root, source, pages, base, commit)
            write(slug, layout(title, content, pages, slug, base, toc, source, commit, dirty))
            search.append({'title': title, 'url': page_url(slug, base), 'text': plain(content),
                           'section': 'Field notes' if slug.startswith('field-notes/') else 'Documentation'})
            if slug.startswith('field-notes/') and not slug.endswith('/contributing-a-note'):
                paragraphs = re.findall(r'<p>(.*?)</p>', content, re.S)
                stories.append((slug, title, plain(paragraphs[0]) if paragraphs else 'Field note',
                                plain(paragraphs[1])[:180] if len(paragraphs) > 1 else 'A reviewed report from actual troubleshooting.'))
        cards = ''.join('<a class="story-card" href="' + page_url(slug, base) + '"><span class="eyebrow">'
                        + html.escape(label) + '</span><h2>' + html.escape(title) + ' <span>↗︎</span></h2><p>'
                        + html.escape(summary) + '</p><span class="tag">Reported observation</span></a>'
                        for slug, title, label, summary in stories)
        notes = ('<p class="lead">Practical reports from actual troubleshooting. Observations are kept separate from assumptions and untested outcomes.</p>'
                 + cards + '<p>Have a useful experience to share? See <a href="'
                 + page_url('field-notes/contributing-a-note', base)
                 + '">how to contribute a field note</a>. We do not publish unverified testimonials or production credentials.</p>')
        write('field-notes', layout('Notes from the field', notes, pages, 'field-notes', base, commit=commit, dirty=dirty))
        write('', layout('Custom NRPE builds. Clear, practical docs.', homepage(base, root), pages, '', base, commit=commit, dirty=dirty, home=True))
        (stage / '404.html').write_text(layout('That page is not here', '<p>The address may have changed. <a href="' + page_url('overview', base) + '">Browse the documentation</a> or use search to find the next step.</p>', pages, '404', base, commit=commit, dirty=dirty), encoding='utf-8')
        (stage / 'assets/search-index.json').write_text(json.dumps(search, ensure_ascii=False), encoding='utf-8')
        notices = stage / 'notices'
        notices.mkdir()
        for path in (root / 'packaging/licenses/sles12sp3').iterdir():
            if path.is_file() and path.suffix in ('.md', '.txt'):
                shutil.copyfile(path, notices / path.name)
        (stage / '.nojekyll').touch()
        files = {p.relative_to(stage).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in sorted(stage.rglob('*')) if p.is_file()}
        manifest = {'generator': 'nrpe-custom-pages', 'schema': 1, 'repository': REPOSITORY,
                    'source_commit': commit, 'dirty': dirty, 'base_path': base,
                    'pages': len(pages) + 2, 'files': files}
        (stage / 'site-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
        validate(stage, base)
        if output.exists():
            shutil.rmtree(output)
        shutil.move(str(stage), output)
    return manifest


class References(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.ids = [], set()
    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if 'id' in values:
            if values['id'] in self.ids:
                raise ValueError('Duplicate HTML id: ' + values['id'])
            self.ids.add(values['id'])
        for attr in ('href', 'src'):
            if attr in values:
                self.links.append(values[attr])


def validate(directory, base):
    documents = {}
    for path in directory.rglob('*.html'):
        parser = References()
        parser.feed(path.read_text(encoding='utf-8'))
        documents[path] = parser
    for source, parser in documents.items():
        for value in parser.links:
            link = urlsplit(value)
            if link.scheme or link.netloc:
                continue
            if link.path:
                if not link.path.startswith(base + '/'):
                    raise ValueError('Internal link misses base path: ' + value)
                target = directory / unquote(link.path[len(base) + 1:])
                if link.path.endswith('/'):
                    target /= 'index.html'
            else:
                target = source
            if not target.is_file():
                raise ValueError('Missing internal link: ' + value + ' in ' + str(source))
            if link.fragment and target in documents and unquote(link.fragment) not in documents[target].ids:
                raise ValueError('Missing anchor: ' + value + ' in ' + str(source))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / '.nrpe/site/nrpe-custom')
    parser.add_argument('--base-path', default=BASE)
    args = parser.parse_args()
    manifest = build(args.output, base=args.base_path)
    print(f"PASS: {manifest['pages']} pages built with verified internal links: {args.output}")


if __name__ == '__main__':
    main()
