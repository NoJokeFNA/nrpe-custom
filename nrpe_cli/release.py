"""Prepare verified release archives; never publish or install packages here."""

import hashlib
import ast
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tarfile
import tempfile

from .state import artifact, reports, workflow_identity
from .targets import TARGETS, DEFAULT_TARGETS
from scripts.export_debian_sources import source_files
from scripts.sles_source import patch_spec


def digest(path):
    checksum = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            checksum.update(block)
    return checksum.hexdigest()


def snapshot_assets(root, target):
    directory = root / 'output' / target
    result = {}
    for path in sorted(directory.rglob('*')):
        if path.is_symlink():
            raise RuntimeError('Release assets must not contain symlinks')
        placeholder = path.name == '.gitkeep' and path.parent == directory and path.stat().st_size == 0
        if path.is_file() and path.suffix != '.buildinfo' and not placeholder:
            result[path.relative_to(directory).as_posix()] = digest(path)
    return result


def verified_evidence(root, target, commit):
    if target not in TARGETS or not re.fullmatch('[0-9a-f]{40}', commit):
        raise RuntimeError('Invalid target or full commit SHA')
    identity = {'commit': commit, 'dirty': False}
    if workflow_identity(root) != identity:
        raise RuntimeError('Release preparation requires the exact clean workflow checkout')
    candidates = [r for r in reports(root) if target in r.get('targets', {})]
    if not candidates:
        raise RuntimeError('No verification report for ' + target)
    report = candidates[0]
    result = report['targets'][target]
    if (report.get('action') != 'verify' or report.get('status') != 'passed'
            or report.get('exit_code') != 0
            or any(result.get(p) != 'passed' for p in ('build', 'package', 'test'))):
        raise RuntimeError('A complete successful build/package/integration verify run is required')
    if any(report.get(key) != identity for key in ('workflow_before', 'workflow_after')):
        raise RuntimeError('Verification belongs to different, dirty or unrecorded workflow sources')
    current = snapshot_assets(root, target)
    if result.get('release_assets') != current or result.get('artifact') != artifact(root, target):
        raise RuntimeError('Binary or source assets changed since verification')
    # Only these fields are public: no raw logs, CA/media paths or environment.
    return {'schema': 1, 'target': target, 'commit': commit,
            'run_id': report['id'], 'checks': {p: result[p] for p in ('build', 'package', 'test')},
            'artifact': result['artifact'], 'assets': current}


def one(directory, pattern):
    matches = list(directory.glob(pattern))
    if len(matches) != 1:
        raise RuntimeError('Expected exactly one ' + pattern)
    return matches[0]


def checked_bytes(path, expected):
    if path.is_symlink() or not path.is_file() or path.stat().st_size != expected['size']:
        raise RuntimeError('Missing or wrong-sized source input: ' + path.name)
    if digest(path) != expected['sha256']:
        raise RuntimeError('Source input checksum mismatch: ' + path.name)
    return path.read_bytes()


def rpm_fields(path):
    text = subprocess.check_output(
        ['rpm', '-qp', '--queryformat', '%{NAME}\n%{VERSION}-%{RELEASE}\n%{SOURCERPM}\n%{SOURCEPACKAGE}\n', str(path)],
        text=True)
    return text.strip().splitlines()


def rpm_source_member(path, name):
    archive = subprocess.check_output(['rpm2cpio', str(path)])
    return subprocess.run(['cpio', '-i', '--quiet', '--to-stdout', '--', name],
                          input=archive, capture_output=True, check=True).stdout


