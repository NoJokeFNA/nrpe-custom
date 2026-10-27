import contextlib
import hashlib
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from fetch_sles_packages import fetch_packages


class SusePackageTests(unittest.TestCase):
    def manifest(self):
        data = b'fake RPM for orchestration tests'
        return {'packages': [{'file': 'example.rpm', 'name': 'example', 'version_release': '1-2',
                              'arch': 'noarch', 'vendor': 'SUSE LLC', 'signature_key': '39db7c82',
                              'roles': ['build'], 'url': 'https://api.opensuse.org/public/build/example.rpm',
                              'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()}]}

    @patch('fetch_sles_packages.subprocess.check_output')
    @patch('fetch_sles_packages.urllib.request.urlopen')
    def test_signature_and_identity_must_pass_after_checksum(self, open_url, check):
        open_url.return_value = io.BytesIO(b'fake RPM for orchestration tests')
        check.side_effect = [b'Header V3 RSA/SHA256 Signature, key ID 39db7c82: OK',
                             b'example 1-2 noarch|SUSE LLC']
        with tempfile.TemporaryDirectory() as temporary, contextlib.redirect_stdout(io.StringIO()):
            directory = Path(temporary)
            fetch_packages(self.manifest(), directory, 'build')
            self.assertTrue((directory / 'example.rpm').is_file())
        self.assertEqual(check.call_count, 2)

    @patch('fetch_sles_packages.subprocess.check_output')
    @patch('fetch_sles_packages.urllib.request.urlopen')
    def test_corrupt_download_is_rejected_before_signature_tool(self, open_url, check):
        open_url.return_value = io.BytesIO(b'corrupt')
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            with self.assertRaisesRegex(ValueError, 'checksum'):
                fetch_packages(self.manifest(), directory, 'build')
            self.assertFalse((directory / 'example.rpm').exists())
        check.assert_not_called()

    @patch('fetch_sles_packages.subprocess.check_output', return_value=b'Payload digest: OK')
    @patch('fetch_sles_packages.urllib.request.urlopen')
    def test_digest_only_success_is_not_a_valid_suse_signature(self, open_url, check):
        open_url.return_value = io.BytesIO(b'fake RPM for orchestration tests')
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            with self.assertRaisesRegex(ValueError, 'signature'):
                fetch_packages(self.manifest(), directory, 'build')
            self.assertFalse((directory / 'example.rpm').exists())

    @patch('fetch_sles_packages.subprocess.check_output')
    @patch('fetch_sles_packages.urllib.request.urlopen')
    def test_rpm_verification_failure_removes_rejected_file(self, open_url, check):
        open_url.return_value = io.BytesIO(b'fake RPM for orchestration tests')
        check.side_effect = subprocess.CalledProcessError(1, 'rpmkeys')
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            with self.assertRaises(subprocess.CalledProcessError):
                fetch_packages(self.manifest(), directory, 'build')
            self.assertFalse((directory / 'example.rpm').exists())

    @patch('fetch_sles_packages.urllib.request.urlopen')
    def test_build_only_package_is_not_downloaded_for_runtime(self, open_url):
        with tempfile.TemporaryDirectory() as temporary:
            fetch_packages(self.manifest(), Path(temporary), 'runtime')
        open_url.assert_not_called()

    def test_plain_http_is_not_accepted(self):
        manifest = self.manifest()
        manifest['packages'][0]['url'] = 'http://api.opensuse.org/example.rpm'
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, 'HTTPS'):
                fetch_packages(manifest, Path(temporary), 'build')


if __name__ == '__main__':
    unittest.main()
