#!/usr/bin/env python3
"""Check PR routing and commit attribution without changing Git history."""

import argparse
import re
import subprocess


def check_route(base, head):
    if base == 'master' and head == 'develop':
        return
    if base == 'develop' and re.fullmatch(r'(feat|fix|refactor|remove)/[A-Za-z0-9][A-Za-z0-9._/-]*', head):
        subprocess.run(['git', 'check-ref-format', '--branch', head],
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
        return
    raise ValueError('Use a feat/fix/refactor/remove branch into develop, or develop into master')


def check_author(name, email, message):
    if not name.strip() or '@' not in email:
        raise ValueError('A human author name and email are required')
    if re.search(r'\[bot\]|\b(dependabot|github-actions|codex|chatgpt|copilot|claude|openai)\b',
                 name + ' ' + email, re.I):
        raise ValueError('Review and re-author bot proposals with the human author before integration')
    if re.search(r'^\s*(co-authored-by:|generated\s+(with|by)\b)', message, re.I | re.M):
        raise ValueError('Commit messages must not contain co-author or generated-with/by attribution')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-name', required=True)
    parser.add_argument('--head-name', required=True)
    parser.add_argument('--base-sha', required=True)
    parser.add_argument('--head-sha', required=True)
    args = parser.parse_args()
    check_route(args.base_name, args.head_name)
    for value in (args.base_sha, args.head_sha):
        if not re.fullmatch(r'[0-9a-f]{40}', value):
            raise ValueError('Expected a full Git commit SHA')
    commits = subprocess.check_output(
        ['git', 'rev-list', args.base_sha + '..' + args.head_sha], text=True).splitlines()
    for commit in commits:
        fields = subprocess.check_output(
            ['git', 'show', '-s', '--format=%an%x00%ae%x00%B', commit], text=True).split('\0', 2)
        check_author(*fields)
    print('PASS: PR route and {} commit author/message checks'.format(len(commits)))


if __name__ == '__main__':
    main()
