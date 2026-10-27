#!/usr/bin/env python3
"""Delete only an unchanged topic head after its PR merged into develop."""

import json
import os
from pathlib import Path
import re
import subprocess


def output(command):
    return subprocess.check_output(command, text=True)


def cleanup(event, repository, call=output):
    pr = event.get('pull_request', {})
    head, base = pr.get('head', {}), pr.get('base', {})
    branch, sha = head.get('ref', ''), head.get('sha', '')
    if (pr.get('merged') is not True or base.get('ref') != 'develop'
            or branch in ('master', 'develop')
            or head.get('repo', {}).get('full_name') != repository
            or base.get('repo', {}).get('full_name') != repository
            or not re.match(r'^(feat|fix|refactor|remove)/', branch)):
        return False
    if not re.fullmatch('[0-9a-f]{40}', sha):
        raise ValueError('Invalid expected head SHA')
    call(['git', 'check-ref-format', '--branch', branch])
    owner = repository.split('/')[0]
    open_prs = json.loads(call(['gh', 'api', '--method', 'GET', 'repos/' + repository + '/pulls',
                               '-f', 'head=' + owner + ':' + branch, '-f', 'state=open']))
    if open_prs:
        return False
    refs = call(['git', 'ls-remote', 'origin', 'refs/heads/' + branch]).split()
    if not refs or refs[0] != sha:
        return False
    # The lease protects work pushed between the check above and the deletion.
    call(['git', 'push', '--force-with-lease=refs/heads/' + branch + ':' + sha,
          'origin', ':refs/heads/' + branch])
    return True


if __name__ == '__main__':
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text(encoding='utf-8'))
    print('Deleted eligible topic branch' if cleanup(event, os.environ['GITHUB_REPOSITORY'])
          else 'Retained branch: not eligible, changed, absent, or still needed')
