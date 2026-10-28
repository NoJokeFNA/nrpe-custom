"""Preview or remove expired local evidence and explicitly selected images."""

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess

from .docker import check_docker
from .state import artifact, maintenance_guard, reports
from .targets import TARGETS


RETIRED_TARGETS = ('sles15sp3', 'sles15sp4')
RUN_ID = re.compile(r'[0-9]{8}T[0-9]{6}-[0-9a-f]{8}')
IMAGE = re.compile(r'nrpe-custom-(?:builder|test(?:-(?:debian1[1-4]|sles12sp3|sles15sp[34]))?):[A-Za-z0-9_][A-Za-z0-9_.-]*')


def ordinary(path):
    """Reject links and Windows junction/reparse points before traversal."""
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
        raise RuntimeError('Cleanup refuses links or reparse points: ' + str(path))
    if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
        raise RuntimeError('Cleanup refuses special files: ' + str(path))
    return info


def tree(path):
    ordinary(path)
    if os.path.ismount(path):
        raise RuntimeError('Cleanup refuses mounted directories: ' + str(path))
    for directory, children, files in os.walk(path, followlinks=False):
        for name in children + files:
            child = Path(directory) / name
            info = ordinary(child)
            if stat.S_ISDIR(info.st_mode) and os.path.ismount(child):
                raise RuntimeError('Cleanup refuses mounted directories: ' + str(child))
            yield info


def checked_roots(root):
    for path in (root, root / '.nrpe', root / '.nrpe/runs', root / '.nrpe/locks', root / 'output'):
        if path.exists() or path.is_symlink():
            ordinary(path)


def plan(root, older_than=30, keep_runs=5, retired_outputs=False, now=None):
    if older_than < 0 or keep_runs < 0:
        raise RuntimeError('Retention days and retained run count must be nonnegative')
    checked_roots(root)
    now = now or datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=older_than)).timestamp()
    # Do not follow report symlinks, including those in malformed run directories.
    runs = root / '.nrpe/runs'
    if runs.exists():
        for directory in runs.iterdir():
            ordinary(directory)
            report = directory / 'report.json'
            if report.exists() or report.is_symlink():
                ordinary(report)
    history = [r for r in reports(root) if isinstance(r.get('targets'), dict)
               and all(isinstance(value, dict) for value in r['targets'].values())]
    protected = {r['id'] for r in history[:keep_runs]}
    for target in TARGETS:
        candidates = [r for r in history if target in r.get('targets', {})]
        if candidates:
            protected.add(candidates[0]['id'])
        try:
            current = artifact(root, target)
        except (OSError, RuntimeError):
            continue
        matching = next((r for r in candidates
                         if r['targets'][target].get('artifact') == current
                         and r['targets'][target].get('test') in ('passed', 'failed', 'interrupted')), None)
        if matching:
            protected.add(matching['id'])
        verified = next((r for r in candidates if r.get('action') == 'verify'
                         and r.get('status') == 'passed'
                         and r['targets'][target].get('artifact') == current
                         and all(r['targets'][target].get(phase) == 'passed'
                                 for phase in ('build', 'package', 'test'))), None)
        if verified:
            protected.add(verified['id'])
    result = []
    for report in history:
        run_id = report['id']
        if (not RUN_ID.fullmatch(run_id) or run_id in protected
                or report.get('status') not in ('passed', 'failed', 'interrupted')):
            continue
        try:
            finished = datetime.fromisoformat(report['finished'])
            if finished.tzinfo is None or finished.timestamp() > cutoff:
                continue
        except (KeyError, TypeError, ValueError):
            continue
        directory = runs / run_id
        if any(p.name not in ('report.json', 'run.log') for p in directory.iterdir()):
            continue
        entries = list(tree(directory))
        if max([directory.stat().st_mtime] + [s.st_mtime for s in entries]) > cutoff:
            continue
        result.append((directory, sum(s.st_size for s in entries if stat.S_ISREG(s.st_mode))))
    if retired_outputs:
        for target in RETIRED_TARGETS:
            directory = root / 'output' / target
            if not directory.exists() and not directory.is_symlink():
                continue
            ordinary(directory)
            known = {'SHA256SUMS', 'source-manifest.json', 'user-source-manifest.json',
                     'macros-source-manifest.json', 'bootstrap-manifest.json', 'obs-sources', 'sources'}
            if any(p.name not in known and not re.fullmatch(
                    r'(?:nrpe|system-user-nagios|monitoring-plugins-nrpe|nagios-rpm-macros)-[0-9][A-Za-z0-9_.+~-]*\.rpm',
                    p.name) for p in directory.iterdir()):
                continue
            entries = list(tree(directory))
            if max([directory.stat().st_mtime] + [s.st_mtime for s in entries]) <= cutoff:
                result.append((directory, sum(s.st_size for s in entries if stat.S_ISREG(s.st_mode))))
    return result


def inspect_images(images):
    if not images:
        return None, []
    if any(not IMAGE.fullmatch(name) for name in images):
        raise RuntimeError('Select an explicit nrpe-custom builder/test image with a tag; '
                           'base images, image IDs and wildcards are not accepted')
    docker = check_docker()
    result = []
    for name in dict.fromkeys(images):
        info = subprocess.run([docker, 'image', 'inspect', name],
                              capture_output=True, text=True, check=False, timeout=30)
        if info.returncode:
            raise RuntimeError('Cannot inspect selected image: ' + name)
        try:
            image_id = json.loads(info.stdout)[0]['Id']
            if not isinstance(image_id, str) or not re.fullmatch(r'sha256:[0-9a-f]{64}', image_id):
                raise ValueError('Invalid image identity')
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise RuntimeError('Invalid Docker image inspection result: ' + name) from exc
        containers = subprocess.check_output(
            [docker, 'ps', '--all', '--quiet', '--filter', 'ancestor=' + image_id], text=True, timeout=30)
        if containers.strip():
            raise RuntimeError('Selected image is used by a running or stopped container: ' + name)
        result.append((name, image_id))
    return docker, result


def clean(root, older_than=30, keep_runs=5, retired_outputs=False, images=(), apply=False):
    """No changes without --apply; never delete active output or arbitrary state."""
    selected = plan(root, older_than, keep_runs, retired_outputs)
    docker, image_plan = inspect_images(images)
    for path, size in selected:
        print(f"Would remove {path.relative_to(root)} ({size} bytes)")
    for name, _ in image_plan:
        print(f"Would remove Docker image {name}")
    if not selected and not image_plan:
        print('Nothing eligible for cleanup. Current packages and retained evidence are kept.')
        return 0
    if not apply:
        print('Preview only. Use --apply with the same options to perform cleanup.')
        return 0
    with maintenance_guard(root):
        locks = [p.name for p in (root / '.nrpe/locks').iterdir() if p.name != 'maintenance']
        if locks:
            raise RuntimeError('Cleanup refused: active or unresolved target locks: ' + ', '.join(sorted(locks)))
        # Recheck under the guard; never act on a stale preview.
        fresh = plan(root, older_than, keep_runs, retired_outputs)
        if fresh != selected:
            raise RuntimeError('Cleanup candidates changed; preview again')
        if inspect_images(images)[1] != image_plan:
            raise RuntimeError('Selected image identity changed; preview again')
        for path, _ in fresh:
            list(tree(path))
            shutil.rmtree(path)
            print('Removed ' + str(path.relative_to(root)))
        for name, _ in image_plan:
            subprocess.run([docker, 'image', 'rm', name], check=True, timeout=60)
    print('Cleanup complete. Current target outputs, locks and release bundles were retained.')
    return 0
