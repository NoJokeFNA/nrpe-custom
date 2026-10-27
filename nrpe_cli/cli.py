"""User-facing commands for the NRPE workflow."""

import argparse
import subprocess
import sys

from .controller import execute
from .docker import check_docker
from .state import ROOT, TARGETS, artifact, reports
from .targets import TARGET_CONFIG, package_files


def doctor(root):
    print("Checking project files...")
    required = ("compose.yaml", "compose.test.yaml", "Dockerfile", "Dockerfile.test",
                "scripts/build.sh", "scripts/verify.sh", "scripts/integration-test.sh",
                "Dockerfile.sles", "Dockerfile.sles-test", "scripts/build-sles.sh",
                "scripts/integration-test-sles.sh", "scripts/test-nrpe-protocol.sh",
                "scripts/sles_source.py", "scripts/setup-sles-repositories.sh",
                "scripts/setup-debian-repositories.sh",
                "packaging/sles15sp4-source.json", "packaging/sles15sp4-backports.asc")
    missing = [name for name in required if not (root / name).is_file()]
    if missing:
        raise RuntimeError("Missing project files: " + ", ".join(missing))
    print("Checking Docker Engine, Linux containers, and Compose v2...")
    docker = check_docker()
    for filename in ("compose.yaml", "compose.test.yaml"):
        print(f"Checking {filename}...")
        result = subprocess.run(
            [docker, "compose", "-f", filename, "--profile", "integration", "config", "--quiet"],
            cwd=root, capture_output=True, text=True, timeout=30, check=False,
        )
        if result.returncode:
            raise RuntimeError(f"Invalid {filename}: {result.stderr.strip()}")
    print("PASS: Local prerequisites and Compose configuration are ready.")
    print("This does not check package repository access from build containers.")
    return 0


def show_status(root):
    history = reports(root)
    print("Target      Version                      Integration / artifact status")
    for target in TARGETS:
        lock = root / ".nrpe" / "locks" / target
        if lock.exists():
            print(f"{target:<12}LOCKED: active or interrupted run; inspect {lock}")
            continue
        try:
            current = artifact(root, target)
        except (OSError, RuntimeError) as exc:
            print(f"{target:<12}{exc}")
            continue
        outcome = "not tested"
        for report in history:
            result = report.get("targets", {}).get(target, {})
            tested = result.get("artifact")
            if result.get("test", "not run") == "not run":
                continue
            if tested == current:
                outcome = f"{result['test']} (run {report['id']})"
                break
        print(f"{target:<12}{current['version']:<29}{outcome}")
        print(f"  SHA-256: {current['sha256']}")
    if history:
        last = history[0]
        print(f"Latest run: {last['id']} ({last['action']}, {last['status']})")
    else:
        print("No recorded runs. Status is based on local artifacts only.")
    print("Test results identify package bytes, not the current source checkout.")
    return 0


def show_logs(root, run_id=None):
    history = reports(root)
    matches = [item for item in history if run_id is None or item["id"] == run_id]
    if not matches:
        raise RuntimeError("No matching run. Use status to find a recorded run ID.")
    report = matches[0]
    print(f"Run {report['id']}: {report['action']} ({report['status']})")
    path = root / ".nrpe" / "runs" / report["id"] / "run.log"
    if path.is_file():
        with path.open(encoding="utf-8", errors="replace") as log:
            for line in log:
                print(line, end="")
    else:
        print("No container output was recorded.")
    if report.get("error"):
        print(f"ERROR: {report['error']}")
    return 0


