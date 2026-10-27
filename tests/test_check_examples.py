"""Exercise the optional Linux wrapper using a disposable fake plugin."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


@unittest.skipIf(os.name == 'nt', 'POSIX deployment wrapper; tested by the Linux CI job')
class CheckExampleTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='nrpe example ')
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.plugin = self.root / 'check_load'
        self.plugin.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\nexit 1\n')
        self.plugin.chmod(0o755)
        self.wrapper = Path(__file__).resolve().parents[1] / 'examples/check-load-profile.sh'

    def run_wrapper(self, *arguments):
        return subprocess.run(['sh', str(self.wrapper), *map(str, arguments)],
                              text=True, capture_output=True, check=False)

    def test_maps_only_named_profiles_to_fixed_thresholds_and_preserves_plugin_status(self):
        for profile, warning, critical in [('standard', '5,4,3', '10,8,6'),
                                            ('busy', '10,8,6', '20,16,12')]:
            with self.subTest(profile=profile):
                result = self.run_wrapper(self.plugin, profile)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout.splitlines(), ['-w', warning, '-c', critical])

    def test_rejects_unknown_profiles_extra_arguments_and_shell_syntax(self):
        marker = self.root / 'unexpected'
        for arguments in [(self.plugin, 'unknown'), (self.plugin, 'standard', 'extra'),
                          (self.plugin, 'standard; touch ' + str(marker)),
                          (self.plugin, '$(touch ' + str(marker) + ')'),
                          (self.plugin, "standard'"), (), (self.plugin,)]:
            with self.subTest(arguments=arguments):
                result = self.run_wrapper(*arguments)
                self.assertEqual(result.returncode, 3)
                self.assertTrue(result.stdout.startswith('UNKNOWN:'))
                self.assertFalse(marker.exists())

    def test_rejects_relative_or_missing_plugin_path(self):
        for plugin in ['check_load', self.root / 'missing-plugin']:
            with self.subTest(plugin=plugin):
                self.assertEqual(self.run_wrapper(plugin, 'standard').returncode, 3)