def validate_sources(root, target, evidence, notices):
    directory = root / 'output' / target
    version = evidence['artifact']['version']
    if target.startswith('debian'):
        dsc = one(directory / 'sources', '*.dsc')
        checked_sources = source_files(dsc, version)
        official_version = re.sub(r'\+withargs[0-9]+$', '', version)
        approved = json.loads((root / 'packaging/debian-license-review.json').read_text())['versions']
        if official_version not in approved:
            raise RuntimeError('New Debian source version requires license review before publication')
        review = approved[official_version]
        actual_upstream = {p.name: sha for p, sha in checked_sources if '.orig.tar.' in p.name}
        if actual_upstream != review['upstream_archives']:
            raise RuntimeError('Reviewed upstream source archive changed')
        allowed = {evidence['artifact']['file'], 'SHA256SUMS', 'sources/SHA256SUMS'}
        allowed.update('sources/' + path.name for path, _ in checked_sources)
        metadata = subprocess.check_output(
            ['dpkg-deb', '--field', str(directory / evidence['artifact']['file']), 'Version'], text=True).strip()
        if metadata != version:
            raise RuntimeError('Debian binary/source version mismatch')
        with tempfile.TemporaryDirectory(prefix='nrpe-release-source-') as temporary:
            extracted = Path(temporary) / 'source'
            subprocess.run(['dpkg-source', '--extract', str(dsc.resolve()), str(extracted)],
                           check=True, capture_output=True)
            rules = (extracted / 'debian/rules').read_text()
            for name, sha in review['license_files'].items():
                if digest(extracted / name) != sha:
                    raise RuntimeError('Debian source/license evidence changed: ' + name)
            if rules.count('--enable-command-args') != 1 or '--enable-bash-command-substitution' in rules:
                raise RuntimeError('Unexpected Debian build flags in corresponding source')
            copyright_text = (extracted / 'debian/copyright').read_text()
            if 'OpenSSL' not in copyright_text or 'GPL-2+' not in copyright_text:
                raise RuntimeError('Debian license terms changed; review before publication')
            for name in ('LICENSE.md', 'LEGAL', 'debian/copyright'):
                data = (extracted / name).read_bytes()
                (notices / Path(name).name).write_bytes(data)
    elif target == 'archlinux':
        from scripts.arch_source import validate_export
        allowed = validate_export(root, directory, evidence, notices)
    else:
        allowed = {'SHA256SUMS', 'source-manifest.json', 'user-source-manifest.json', 'macros-source-manifest.json', 'bootstrap-manifest.json'}
        pairs = [('nrpe', 'source-manifest.json', 'sles12sp3-source.json'),
                 ('system-user-nagios', 'user-source-manifest.json', 'sles12sp3-user-source.json'),
                 ('nagios-rpm-macros', 'macros-source-manifest.json', 'sles12sp3-macros-source.json')]
        for package, manifest_name, pinned_name in pairs:
            manifest = json.loads((root / 'packaging' / pinned_name).read_text())
            if json.loads((directory / manifest_name).read_text()) != manifest:
                raise RuntimeError('SLES manifest differs from the workflow inputs')
            source = one(directory, package + '-*.src.rpm')
            expected_version = manifest['version'] + '-' + manifest.get('custom_release', manifest.get('release', ''))
            source_info = rpm_fields(source)
            if source_info[:2] != [package, expected_version] or source_info[3] != '1':
                raise RuntimeError('RPM source identity mismatch')
            allowed.add(source.name)
            if package != 'nagios-rpm-macros':
                binary = (directory / evidence['artifact']['file'] if package == 'nrpe'
                          else one(directory, package + '-*.noarch.rpm'))
                binary_info = rpm_fields(binary)
                if binary_info[:2] != source_info[:2] or binary_info[2] != source.name:
                    raise RuntimeError('RPM binary/source identity mismatch')
                allowed.add(binary.name)
            if package == 'nrpe':
                if version != expected_version:
                    raise RuntimeError('RPM filename and source version mismatch')
                client = one(directory, 'monitoring-plugins-nrpe-*.x86_64.rpm')
                client_info = rpm_fields(client)
                if client_info[:3] != ['monitoring-plugins-nrpe', expected_version, source.name]:
                    raise RuntimeError('NRPE client does not match the server source')
                allowed.add(client.name)
            for name, expected in manifest['files'].items():
                if Path(name).name != name or '\\' in name:
                    raise RuntimeError('Unsafe manifest filename')
                original = checked_bytes(directory / 'obs-sources' / package / name, expected)
                allowed.add('obs-sources/' + package + '/' + name)
                if name.endswith('.changes'):
                    continue  # OBS history is included separately, not declared as SRPM Source.
                packed = rpm_source_member(source, name)
                if package == 'nrpe' and name == 'nrpe.spec':
                    original = patch_spec(original.decode(), manifest['version'], manifest['custom_release']).encode()
                if packed != original:
                    raise RuntimeError('SRPM source differs from pinned input: ' + name)
            if package == 'nrpe':
                archive = directory / 'obs-sources/nrpe' / ('nrpe-' + manifest['version'] + '.tar.xz')
                with tarfile.open(archive) as source_tar:
                    prefix = 'nrpe-' + manifest['version'] + '/'
                    for source_name, notice_name in [('LICENSE.md', 'NRPE-GPL-2.0.md'), ('LEGAL', 'NRPE-LEGAL.txt')]:
                        data = source_tar.extractfile(prefix + source_name).read()
                        if data != (root / 'packaging/licenses/sles12sp3' / notice_name).read_bytes():
                            raise RuntimeError('SLES license text changed; update the review and notices')
                    utils = source_tar.extractfile(prefix + 'src/utils.c').read().decode()
                    section = utils.split('void display_license(void)', 1)[1]
                    notice = ''.join(ast.literal_eval(s) for s in re.findall(r'printf\(("(?:[^"\\]|\\.)*")\)', section))
                    if notice != (root / 'packaging/licenses/sles12sp3/NRPE-license-notice.txt').read_text():
                        raise RuntimeError('SLES OpenSSL/GPL notice changed')
            elif package == 'system-user-nagios':
                header = (directory / 'obs-sources/system-user-nagios/system-user-nagios.spec').read_text().split('%if', 1)[0]
                if header != (root / 'packaging/licenses/sles12sp3/system-user-nagios-spec-header.txt').read_text():
                    raise RuntimeError('Companion source copyright/licensing header changed')
            elif package == 'nagios-rpm-macros':
                original = directory / 'obs-sources/nagios-rpm-macros/nagios-rpm-macros-COPYING'
                if original.read_bytes() != (root / 'packaging/licenses/sles12sp3/nagios-rpm-macros-BSD.txt').read_bytes():
                    raise RuntimeError('Nagios macros license notice changed')
        bootstrap = json.loads((directory / 'bootstrap-manifest.json').read_text())
        if bootstrap != json.loads((root / 'packaging/sles12sp3-bootstrap.json').read_text()):
            raise RuntimeError('Bootstrap manifest mismatch')
        shutil.copytree(root / 'packaging/licenses/sles12sp3', notices / 'sles12sp3')
    if set(evidence['assets']) != allowed:
        raise RuntimeError('Output asset mismatch: missing={}, extra={}'.format(
            sorted(allowed - set(evidence['assets'])), sorted(set(evidence['assets']) - allowed)))


