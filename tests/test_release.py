"""Release gates reject stale, incomplete and unsafe bundles without Docker."""

import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from nrpe_cli import release, state


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.commit = 'a' * 40
        self.identity = {'commit': self.commit, 'dirty': False}
        self.directory = self.root / 'output/debian12'
        self.directory.mkdir(parents=True)
        self.binary = 'nagios-nrpe-server_4.1.0-1+withargs1_amd64.deb'
        self.files = {self.binary: b'binary', 'SHA256SUMS': b'checksums',
                      'sources/source.dsc': b'dsc', 'sources/source.orig.tar.gz': b'upstream',
                      'sources/source.debian.tar.xz': b'custom packaging',
                      'licenses/PROJECT-MIT.txt': b'project', 'licenses/THIRD_PARTY.md': b'inventory',
                      'licenses/LICENSE.md': b'GPL', 'licenses/LEGAL': b'trademarks',
                      'licenses/copyright': b'copyright and exception'}
        for name, data in self.files.items():
            if not name.startswith('licenses/'):
                path = self.directory / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
        sha = hashlib.sha256(b'binary').hexdigest()
        (self.directory / 'SHA256SUMS').write_text(sha + '  ' + self.binary + '\n')
        self.files['SHA256SUMS'] = (self.directory / 'SHA256SUMS').read_bytes()
        self.report = {'schema': 1, 'id': 'verify-run', 'action': 'verify', 'status': 'passed',
                       'exit_code': 0, 'workflow_before': self.identity, 'workflow_after': self.identity,
                       'targets': {'debian12': {'build': 'passed', 'package': 'passed', 'test': 'passed',
                           'artifact': state.artifact(self.root, 'debian12'),
                           'release_assets': release.snapshot_assets(self.root, 'debian12')}}}
        self.save_report()

    def save_report(self):
        directory = self.root / '.nrpe/runs/verify-run'
        directory.mkdir(parents=True, exist_ok=True)
        state.save_report(directory, self.report)

    def evidence(self):
        with patch('nrpe_cli.release.workflow_identity', return_value=self.identity):
            return release.verified_evidence(self.root, 'debian12', self.commit)

    def test_evidence_is_bound_to_clean_commit_and_sanitized(self):
        self.report.update(sles_media='private/path', ca_certificate_sha256='private identity', error='private log')
        self.save_report()
        evidence = self.evidence()
        self.assertEqual(evidence['commit'], self.commit)
        self.assertNotIn('private', json.dumps(evidence))
        with patch('nrpe_cli.release.workflow_identity', return_value={'commit': self.commit, 'dirty': True}):
            with self.assertRaisesRegex(RuntimeError, 'clean'):
                release.verified_evidence(self.root, 'debian12', self.commit)

    def test_runtime_only_failed_and_wrong_source_reports_are_rejected(self):
        for key, value in [('action', 'test'), ('status', 'failed'), ('workflow_before', None),
                           ('workflow_after', {'commit': 'b' * 40, 'dirty': False})]:
            with self.subTest(key=key):
                original = self.report[key]
                self.report[key] = value
                self.save_report()
                with self.assertRaises(RuntimeError):
                    self.evidence()
                self.report[key] = original
        self.report['targets']['debian12']['build'] = 'not run'
        self.save_report()
        with self.assertRaises(RuntimeError):
            self.evidence()

    def test_changed_sources_invalidate_successful_binary_tests(self):
        (self.directory / 'sources/source.debian.tar.xz').write_bytes(b'replaced')
        with self.assertRaisesRegex(RuntimeError, 'changed'):
            self.evidence()

    def test_buildinfo_with_local_environment_is_not_a_release_asset(self):
        (self.directory / 'local.buildinfo').write_text('private environment values')
        self.assertFalse(any(n.endswith('.buildinfo') for n in self.evidence()['assets']))

    def test_only_empty_root_placeholders_are_excluded(self):
        marker = self.directory / '.gitkeep'
        marker.touch()
        self.assertNotIn('.gitkeep', self.evidence()['assets'])
        marker.write_text('unexpected content')
        with self.assertRaisesRegex(RuntimeError, 'changed'):
            self.evidence()

    def test_unreviewed_debian_source_is_rejected_before_external_tools(self):
        metadata = self.root / 'packaging/debian-license-review.json'
        metadata.parent.mkdir()
        metadata.write_text('{"versions": {}}')
        with patch('nrpe_cli.release.source_files', return_value=[]), \
                patch('nrpe_cli.release.subprocess.check_output') as command:
            with self.assertRaisesRegex(RuntimeError, 'license review'):
                release.validate_sources(self.root, 'debian12', self.evidence(), self.root / 'notices')
            command.assert_not_called()

    def archive(self, files=None, extra=None):
        files = self.files.copy() if files is None else files
        evidence = self.evidence()
        evidence['files'] = {n: hashlib.sha256(data).hexdigest() for n, data in files.items()}
        path = self.root / 'bundle.tar.gz'
        with tarfile.open(path, 'w:gz') as stream:
            for name, data in dict(files, **{'manifest.json': json.dumps(evidence).encode()}).items():
                info = tarfile.TarInfo('debian12/' + name)
                info.size = len(data)
                stream.addfile(info, io.BytesIO(data))
            if extra is not None:
                stream.addfile(extra, io.BytesIO(b'x'))
        return path

    def test_archive_checks_target_commit_notices_and_exact_contents(self):
        path = self.archive()
        self.assertEqual(release.verify_archive(path, 'debian12', self.commit)['target'], 'debian12')
        with self.assertRaises(RuntimeError):
            release.verify_archive(path, 'debian12', 'b' * 40)
        files = self.files.copy()
        del files['licenses/LEGAL']
        with self.assertRaisesRegex(RuntimeError, 'license'):
            release.verify_archive(self.archive(files), 'debian12', self.commit)

    def test_archive_rejects_traversal_links_duplicates_and_extra_files(self):
        for name in ('../escape', '/absolute', 'debian12/../escape', 'debian12/extra', 'debian12/SHA256SUMS'):
            with self.subTest(name=name):
                info = tarfile.TarInfo(name)
                info.size = 1
                with self.assertRaises(RuntimeError):
                    release.verify_archive(self.archive(extra=info), 'debian12', self.commit)
        info = tarfile.TarInfo('debian12/link')
        info.type = tarfile.SYMTYPE
        info.linkname = '/outside'
        with self.assertRaises(RuntimeError):
            release.verify_archive(self.archive(extra=info), 'debian12', self.commit)

    def test_assembler_requires_all_five_targets(self):
        incoming = self.root / 'incoming'
        incoming.mkdir()
        with patch('nrpe_cli.release.workflow_identity', return_value=self.identity):
            with self.assertRaisesRegex(RuntimeError, 'five'):
                release.assemble(self.root, incoming, self.commit, self.root / 'final')
        self.assertFalse((self.root / 'final').exists())
