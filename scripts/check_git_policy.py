#!/usr/bin/env python3
"""Check PR routing and commit attribution without changing Git history."""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess


DEPENDABOT_AUTHOR = ('dependabot[bot]', '49699333+dependabot[bot]@users.noreply.github.com')


def same_repository(pr, repository):
    return bool(repository and all(pr.get(side, {}).get('repo', {}).get('full_name') == repository
                                   for side in ('base', 'head')))


def is_dependabot_pr(pr, repository):
    user = pr.get('user', {})
    return (same_repository(pr, repository) and pr.get('base', {}).get('ref') == 'develop'
            and pr.get('head', {}).get('ref', '').startswith('dependabot/')
            and user.get('login') == 'dependabot[bot]' and user.get('id') == 49699333
            and user.get('type') == 'Bot')


def dependabot_permissions(base, head, base_sha, head_sha, event, repository):
    pr = event.get('pull_request', {})
    matches = (pr.get('base', {}).get('ref') == base and pr.get('head', {}).get('ref') == head
               and pr.get('base', {}).get('sha') == base_sha
               and pr.get('head', {}).get('sha') == head_sha)
    proposal = matches and is_dependabot_pr(pr, repository)
    promotion = (matches and same_repository(pr, repository)
                 and base == 'master' and head == 'develop')
    return proposal, proposal or promotion


def check_route(base, head, allow_dependabot=False):
    if base == 'master' and head == 'develop':
        return
    prefixes = 'feat|fix|refactor|remove' + ('|dependabot' if allow_dependabot else '')
    if base == 'develop' and re.fullmatch(r'(' + prefixes + r')/[A-Za-z0-9][A-Za-z0-9._/-]*', head):
        subprocess.run(['git', 'check-ref-format', '--branch', head],
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
        return
    raise ValueError('Use a feat/fix/refactor/remove branch into develop, or develop into master')


def check_author(name, email, message, allow_dependabot=False):
    if not name.strip() or '@' not in email:
        raise ValueError('A human author name and email are required')
    approved_bot = allow_dependabot and (name, email) == DEPENDABOT_AUTHOR
    if not approved_bot and re.search(r'\[bot\]|\b(dependabot|github-actions|codex|chatgpt|copilot|claude|openai)\b',
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
    event_path = os.environ.get('GITHUB_EVENT_PATH')
    event = json.loads(Path(event_path).read_text(encoding='utf-8')) if event_path else {}
    proposal, allow_bot = dependabot_permissions(
        args.base_name, args.head_name, args.base_sha, args.head_sha,
        event, os.environ.get('GITHUB_REPOSITORY', ''))
    check_route(args.base_name, args.head_name, allow_dependabot=proposal)
    for value in (args.base_sha, args.head_sha):
        if not re.fullmatch(r'[0-9a-f]{40}', value):
            raise ValueError('Expected a full Git commit SHA')
    commits = subprocess.check_output(
        ['git', 'rev-list', args.base_sha + '..' + args.head_sha], text=True).splitlines()
    for commit in commits:
        fields = subprocess.check_output(
            ['git', 'show', '-s', '--format=%an%x00%ae%x00%B', commit], text=True).split('\0', 2)
        check_author(*fields, allow_dependabot=allow_bot)
    print('PASS: PR route and {} commit author/message checks'.format(len(commits)))


if __name__ == '__main__':
    main()
