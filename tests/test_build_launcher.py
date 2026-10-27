import contextlib
import io
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build


class BuildLauncherTests(unittest.TestCase):
    def run_main(self, target):
        with contextlib.redirect_stderr(io.StringIO()) as errors:
            with contextlib.redirect_stdout(io.StringIO()):
                status = build.main([target])
        return status, errors.getvalue()

    @patch("build.platform.system", return_value="Windows")
    @patch("build.shutil.which", return_value=None)
    @patch("build.subprocess.run")
    def test_missing_cli_explains_installation_without_starting_build(self, run, which, system):
        status, errors = self.run_main("debian12")
        self.assertEqual(status, 1)
        self.assertIn("Install Docker Desktop", errors)
        run.assert_not_called()

    @patch("build.platform.system", return_value="Windows")
    @patch("build.shutil.which", return_value="docker")
    @patch("build.subprocess.run")
    def test_stopped_engine_explains_desktop_and_preserves_diagnostic(self, run, which, system):
        run.return_value = subprocess.CompletedProcess([], 1, "", "Pipe not found")
        status, errors = self.run_main("debian12")
        self.assertEqual(status, 1)
        self.assertIn("Start Docker Desktop", errors)
        self.assertIn("Pipe not found", errors)
        self.assertEqual(run.call_count, 1)

    @patch("build.platform.system", return_value="Windows")
    @patch("build.shutil.which", return_value="docker")
    @patch("build.subprocess.run", side_effect=subprocess.TimeoutExpired("docker", 15))
    def test_unresponsive_engine_does_not_start_build(self, run, which, system):
        status, errors = self.run_main("all")
        self.assertEqual(status, 1)
        self.assertIn("15 seconds", errors)
        self.assertIn("Start Docker Desktop", errors)
        self.assertEqual(run.call_count, 1)

    @patch("build.shutil.which", return_value="docker")
    @patch("build.subprocess.run")
    def test_windows_container_engine_is_rejected(self, run, which):
        run.return_value = subprocess.CompletedProcess([], 0, "windows\n", "")
        status, errors = self.run_main("debian12")
        self.assertEqual(status, 1)
        self.assertIn("Linux containers are required", errors)
        self.assertEqual(run.call_count, 1)

    @patch("build.shutil.which", return_value="docker")
    @patch("build.subprocess.run")
    def test_missing_compose_does_not_start_build(self, run, which):
        run.side_effect = [
            subprocess.CompletedProcess([], 0, "linux\n", ""),
            subprocess.CompletedProcess([], 1, "", "missing compose"),
        ]
        status, errors = self.run_main("debian12")
        self.assertEqual(status, 1)
        self.assertIn("Docker Compose v2 is unavailable", errors)
        self.assertEqual(run.call_count, 2)

    @patch("build.check_docker", return_value="docker")
    @patch("build.subprocess.run")
    def test_all_builds_run_in_project_root(self, run, check):
        run.return_value = subprocess.CompletedProcess([], 0)
        status, errors = self.run_main("all")
        self.assertEqual(status, 0)
        self.assertEqual(errors, "")
        self.assertEqual(
            [call.args[0][-1] for call in run.call_args_list], list(build.TARGETS)
        )
        for call in run.call_args_list:
            self.assertEqual(call.kwargs["cwd"], build.ROOT)
            self.assertEqual(call.args[0][1:5], ["compose", "run", "--rm", "--build"])

    @patch("build.check_docker", return_value="docker")
    @patch("build.subprocess.run")
    def test_first_build_failure_stops_all_and_preserves_exit_code(self, run, check):
        run.return_value = subprocess.CompletedProcess([], 42)
        status, errors = self.run_main("all")
        self.assertEqual(status, 42)
        self.assertEqual(run.call_count, 1)

    @patch("build.platform.system", return_value="Linux")
    @patch("build.shutil.which", return_value="docker")
    @patch("build.subprocess.run")
    def test_linux_connection_error_has_platform_appropriate_guidance(self, run, which, system):
        run.return_value = subprocess.CompletedProcess([], 1, "", "Permission denied")
        status, errors = self.run_main("debian13")
        self.assertEqual(status, 1)
        self.assertIn("access permissions", errors)
        self.assertNotIn("Start Docker Desktop, enable", errors)


if __name__ == "__main__":
    unittest.main()