def parser():
    result = argparse.ArgumentParser(description="Build, test, and inspect custom NRPE packages.")
    commands = result.add_subparsers(dest="action")
    for action, help_text in (
        ("build", "Build packages and check their exported artifacts"),
        ("test", "Install and test existing packages without rebuilding"),
        ("verify", "Build packages and run their integration tests"),
    ):
        command = commands.add_parser(action, help=help_text)
        command.add_argument("targets", nargs="+", choices=(*TARGETS, "all"))
        command.add_argument("--pull", action="store_true",
                             help="check for updated base images before building images")
        if action != "test":
            command.add_argument("--rebuild", action="store_true",
                                 help="explicitly allow rebuilding existing package outputs")
    commands.add_parser("doctor", help="Diagnose Docker and project configuration")
    commands.add_parser("status", help="Show local packages and recorded test results (no Docker required)")
    logs = commands.add_parser("logs", help="Display output from a recorded run (no Docker required)")
    selection = logs.add_mutually_exclusive_group()
    selection.add_argument("--last", action="store_true", help="Show the latest run (default)")
    selection.add_argument("--run", metavar="ID", help="Show a specific run")
    return result


def interactive_menu():
    print("NRPE package controller")
    actions = {"1": "verify", "2": "build", "3": "test", "4": "doctor",
               "5": "status", "6": "logs"}
    print("1. Build and test\n2. Build only\n3. Test existing packages\n"
          "4. Diagnose Docker\n5. Show status\n6. Show latest log\nq. Quit")
    while True:
        answer = input("Action: ").strip().lower()
        if answer in ("q", "quit"):
            return None
        action = actions.get(answer)
        if action:
            break
        print("Choose an action from 1 to 6, or q to quit.")
    if action not in ("build", "test", "verify"):
        return [action]
    labels = [f"{index}. {target}" for index, target in enumerate((*TARGETS, "all"), 1)]
    print("Targets: " + "   ".join(labels))
    aliases = {str(index): target for index, target in enumerate((*TARGETS, "all"), 1)}
    while True:
        answer = input("Targets (space-separated numbers or names; q to quit): ").strip().lower()
        if answer in ("q", "quit"):
            return None
        targets = [aliases.get(item, item) for item in answer.split()]
        if (targets and all(item in (*TARGETS, "all") for item in targets)
                and ("all" not in targets or targets == ["all"])):
            return [action, *targets]
        print("Choose targets, or all by itself.")


def main(argv=None, root=ROOT):
    argv = sys.argv[1:] if argv is None else argv
    if not argv and sys.stdin.isatty() and sys.stdout.isatty():
        try:
            argv = interactive_menu()
            if argv is None:
                return 0
        except EOFError:
            return 0
        except KeyboardInterrupt:
            print("\nCancelled.", file=sys.stderr)
            return 130
    command_parser = parser()
    args = command_parser.parse_args(argv)
    if args.action is None:
        command_parser.print_help()
        return 0
    try:
        if args.action == "doctor":
            return doctor(root)
        if args.action == "status":
            return show_status(root)
        if args.action == "logs":
            return show_logs(root, args.run)
        if "all" in args.targets and len(args.targets) != 1:
            command_parser.error("Use 'all' alone, or list specific targets.")
        targets = list(TARGETS) if args.targets == ["all"] else list(dict.fromkeys(args.targets))
        for target in targets:
            if TARGET_CONFIG[target].get("experimental"):
                print(f"Experimental target: {target}. Review build and integration results before deployment.")
        rebuild = getattr(args, "rebuild", False)
        if args.action in ("build", "verify") and not rebuild:
            existing = [target for target in targets if package_files(root, target)]
            if existing:
                print("Existing package output: " + ", ".join(existing))
                if not sys.stdin.isatty() or not sys.stdout.isatty():
                    raise RuntimeError("Use --rebuild to replace existing packages, or use test to test them.")
                try:
                    answer = input("Rebuild the selected targets? [y/N]: ").strip().lower()
                except EOFError:
                    answer = ""
                if answer not in ("y", "yes"):
                    print("Cancelled; existing packages were kept.")
                    return 0
                rebuild = True
        return execute(args.action, targets, root, rebuild=rebuild, pull=args.pull)
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        return 130
