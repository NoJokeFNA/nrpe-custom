#!/usr/bin/env python3
"""Preview a human-authored gh-pages deployment; push only with --push."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.check_git_policy import check_author
from website.build import BASE, REPOSITORY, identity, validate


def git(root, *arguments, **kwargs):
    return subprocess.check_output(['git', *arguments], cwd=root, text=True, **kwargs).strip()


def publish(root, output, push=False, remote='origin', allow_topic=False):
    commit, dirty = identity(root)
    if dirty or not commit:
        raise RuntimeError('Publication requires a clean committed source checkout')
    if git(root, 'branch', '--show-current') not in ('develop', 'master') and not allow_topic:
        raise RuntimeError('Explicitly review website topic sources and use --allow-topic for separate publication')
    manifest = json.loads((output / 'site-manifest.json').read_text(encoding='utf-8'))
    if (manifest.get('generator') != 'nrpe-custom-pages' or manifest.get('source_commit') != commit
            or manifest.get('dirty') is not False or manifest.get('base_path') != BASE
            or manifest.get('repository') != REPOSITORY):
        raise RuntimeError('Rebuild from this exact clean source commit with the production base path')
    files, actual = manifest['files'], set()
    for path in [output, *output.rglob('*')]:
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise RuntimeError('Refusing linked deployment files')
        if path.is_file():
            actual.add(path.relative_to(output).as_posix())
    if actual != set(files) | {'site-manifest.json'}:
        raise RuntimeError('Deployment contains extra or missing files')
    for name, expected in files.items():
        if Path(name).is_absolute() or '..' in Path(name).parts:
            raise RuntimeError('Unsafe deployment filename')
        if hashlib.sha256((output / name).read_bytes()).hexdigest() != expected:
            raise RuntimeError('Deployment asset changed since build: ' + name)
    validate(output, BASE)
    message = 'docs(pages): publish documentation from ' + commit[:12]
    for kind in ('AUTHOR', 'COMMITTER'):
        ident = git(root, 'var', 'GIT_' + kind + '_IDENT')
        parsed = re.fullmatch(r'(.+) <([^>]+)> [0-9]+ [+-][0-9]{4}', ident)
        if not parsed:
            raise RuntimeError('Cannot determine the human Git identity')
        check_author(parsed[1], parsed[2], message)
    print(f'Site source: {commit}; {len(actual)} checked files')
    print('Deployment target: ' + remote + ':refs/heads/gh-pages')
    if not push:
        print('Preview only. Use --push after reviewing the rendered site. No Git refs were changed.')
        return None
    remote_ref = git(root, 'ls-remote', '--heads', remote, 'refs/heads/gh-pages').split()
    parent = remote_ref[0] if remote_ref else None
    if parent:
        git(root, 'fetch', '--no-tags', remote, 'refs/heads/gh-pages')
        if git(root, 'rev-parse', 'FETCH_HEAD') != parent:
            raise RuntimeError('Deployment branch moved; review and retry')
    state = root / '.nrpe'
    state.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='pages-index-', dir=state) as temporary:
        environment = dict(os.environ, GIT_INDEX_FILE=str(Path(temporary) / 'index'), GIT_WORK_TREE=str(output.resolve()))
        git(root, 'read-tree', '--empty', env=environment)
        git(root, 'add', '--', *sorted(actual), env=environment)
        tree = git(root, 'write-tree', env=environment)
        arguments = ['commit-tree', tree, '-m', message]
        if parent:
            arguments += ['-p', parent]
        deployed = git(root, *arguments)
    git(root, 'push', remote, deployed + ':refs/heads/gh-pages')
    print('Published human-authored deployment commit: ' + deployed)
    return deployed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=ROOT / '.nrpe/site/nrpe-custom')
    parser.add_argument('--push', action='store_true')
    parser.add_argument('--allow-topic', action='store_true',
                        help='Publish reviewed topic sources without merging them into develop/master')
    args = parser.parse_args()
    publish(ROOT, args.directory, args.push, allow_topic=args.allow_topic)


if __name__ == '__main__':
    main()
