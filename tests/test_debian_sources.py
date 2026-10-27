"""Reject incomplete or mismatched corresponding-source exports."""

import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from export_debian_sources import export_sources


class DebianSourceTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.destination = self.root / 'export'
        self.version = '4.1.3-1+withargs1'
        self.description = self.root / ('nagios-nrpe_' + self.version + '.dsc')
        self.assets = {
            'nagios-nrpe_4.1.3.orig.tar.gz': b'upstream source fixture',
            'nagios-nrpe_' + self.version + '.debian.tar.xz': b'custom packaging fixture',
        }
        for name, data in self.assets.items():
            (self.root / name).write_bytes(data)
        self.write_description()

    def write_description(self, entries=None, version=None):
        if entries is None:
            entries = [(hashlib.sha256(data).hexdigest(), len(data), name)
                       for name, data in self.assets.items()]
        text = 'Format: 3.0 (quilt)\nSource: nagios-nrpe\nVersion: {}\nChecksums-Sha256:\n'.format(
            version or self.version)
        text += ''.join(' {} {} {}\n'.format(*entry) for entry in entries)
        self.description.write_text(text)

    def test_exports_description_and_all_matching_sources_with_checksums(self):
        export_sources(self.description, self.destination, self.version)
        expected = dict(self.assets, **{self.description.name: self.description.read_bytes()})
        checksums = (self.destination / 'SHA256SUMS').read_text().splitlines()
        self.assertEqual(len(checksums), len(expected))
        for name, data in expected.items():
            self.assertEqual((self.destination / name).read_bytes(), data)
            self.assertIn(hashlib.sha256(data).hexdigest() + '  ' + name, checksums)

    def test_rejects_mismatched_version_before_export(self):
        self.write_description(version='4.1.3-1')
        with self.assertRaisesRegex(ValueError, 'identity'):
            export_sources(self.description, self.destination, self.version)
        self.assertFalse(self.destination.exists())

    def test_missing_or_corrupt_source_does_not_replace_existing_export(self):
        self.destination.mkdir()
        previous = self.destination / 'previous.dsc'
        previous.write_text('previous valid export')
        upstream = self.root / next(iter(self.assets))
        upstream.write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            export_sources(self.description, self.destination, self.version)
        self.assertEqual(previous.read_text(), 'previous valid export')
        upstream.unlink()
        with self.assertRaisesRegex(ValueError, 'missing'):
            export_sources(self.description, self.destination, self.version)

    def test_rejects_unsafe_paths_duplicates_and_missing_packaging(self):
        digest = hashlib.sha256(b'data').hexdigest()
        for name in ('../outside.tar.gz', r'..\outside.tar.gz', '/outside.tar.gz'):
            with self.subTest(name=name):
                self.write_description(entries=[(digest, 4, name)])
                with self.assertRaisesRegex(ValueError, 'unsafe'):
                    export_sources(self.description, self.destination, self.version)
                self.assertFalse(self.destination.exists())
        name, data = next(iter(self.assets.items()))
        entry = (hashlib.sha256(data).hexdigest(), len(data), name)
        self.write_description(entries=[entry, entry])
        with self.assertRaisesRegex(ValueError, 'unsafe'):
            export_sources(self.description, self.destination, self.version)
        self.write_description(entries=[entry])
        with self.assertRaisesRegex(ValueError, 'packaging archive'):
            export_sources(self.description, self.destination, self.version)
