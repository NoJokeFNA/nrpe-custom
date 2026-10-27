"""Docker readiness and isolated Compose execution."""

import platform
import shutil
import subprocess

def check_docker():
    """Return the Docker executable only when Linux containers are available."""
    docker = shutil.which("docker")
    if docker is None:
        hint = (
            "Install Docker Desktop and start it with Linux containers enabled."
            if platform.system() == "Windows"
            else "Install Docker Engine and the Docker Compose v2 plugin."
        )
        raise RuntimeError(f"Docker CLI was not found in PATH. {hint}")

    try:
        result = subprocess.run(
            [docker, "info", "--format", "{{.OSType}}"],
            capture_output=True, text=True, timeout=15, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(_connection_hint("Docker did not respond within 15 seconds.")) from exc
    if result.returncode != 0:
        details = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(_connection_hint(f"Docker Engine is unavailable.\n{details}"))
    if result.stdout.strip() != "linux":
        raise RuntimeError(
            "Linux containers are required. On Windows, switch Docker Desktop "
            "to Linux containers and wait until the engine is ready."
        )

    result = subprocess.run(
        [docker, "compose", "version"],
        capture_output=True, text=True, timeout=15, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Docker Compose v2 is unavailable. Install the Compose plugin or "
            "update Docker Desktop."
        )
    return docker


def _connection_hint(message):
    if platform.system() == "Windows":
        return (
            f"{message}\nStart Docker Desktop, enable Linux containers, and wait "
            "until the engine is running. Then retry this command. If Docker "
            "Desktop is already running, check your Docker context and connection "
            "with 'docker context show' and 'docker info'."
        )
    return (
        f"{message}\nStart Docker Engine (or Docker Desktop) and check the "
        "selected Docker context and your access permissions with 'docker info'."
    )

