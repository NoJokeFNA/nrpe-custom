import contextlib
import io
import subprocess
import unittest
from unittest.mock import patch

import build
from nrpe_cli.docker import check_docker


class DockerReadinessTests(unittest.TestCase):
    @patch('nrpe_cli.docker.platform.system', return_value='Windows')
    @patch('nrpe_cli.docker.shutil.which', return_value=None)
    @patch('nrpe_cli.docker.subprocess.run')
    def test_missing_cli(self, run, which, system):
        with self.assertRaisesRegex(RuntimeError, 'Install Docker Desktop'):
            check_docker()
        run.assert_not_called()

    @patch('nrpe_cli.docker.platform.system', return_value='Windows')
    @patch('nrpe_cli.docker.shutil.which', return_value='docker')
    @patch('nrpe_cli.docker.subprocess.run')
    def test_stopped_engine(self, run, which, system):
        run.return_value = subprocess.CompletedProcess([], 1, '', 'Pipe not found')
        with self.assertRaisesRegex(RuntimeError, '(?s)Pipe not found.*Start Docker Desktop'):
            check_docker()
        self.assertEqual(run.call_count, 1)

    @patch('nrpe_cli.docker.platform.system', return_value='Windows')
    @patch('nrpe_cli.docker.shutil.which', return_value='docker')
    @patch('nrpe_cli.docker.subprocess.run', side_effect=subprocess.TimeoutExpired('docker', 15))
    def test_timeout(self, run, which, system):
        with self.assertRaisesRegex(RuntimeError, '(?s)15 seconds.*Start Docker Desktop'):
            check_docker()

    @patch('nrpe_cli.docker.shutil.which', return_value='docker')
    @patch('nrpe_cli.docker.subprocess.run')
    def test_windows_engine_rejected(self, run, which):
        run.return_value = subprocess.CompletedProcess([], 0, 'windows\n', '')
        with self.assertRaisesRegex(RuntimeError, 'Linux containers are required'):
            check_docker()

    @patch('nrpe_cli.docker.shutil.which', return_value='docker')
    @patch('nrpe_cli.docker.subprocess.run')
    def test_compose_required(self, run, which):
        run.side_effect = [subprocess.CompletedProcess([], 0, 'linux\n', ''),
                           subprocess.CompletedProcess([], 1, '', 'missing')]
        with self.assertRaisesRegex(RuntimeError, 'Compose v2 is unavailable'):
            check_docker()

    @patch('nrpe_cli.docker.platform.system', return_value='Linux')
    @patch('nrpe_cli.docker.shutil.which', return_value='docker')
    @patch('nrpe_cli.docker.subprocess.run')
    def test_linux_permissions_hint(self, run, which, system):
        run.return_value = subprocess.CompletedProcess([], 1, '', 'Permission denied')
        with self.assertRaisesRegex(RuntimeError, 'access permissions'):
            check_docker()


class CompatibilityTests(unittest.TestCase):
    @patch('build.controller_main', return_value=7)
    def test_previous_commands_map_to_new_actions(self, main):
        for options, expected in [([], 'build'), (['--test'], 'verify'), (['--test-only'], 'test')]:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(build.main(['debian12', *options]), 7)
            main.assert_called_with([expected, 'debian12'])
