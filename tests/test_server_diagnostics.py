"""Server inventory reads configuration without executing configured commands."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('bash') and os.name != 'nt', 'Target-server script requires Linux shell tools')
class ServerDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.config = self.root / 'nrpe.cfg'
        self.executable('nrpe', 'echo "Version: 4.1.1"\nexit 3')
        self.executable('systemctl', 'case "$1" in show) echo nagios;; esac\nexit 0')
        self.executable('rpm', 'echo nrpe-4.1.1-custom')
        self.executable('runuser', 'exit 0')
        self.executable('ss', 'echo "LISTEN 0 5 *:5666 *:*"')

    def executable(self, name, body):
        path = self.bin / name
        path.write_text('#!/bin/sh\n' + body + '\n')
        path.chmod(0o755)
        return path

    def run_script(self, *arguments):
        return subprocess.run(['bash', str(ROOT / 'scripts/diagnose-server.sh'),
                               '--config', str(self.config), '--nrpe', str(self.bin / 'nrpe'),
                               '--unit', 'nrpe.service', *arguments],
                              env=dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ['PATH']),
                              text=True, capture_output=True, timeout=15)

    def test_existing_plugins_and_recursive_includes_are_read_but_never_executed(self):
        marker = self.root / 'plugin-was-executed'
        plugin = self.executable('check_load', 'touch "' + str(marker) + '"')
        included = self.root / 'commands.cfg'
        included.write_text(f'include={self.config}\ncommand[check_load]={plugin} -w $ARG1$\n')
        self.config.write_text(f'include={included}\nallowed_hosts=192.0.2.10\n#ssl_version=TLSv1.2\n')
        result = self.run_script('--monitor-ip', '192.0.2.10')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(marker.exists())
        self.assertEqual(result.stdout.count('READ:'), 2)
        self.assertIn('NRPE Version: 4.1.1', result.stdout)
        self.assertIn('explicitly listed', result.stdout)
        self.assertIn('Commented TLS directives use daemon defaults', result.stdout)
        self.assertNotIn('SETTING: ssl_version', result.stdout)

    def test_missing_swap_and_ntp_plugins_fail_without_printing_command_secrets(self):
        self.config.write_text(f'command[check_swap]={self.bin}/missing_swap -a secret-password\n'
                               f'command[check_ntp_time]={self.bin}/missing_ntp\n')
        result = self.run_script()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('Command check_swap: executable missing', result.stdout)
        self.assertIn('Command check_ntp_time: executable missing', result.stdout)
        self.assertNotIn('secret-password', result.stdout)

    def test_shell_substitutions_in_configuration_are_not_executed(self):
        marker = self.root / 'config-was-executed'
        self.config.write_text(f'command[unsafe]=$(touch {marker})\n'
                               f'password=$(touch {marker})\n')
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(marker.exists())
        self.assertIn('complex/quoted executable', result.stdout)
        self.assertNotIn('touch', result.stdout)

    def test_missing_configuration_and_inactive_service_are_reported_as_failures(self):
        self.executable('systemctl', 'exit 3')
        result = self.run_script()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('Managed service is not active', result.stdout)
        self.assertIn('Configuration not readable', result.stdout)

    def test_invalid_options_do_not_start_inspection(self):
        result = self.run_script('--unit', '--bad')
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('OS:', result.stdout)
