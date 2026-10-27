"""Coordinate package workflows and persist their evidence."""

import os
import signal
import subprocess

from .docker import check_docker
from .state import ROOT, artifact, new_id, save_report, target_lock, timestamp
from .targets import package_files


def stop_process(process):
    if process.poll() is not None:
        return
    try:
        if os.name == "nt":
            process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        if os.name == "nt":
            process.kill()
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        process.wait()


def run_phase(docker, root, run_id, target, phase, log, lock, pull=False, media=None):
    name = f"nrpe-{run_id}-{target}-{phase}"
    base = [docker, "compose", "-f",
            "compose.yaml" if phase == "build" else "compose.test.yaml"]
    service = target if phase == "build" else f"test-{target}"
    commands = []
    if pull:
        commands.append(base + ["build", "--pull", service])
    commands.append(base + ["run", "--rm", "--name", name]
                    + ([] if pull else ["--build"]) + [service])
    options = ({"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
               if os.name == "nt" else {"start_new_session": True})
    if media is not None:
        options["env"] = dict(os.environ, SLES_MEDIA_DIR=str(media))
    process = None
    try:
        for command in commands:
            process = subprocess.Popen(
                command, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace", **options,
            )
            for line in process.stdout:
                log.write(line)
                log.flush()
                print(line, end="", flush=True)
            code = process.wait()
            process.stdout.close()
            if code:
                return code
        return 0
    finally:
        if process is not None:
            stop_process(process)
            process.stdout.close()
            # Never use compose down: other runs may share the project network.
            try:
                cleanup = subprocess.run(
                    [docker, "rm", "-f", name], capture_output=True, text=True,
                    timeout=20, check=False,
                )
                if cleanup.returncode and "No such container" not in cleanup.stderr:
                    raise RuntimeError(cleanup.stderr.strip())
            except (OSError, subprocess.TimeoutExpired, RuntimeError) as exc:
                (lock / "cleanup-required").write_text(name, encoding="utf-8")
                raise RuntimeError(f"Could not clean up {name}; target lock retained: {exc}") from exc


def summary(report):
    print("\nTarget      Build        Package      Integration")
    for target, result in report["targets"].items():
        print(f"{target:<12}{result['build']:<13}{result['package']:<13}{result['test']}")
    print(f"Run: {report['id']} ({report['status']})")


def execute(action, targets, root=ROOT, rebuild=False, pull=False, media=None):
    run_id = new_id()
    directory = root / ".nrpe" / "runs" / run_id
    directory.mkdir(parents=True)
    report = {"schema": 1, "id": run_id, "action": action, "started": timestamp(),
              "status": "running", "exit_code": None, "rebuild": rebuild, "pull": pull,
              "sles_media": str(media) if media is not None else None,
              "targets": {
                  target: {"build": "not run", "package": "not run", "test": "not run"}
                  for target in targets}}
    save_report(directory, report)
    code = 1
    active = None
    phase = None
    try:
        docker = check_docker()
        for target in targets:
            active = report["targets"][target]
            phase = None
            with target_lock(root, target, run_id) as lock:
                with (directory / "run.log").open("a", encoding="utf-8") as log:
                    if action in ("build", "verify"):
                        if not rebuild and package_files(root, target):
                            raise RuntimeError(f"{target}: output already exists. Use --rebuild or test it instead.")
                        phase = "build"
                        active[phase] = "running"
                        save_report(directory, report)
                        print(f"\n[{target}] Building package", flush=True)
                        log.write(f"\n[{target}] Building package\n")
                        code = run_phase(docker, root, run_id, target, phase, log, lock, pull=pull,
                                         media=media if target == "sles15sp4" else None)
                        active[phase] = "passed" if code == 0 else "failed"
                        if code:
                            break
                    phase = "package"
                    active[phase] = "running"
                    print(f"[{target}] Checking package checksum", flush=True)
                    before = artifact(root, target)
                    active["artifact"] = before
                    active[phase] = "passed"
                    save_report(directory, report)
                    if action in ("test", "verify"):
                        phase = "test"
                        active[phase] = "running"
                        save_report(directory, report)
                        print(f"[{target}] Installing package and testing NRPE arguments", flush=True)
                        log.write(f"\n[{target}] Installing package and testing NRPE arguments\n")
                        code = run_phase(docker, root, run_id, target, phase, log, lock, pull=pull,
                                         media=media if target == "sles15sp4" else None)
                        active[phase] = "passed" if code == 0 else "failed"
                        if code:
                            break
                        if artifact(root, target) != before:
                            raise RuntimeError(f"{target}: package changed during the test; result is invalid.")
                    code = 0
            save_report(directory, report)
        report["status"] = "passed" if code == 0 else "failed"
    except KeyboardInterrupt:
        code = 130
        report["status"] = "interrupted"
        if active is not None and phase and active[phase] == "running":
            active[phase] = "interrupted"
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        code = 1
        report["status"] = "failed"
        report["error"] = str(exc)
        if active is not None and phase:
            active[phase] = "failed"
        print(f"ERROR: {exc}")
    finally:
        report["finished"] = timestamp()
        report["exit_code"] = code
        save_report(directory, report)
        summary(report)
        print(f"Logs and report: {directory}")
    return code
