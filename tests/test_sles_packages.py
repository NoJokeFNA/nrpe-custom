"""Input downloads validate size/hash; native verification owns RPM trust checks."""

import hashlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from fetch_sles_packages import download_packages


class SusePackageTests(unittest.TestCase):
    DATA = b'fake RPM for orchestration tests'

    def manifest(self):
        return {'packages': [{'file': 'example.rpm', 'roles': ['build'],
                              'url': 'https://api.opensuse.org/public/build/example.rpm',
                              'size': len(self.DATA), 'sha256': hashlib.sha256(self.DATA).hexdigest()}]}

    @patch('fetch_sles_packages.urllib.request.urlopen')
    def test_validated_download_preserves_bytes_and_metadata(self, open_url):
        open_url.return_value = io.BytesIO(self.DATA)
        manifest = self.manifest()
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            result = list(download_packages(manifest, directory, 'build'))
            self.assertEqual(result, [(manifest['packages'][0], directory / 'example.rpm')])
            self.assertEqual(result[0][1].read_bytes(), self.DATA)

    @patch('fetch_sles_packages.urllib.request.urlopen')
    def test_corrupt_short_or_oversized_download_is_rejected_before_export(self, open_url):
        for data in (b'corrupt', self.DATA[:-1], self.DATA + b'extra'):
            open_url.return_value = io.BytesIO(data)
            with self.subTest(data=data), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                with self.assertRaisesRegex(ValueError, 'checksum'):
                    list(download_packages(self.manifest(), directory, 'build'))
                self.assertFalse((directory / 'example.rpm').exists())

    @patch('fetch_sles_packages.urllib.request.urlopen')
    def test_build_only_package_is_not_downloaded_for_runtime(self, open_url):
        with tempfile.TemporaryDirectory() as temporary:
            self.assertEqual(list(download_packages(self.manifest(), Path(temporary), 'runtime')), [])
        open_url.assert_not_called()

    @patch('fetch_sles_packages.urllib.request.urlopen')
    def test_untrusted_urls_are_rejected_before_network_access(self, open_url):
        for url in ('http://api.opensuse.org/example.rpm', 'https://other.invalid/example.rpm',
                    'https://user:password@api.opensuse.org/example.rpm'):
            manifest = self.manifest()
            manifest['packages'][0]['url'] = url
            with self.subTest(url=url), tempfile.TemporaryDirectory() as temporary:
                with self.assertRaisesRegex(ValueError, 'HTTPS'):
                    list(download_packages(manifest, Path(temporary), 'build'))
        open_url.assert_not_called()

    @patch('fetch_sles_packages.urllib.request.urlopen')
    def test_unsafe_filenames_are_rejected_before_network_access(self, open_url):
        for name in ('../outside.rpm', '/outside.rpm', 'bad\\path.rpm', '--option.rpm'):
            manifest = self.manifest()
            manifest['packages'][0]['file'] = name
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                with self.assertRaisesRegex(ValueError, 'filename'):
                    list(download_packages(manifest, Path(temporary), 'build'))
        open_url.assert_not_called()

    @patch('fetch_sles_packages.urllib.request.urlopen')
    def test_duplicate_filename_cannot_overwrite_a_validated_download(self, open_url):
        open_url.return_value = io.BytesIO(self.DATA)
        manifest = self.manifest()
        manifest['packages'] *= 2
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            with self.assertRaisesRegex(ValueError, 'filename'):
                list(download_packages(manifest, directory, 'build'))
            self.assertEqual((directory / 'example.rpm').read_bytes(), self.DATA)
        self.assertEqual(open_url.call_count, 1)
