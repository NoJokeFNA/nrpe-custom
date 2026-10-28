"""Local run reports, artifact identities, and exclusive target locks."""

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import uuid
from .targets import TARGETS, TARGET_CONFIG, package_files


ROOT = Path(__file__).resolve().parents[1]


def workflow_identity(root):
    """Record Git provenance when available; ordinary ZIP-based use still works."""
    try:
        commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=root,
                                capture_output=True, text=True, timeout=10)
        status = subprocess.run(['git', 'status', '--porcelain', '--untracked-files=all'],
                                cwd=root, capture_output=True, text=True, timeout=10)
        if commit.returncode or status.returncode:
            return None
        return {'commit': commit.stdout.strip(), 'dirty': bool(status.stdout.strip())}
    except (OSError, subprocess.TimeoutExpired):
        return None


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def new_id():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8]


def save_report(directory, report):
    path = directory / "report.json"
    temporary = directory / "report.tmp"
    temporary.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def reports(root):
    result = []
    for path in (root / ".nrpe" / "runs").glob("*/report.json"):
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
            if report.get("schema") == 1 and report.get("id") == path.parent.name:
                result.append(report)
        except (OSError, ValueError, AttributeError):
            continue
    return sorted(result, key=lambda item: item.get("started", item["id"]), reverse=True)


def _sha256(path):
    """Hash package payloads without loading entire artifacts into memory."""
    checksum = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def artifact(root, target):
    directory = root / "output" / target
    packages = package_files(root, target)
    if len(packages) != 1:
        raise RuntimeError(f"{target}: expected one server package, found {len(packages)}. Run build first.")
    path = packages[0]
    digest = _sha256(path)
    # The server checksum must be present; SLES also records its companion RPM.
    expected = f"{digest}  {path.name}"
    checksums = directory / "SHA256SUMS"
    entries = checksums.read_text(encoding="utf-8").splitlines() if checksums.is_file() else []
    if expected not in entries:
        raise RuntimeError(f"{target}: package checksum is missing or incorrect. Rebuild the package.")
    config = TARGET_CONFIG[target]
    result = {"file": path.name, "sha256": digest,
              "version": path.name[len(config["prefix"]):-len(config["suffix"])]}
    if target == "sles15sp3":
        helpers = sorted(directory.glob("system-user-nagios-*.noarch.rpm"))
        if len(helpers) != 1:
            raise RuntimeError("sles15sp3: expected one companion user-package RPM. Rebuild the target.")
        helper = helpers[0]
        helper_digest = _sha256(helper)
        if f"{helper_digest}  {helper.name}" not in entries:
            raise RuntimeError("sles15sp3: companion package checksum is missing or incorrect.")
        result["companions"] = [{"file": helper.name, "sha256": helper_digest}]
    return result


@contextmanager
def target_lock(root, target, run_id):
    path = root / ".nrpe" / "locks" / target
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.mkdir()
    except FileExistsError as exc:
        raise RuntimeError(
            f"{target} is locked by another or interrupted run ({path}). "
            "Check status and running containers. Remove this lock directory only "
            "after confirming that its owner is no longer running."
        ) from exc
    try:
        (path / "owner.json").write_text(
            json.dumps({"run": run_id, "started": timestamp()}), encoding="utf-8"
        )
        yield path
    finally:
        # A failed container cleanup leaves a marker and retains the lock.
        if not (path / "cleanup-required").exists():
            (path / "owner.json").unlink(missing_ok=True)
            path.rmdir()
