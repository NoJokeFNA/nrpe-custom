import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from sles_source import fetch_sources, patch_spec
from nrpe_cli.state import artifact


SPEC = '''Name: nrpe
Version: 4.1.1
Release: 0
Requires: system-user-nagios
%build
%configure \\
    --with-dist-type=suse \\
    --enable-command-args \\
    --enable-bash-command-substitution \\
    --enable-ssl
make all
%install
make install
%files
/etc/nrpe.cfg
%changelog
'''


class SlesSourceTests(unittest.TestCase):
    def test_changes_only_release_and_unsafe_build_flag(self):
        result = patch_spec(SPEC, '4.1.1', '0.withargs1')
        expected = SPEC.replace('Release: 0', 'Release:        0.withargs1')
        expected = expected.replace('    --enable-bash-command-substitution \\\n', '')
        self.assertEqual(result, expected)
        self.assertEqual(result.count('--enable-command-args'), 1)

    def test_unknown_recipe_or_version_fails_closed(self):
        for text in [SPEC.replace('Version: 4.1.1', 'Version: 4.2.0'),
                     SPEC.replace('%build', '%build_missing'),
                     SPEC.replace('--enable-command-args', '--disable-command-args'),
                     SPEC.replace('--enable-ssl', '--enable-bash-command-substitution')]:
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    patch_spec(text, '4.1.1', '0.withargs1')

    def test_custom_release_cannot_inject_spec_content(self):
        with self.assertRaises(ValueError):
            patch_spec(SPEC, '4.1.1', '1\n%post\nmalicious')

    def manifest(self):
        data = SPEC.encode()
        return {'project': 'server:monitoring', 'package': 'nrpe', 'revision': 'pinned',
                'version': '4.1.1', 'custom_release': '0.withargs1',
                'files': {'nrpe.spec': {'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()}}}

    def test_fetch_verifies_checksum_before_patching(self):
        calls = []
        def opener(url, timeout):
            calls.append(url)
            return io.BytesIO(SPEC.encode())
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary)
            fetch_sources(self.manifest(), destination, opener)
            result = (destination / 'nrpe.spec').read_text()
            self.assertNotIn('--enable-bash-command-substitution', result)
            self.assertIn('0.withargs1', result)
        self.assertIn('rev=pinned', calls[0])

    def test_corrupt_source_is_not_written(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary)
            with self.assertRaisesRegex(ValueError, 'checksum'):
                fetch_sources(self.manifest(), destination, lambda *args, **kwargs: io.BytesIO(b'corrupt'))
            self.assertFalse((destination / 'nrpe.spec').exists())

    def test_originals_keep_unmodified_recipe_for_release_provenance(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fetch_sources(self.manifest(), root / 'build', lambda *a, **k: io.BytesIO(SPEC.encode()),
                          originals=root / 'originals')
            self.assertEqual((root / 'originals/nrpe.spec').read_text(), SPEC)
            self.assertNotIn('--enable-bash-command-substitution', (root / 'build/nrpe.spec').read_text())

    def test_source_manifest_cannot_escape_destination(self):
        manifest = self.manifest()
        manifest['files']['../nrpe.spec'] = manifest['files'].pop('nrpe.spec')
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, 'Unsafe'):
                fetch_sources(manifest, Path(temporary))

    def test_pinned_source_manifest_describes_known_version(self):
        path = Path(__file__).resolve().parents[1] / 'packaging/sles12sp3-source.json'
        manifest = json.loads(path.read_text())
        self.assertEqual(manifest['version'], '4.1.1')
        self.assertIn('nrpe-4.1.1.tar.xz', manifest['files'])
        self.assertEqual(len(manifest['files']['nrpe.spec']['sha256']), 64)

    def test_rpm_artifact_detection_ignores_source_and_debug_rpms(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / 'output/sles12sp3'
            directory.mkdir(parents=True)
            name = 'nrpe-4.1.1-0.withargs1.x86_64.rpm'
            data = b'test artifact'
            (directory / name).write_bytes(data)
            (directory / 'nrpe-debuginfo-4.1.1.x86_64.rpm').touch()
            (directory / 'nrpe-4.1.1.src.rpm').touch()
            (directory / 'SHA256SUMS').write_text(hashlib.sha256(data).hexdigest() + '  ' + name + '\n')
            helper = 'system-user-nagios-1.0.0-0.noarch.rpm'
            (directory / helper).write_bytes(b'user package')
            with (directory / 'SHA256SUMS').open('a') as checksums:
                checksums.write(hashlib.sha256(b'user package').hexdigest() + '  ' + helper + '\n')
            client = 'monitoring-plugins-nrpe-4.1.1-0.withargs1.x86_64.rpm'
            (directory / client).write_bytes(b'client package')
            with (directory / 'SHA256SUMS').open('a') as checksums:
                checksums.write(hashlib.sha256(b'client package').hexdigest() + '  ' + client + '\n')
            result = artifact(root, 'sles12sp3')
            self.assertEqual(result['file'], name)
            self.assertEqual(result['version'], '4.1.1-0.withargs1')


if __name__ == '__main__':
    unittest.main()