def prepare_target(root, target, commit, destination):
    evidence = verified_evidence(root, target, commit)
    destination.mkdir(parents=True, exist_ok=True)
    output = destination / ('nrpe-custom-' + target + '.tar.gz')
    if output.exists():
        raise RuntimeError('Refusing to replace an existing target archive')
    with tempfile.TemporaryDirectory(prefix='nrpe-release-') as temporary:
        stage = Path(temporary) / target
        stage.mkdir()
        notices = stage / 'licenses'
        notices.mkdir()
        validate_sources(root, target, evidence, notices)
        for name in evidence['assets']:
            source = root / 'output' / target / name
            path = stage / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, path)
        shutil.copyfile(root / 'LICENSE', notices / 'PROJECT-MIT.txt')
        shutil.copyfile(root / 'THIRD_PARTY.md', notices / 'THIRD_PARTY.md')
        files = {p.relative_to(stage).as_posix(): digest(p) for p in stage.rglob('*') if p.is_file()}
        evidence['files'] = files
        (stage / 'manifest.json').write_text(json.dumps(evidence, indent=2) + '\n')
        if verified_evidence(root, target, commit)['assets'] != evidence['assets']:
            raise RuntimeError('Assets changed during staging')
        try:
            with tarfile.open(output, 'w:gz') as archive:
                def public_metadata(info):
                    info.uid = info.gid = 0
                    info.uname = info.gname = ''
                    info.mtime = 0
                    info.pax_headers = {}
                    info.mode = 0o644
                    return info
                for path in sorted(stage.rglob('*')):
                    if path.is_file():
                        archive.add(path, arcname=target + '/' + path.relative_to(stage).as_posix(),
                                    filter=public_metadata)
            verify_archive(output, target, commit)
        except Exception:
            output.unlink(missing_ok=True)
            raise
    return output


