import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from enable_command_args import patch_rules

RULES = """#!/usr/bin/make -f
%:
\tdh $@

override_dh_auto_configure:
\tdh_auto_configure -- \\
\t\t--prefix=/usr \\
\t\t--enable-ssl \\
\t\t--with-logdir=/var/log

override_dh_auto_build:
\tdh_auto_build -- all
"""


class RulesPatchTests(unittest.TestCase):
    def test_inserts_flag_once_in_correct_position(self):
        result = patch_rules(RULES)
        self.assertIn("\t\t--enable-ssl \\\n\t\t--enable-command-args \\\n\t\t--with-logdir=", result)
        self.assertEqual(result.count("--enable-command-args"), 1)
        self.assertEqual(result.replace("\t\t--enable-command-args \\\n", ""), RULES)

    def test_refuses_missing_target(self):
        with self.assertRaises(ValueError):
            patch_rules(RULES.replace("override_dh_auto_configure:", "override_missing:"))

    def test_refuses_unrecognized_structure(self):
        with self.assertRaises(ValueError):
            patch_rules(RULES.replace("--enable-ssl", "--disable-ssl"))

    def test_refuses_double_patch(self):
        with self.assertRaises(ValueError):
            patch_rules(patch_rules(RULES))

    def test_refuses_bash_substitution(self):
        with self.assertRaises(ValueError):
            patch_rules(RULES.replace("--prefix=/usr", "--enable-bash-command-substitution"))


if __name__ == "__main__":
    unittest.main()
