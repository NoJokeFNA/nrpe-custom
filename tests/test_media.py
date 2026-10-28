import contextlib
import io
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from nrpe_cli import cli, controller, state
from nrpe_cli.media import validate_media


class MediaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='nrpe media ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def medium(self, label='SUSE Linux Enterprise 15 SP3 x86_64'):
        (self.root / 'Media.1').mkdir()
        (self.root / 'Media.1/media').write_text(label + '\n')
        repository = self.root / 'Module-Basesystem/repodata'
        repository.mkdir(parents=True)
        (repository / 'repomd.xml').write_text('<repomd/>')
        # Layout tests check signature presence. Actual authenticity is checked
        # by zypper in the container, not by these synthetic unit-test files.
        (repository / 'repomd.xml.asc').write_text('test signature placeholder')
        return repository

    def test_accepts_signed_repository_layout_with_spaces_in_path(self):
        self.medium()
        self.assertEqual(validate_media(self.root), self.root.resolve())

    def test_rejects_wrong_service_pack(self):
        self.medium()
        metadata = self.root / 'Media.1/media'
        for service_pack in (2, 4, 5, 7):
            with self.subTest(service_pack=service_pack):
                metadata.write_text('SUSE Linux Enterprise 15 SP' + str(service_pack) + ' x86_64')
                with self.assertRaisesRegex(RuntimeError, '15 SP3'):
                    validate_media(self.root)

    def test_rejects_leap_even_with_a_matching_version_number(self):
        self.medium('openSUSE Leap 15.3')
        with self.assertRaises(RuntimeError):
            validate_media(self.root)

    def test_rejects_missing_signature(self):
        repository = self.medium()
        (repository / 'repomd.xml.asc').unlink()
        with self.assertRaisesRegex(RuntimeError, 'signature'):
            validate_media(self.root)

    def test_online_installer_without_package_repositories_is_rejected(self):
        (self.root / 'Media.1').mkdir()
        (self.root / 'Media.1/media').write_text('SUSE Linux Enterprise 15 SP3 x86_64')
        with self.assertRaisesRegex(RuntimeError, 'Full Media1'):
            validate_media(self.root)

    def test_non_x86_medium_is_rejected(self):
        self.medium('SUSE Linux Enterprise 15 SP3 aarch64')
        with self.assertRaisesRegex(RuntimeError, 'x86_64'):
            validate_media(self.root)

    def test_iso_file_requires_extraction(self):
        path = self.root / 'SLES.iso'
        path.touch()
        with self.assertRaisesRegex(RuntimeError, 'extracted directory'):
            validate_media(path)

    def test_metadata_symlink_cannot_escape_media_directory(self):
        self.medium()
        outside = self.root.parent / (self.root.name + '-outside')
        outside.write_text('SUSE Linux Enterprise 15 SP3')
        self.addCleanup(outside.unlink)
        metadata = self.root / 'Media.1/media'
        metadata.unlink()
        try:
            metadata.symlink_to(outside)
        except PermissionError:
            if os.name == 'nt':
                self.skipTest('Windows requires Developer Mode or administrator rights to create symlinks')
            raise
        with self.assertRaisesRegex(RuntimeError, 'symlink'):
            validate_media(self.root)

    @patch('nrpe_cli.cli.execute', return_value=0)
    def test_cli_passes_validated_media_to_sles_controller(self, execute):
        self.medium()
        with contextlib.redirect_stdout(io.StringIO()):
            code = cli.main(['verify', 'sles15sp3', '--sles-media', str(self.root)], root=self.root)
        self.assertEqual(code, 0)
        self.assertEqual(execute.call_args.kwargs['media'], self.root.resolve())

    @patch('nrpe_cli.cli.execute')
    def test_invalid_media_fails_before_docker_work(self, execute):
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            code = cli.main(['verify', 'sles15sp3', '--sles-media', str(self.root)])
        self.assertEqual(code, 1)
        execute.assert_not_called()

    @patch('nrpe_cli.controller.subprocess.Popen')
    @patch('nrpe_cli.controller.subprocess.run')
    def test_media_path_is_passed_as_environment_not_shell_code(self, run, popen):
        process = MagicMock()
        process.stdout = io.StringIO('done\n')
        process.wait.return_value = 0
        process.poll.return_value = 0
        popen.return_value = process
        run.return_value = subprocess.CompletedProcess([], 0, '', '')
        with state.target_lock(self.root, 'sles15sp3', 'media') as lock:
            with contextlib.redirect_stdout(io.StringIO()):
                code = controller.run_phase('docker', self.root, 'media', 'sles15sp3',
                                             'build', io.StringIO(), lock, media=self.root)
        self.assertEqual(code, 0)
        self.assertEqual(popen.call_args.kwargs['env']['SLES_MEDIA_DIR'], str(self.root))
        self.assertNotIn('shell', popen.call_args.kwargs)


if __name__ == '__main__':
    unittest.main()