def verify_archive(path, target, commit):
    contents = {}
    total = 0
    with tarfile.open(path, 'r:gz') as archive:
        for entry in archive:
            parts = PurePosixPath(entry.name).parts
            total += entry.size
            if (not entry.isfile() or not parts or parts[0] != target or '..' in parts
                    or entry.name.startswith('/') or '\\' in entry.name or ':' in entry.name
                    or entry.name in contents or total > 256 * 1024 * 1024):
                raise RuntimeError('Unsafe, duplicate or oversized archive entry')
            contents[entry.name] = archive.extractfile(entry).read()
    manifest = json.loads(contents.pop(target + '/manifest.json'))
    if (manifest.get('target') != target or manifest.get('commit') != commit
            or manifest.get('checks') != {p: 'passed' for p in ('build', 'package', 'test')}):
        raise RuntimeError('Archive target, workflow or test evidence mismatch')
    actual = {name[len(target) + 1:]: hashlib.sha256(data).hexdigest() for name, data in contents.items()}
    if actual != manifest['files'] or any(actual.get(n) != h for n, h in manifest['assets'].items()):
        raise RuntimeError('Archive asset checksum or completeness mismatch')
    for required in ('licenses/PROJECT-MIT.txt', 'licenses/THIRD_PARTY.md', 'SHA256SUMS'):
        if required not in actual:
            raise RuntimeError('Missing required notice or checksum manifest')
    assets = manifest['assets']
    binary = manifest['artifact']['file']
    if binary not in assets:
        raise RuntimeError('Missing binary artifact')
    if target.startswith('debian'):
        for marker in ('.dsc', '.orig.tar.', '.debian.tar.'):
            if not any(n.startswith('sources/') and marker in n for n in assets):
                raise RuntimeError('Missing corresponding Debian source')
        required = ['licenses/LICENSE.md', 'licenses/LEGAL', 'licenses/copyright']
    elif target == 'archlinux':
        required = ['licenses/archlinux/LICENSE.md', 'licenses/archlinux/LEGAL']
        if ('ARGUMENT-POLICY.md' not in assets or 'source-manifest.json' not in assets
                or not any(n.startswith('sources/') and n.endswith('.src.tar.gz') for n in assets)):
            raise RuntimeError('Missing optional Arch policy or corresponding source')
    else:
        required = ['licenses/sles12sp3/' + n for n in (
            'NRPE-GPL-2.0.md', 'NRPE-LEGAL.txt', 'NRPE-license-notice.txt',
            'system-user-nagios-MIT.txt', 'system-user-nagios-spec-header.txt', 'nagios-rpm-macros-BSD.txt')]
        for name in ('source-manifest.json', 'user-source-manifest.json', 'bootstrap-manifest.json',
                     'macros-source-manifest.json', 'obs-sources/nrpe/nrpe.changes',
                     'obs-sources/system-user-nagios/system-user-nagios.changes',
                     'obs-sources/nagios-rpm-macros/nagios-rpm-macros.changes'):
            if name not in assets:
                raise RuntimeError('Missing SLES source provenance')
        if sum(n.endswith('.src.rpm') for n in assets) != 3:
            raise RuntimeError('All three SLES source RPMs are required')
        if not any(n.startswith('monitoring-plugins-nrpe-') and n.endswith('.x86_64.rpm') for n in assets):
            raise RuntimeError('Matching SLES NRPE client is required')
    if not all(name in actual for name in required):
        raise RuntimeError('Missing component license notices')
    return manifest


def assemble(root, incoming, commit, destination):
    if workflow_identity(root) != {'commit': commit, 'dirty': False}:
        raise RuntimeError('Exact clean workflow checkout required')
    expected = {'nrpe-custom-' + t + '.tar.gz' for t in DEFAULT_TARGETS}
    if {p.name for p in incoming.iterdir()} != expected:
        raise RuntimeError('All five target archives, and no extra assets, are required')
    manifests = [verify_archive(incoming / ('nrpe-custom-' + t + '.tar.gz'), t, commit) for t in DEFAULT_TARGETS]
    destination.mkdir(parents=True, exist_ok=False)
    for name in expected:
        shutil.copyfile(incoming / name, destination / name)
    subprocess.run(['git', 'archive', '--format=tar.gz', '--prefix=nrpe-custom/',
                    '--output=' + str((destination / 'workflow-source.tar.gz').resolve()), commit],
                   cwd=root, check=True)
    for name in ('LICENSE', 'THIRD_PARTY.md'):
        shutil.copyfile(root / name, destination / name)
    release = {'schema': 1, 'commit': commit, 'targets': manifests}
    (destination / 'release.json').write_text(json.dumps(release, indent=2) + '\n')
    lines = ['Unofficial NRPE custom build', '', 'Workflow commit: ' + commit, '',
             'All five targets passed build, package installation and TLS argument tests.', '']
    lines += ['- ' + m['target'] + ': ' + m['artifact']['version'] for m in manifests]
    lines += ['', 'Arguments remain disabled by default; Bash substitution stays disabled.',
              'Local custom RPMs are unsigned. Archives contain corresponding sources and license notices.',
              'No container images or SLES media are distributed.',
              'See docs/installation.md and docs/updates-and-rollback.md in workflow-source.tar.gz.',
              'Provided AS IS under the included licenses; systemd/production TLS/firewall deployment is not certified.']
    (destination / 'RELEASE_NOTES.md').write_text('\n'.join(lines) + '\n')
    (destination / 'SHA256SUMS').write_text(''.join(
        digest(path) + '  ' + path.name + '\n' for path in sorted(destination.iterdir()) if path.is_file()))
