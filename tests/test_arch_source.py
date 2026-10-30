"""Optional Arch inputs, source identity and release rejection behavior."""
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from scripts import arch_source
from nrpe_cli.targets import DEFAULT_TARGETS, TARGETS


def tar_bytes(entries):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode='w:gz') as archive:
        for name, data in entries.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return output.getvalue()


class ArchSourceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.recipe = self.root / 'packaging/archlinux'
        self.recipe.mkdir(parents=True)
        self.directory = self.root / 'output/archlinux'
        self.directory.mkdir(parents=True)
        self.licenses = {'LICENSE.md': b'license text', 'LEGAL': b'upstream notice'}
        upstream = tar_bytes({'nrpe-4.2.0/' + n: b for n, b in self.licenses.items()})
        self.manifest = {'version': '4.2.0', 'pkgrel': '1.1', 'archive': 'nrpe-4.2.0.tar.gz',
                         'url': 'https://example.invalid/archive',
                         'sha256': hashlib.sha256(upstream).hexdigest(),
                         'licenses': {n: hashlib.sha256(b).hexdigest() for n, b in self.licenses.items()}}
        for path in (self.root / 'packaging/archlinux-source.json', self.directory / 'source-manifest.json'):
            path.write_text(json.dumps(self.manifest))
        self.entries = {'nrpe/' + n: n.encode() for n in ('PKGBUILD', 'nrpe.service', 'nrpe.sysusers', 'ARGUMENT-POLICY.md', 'nrpe.install')}
        for name, data in self.entries.items():
            (self.recipe / Path(name).name).write_bytes(data)
            path = self.directory / 'build-recipe' / Path(name).name
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(data)
        (self.directory / 'ARGUMENT-POLICY.md').write_bytes(self.entries['nrpe/ARGUMENT-POLICY.md'])
        self.entries.update({'nrpe/nrpe-4.2.0.tar.gz': upstream, 'nrpe/.SRCINFO': b'pkgver = 4.2.0'})
        self.source = self.directory / 'sources/nrpe-4.2.0-1.1.src.tar.gz'
        self.source.parent.mkdir()
        self.source.write_bytes(tar_bytes(self.entries))
        self.evidence = {'artifact': {'file': 'nrpe-4.2.0-1.1-x86_64.pkg.tar.zst', 'version': '4.2.0-1.1'}}
        self.notices = self.root / 'notices'
        self.notices.mkdir()

    def validate(self, metadata='pkgname = nrpe\npkgver = 4.2.0-1.1\narch = x86_64\n'):
        with patch.object(arch_source.subprocess, 'check_output', side_effect=lambda command, **kwargs: metadata if command[-1] == '.PKGINFO' else b'nrpe.install'):
            return arch_source.validate_export(self.root, self.directory, self.evidence, self.notices)

    def test_arch_is_available_but_never_part_of_default_selection(self):
        self.assertIn('archlinux', TARGETS)
        self.assertNotIn('archlinux', DEFAULT_TARGETS)
        self.assertEqual(len(DEFAULT_TARGETS), 5)

    def test_current_reviewed_sources_export_licenses_and_exact_asset_set(self):
        allowed = self.validate()
        self.assertEqual(len(allowed), 10)
        self.assertIn('ARGUMENT-POLICY.md', allowed)
        for name, content in self.licenses.items():
            self.assertEqual((self.notices / 'archlinux' / name).read_bytes(), content)

    def test_binary_version_cannot_be_manufactured_by_renaming(self):
        with self.assertRaisesRegex(RuntimeError, 'metadata mismatch'):
            self.validate('pkgname = nrpe\npkgver = 4.1.2-1\narch = x86_64\n')

    def test_corresponding_upstream_archive_tampering_is_rejected(self):
        self.entries['nrpe/nrpe-4.2.0.tar.gz'] = b'unreviewed source'
        self.source.write_bytes(tar_bytes(self.entries))
        with self.assertRaisesRegex(RuntimeError, 'source changed'):
            self.validate()

    def test_security_notice_cannot_be_removed_or_changed(self):
        (self.directory / 'ARGUMENT-POLICY.md').write_bytes(b'arguments are safe')
        with self.assertRaisesRegex(RuntimeError, 'policy notice changed'):
            self.validate()

    def test_replaced_recipe_is_rejected(self):
        self.entries['nrpe/PKGBUILD'] = b'enable unsafe substitutions'
        self.source.write_bytes(tar_bytes(self.entries))
        with self.assertRaisesRegex(RuntimeError, 'recipe changed'):
            self.validate()

    def test_unreviewed_latest_release_fails_before_creating_destination(self):
        destination = self.root / 'new-source'
        with patch.object(arch_source, 'fetch', return_value=b'{"tag_name":"nrpe-4.3.0"}'):
            with self.assertRaisesRegex(RuntimeError, 'requires source, license'):
                arch_source.prepare(self.root, destination)
        self.assertFalse(destination.exists())

    def test_source_download_checksum_mismatch_fails_closed(self):
        destination = self.root / 'new-source'
        release = b'{"tag_name":"nrpe-4.2.0","draft":false,"prerelease":false}'
        with patch.object(arch_source, 'fetch', side_effect=[release, b'wrong archive']):
            with self.assertRaisesRegex(RuntimeError, 'checksum mismatch'):
                arch_source.prepare(self.root, destination)
        self.assertFalse(destination.exists())

    def test_unsafe_source_archive_member_is_rejected(self):
        self.source.write_bytes(tar_bytes({'../outside': b'data'}))
        with self.assertRaisesRegex(RuntimeError, 'Unsafe'):
            arch_source.checked_members(self.source)
