# nrpe-custom

Rebuild the official Debian `nagios-nrpe-server` package with
`--enable-command-args`, preserving Debian's packaging and runtime defaults.

## Requirements

- Python 3.9 or newer; no third-party Python dependencies.
- Docker Engine with Linux containers and Docker Compose v2.
- Access from containers to the official Debian repositories.
- Disk space for builder images, source trees, test images, and packages.

Any editor can be used. On Windows, Docker Desktop with Linux containers is a
suitable Docker runtime. ARM hosts need support for `linux/amd64` emulation.
Bash is needed inside containers and for optional local shell syntax checks.

## Quick start

**Use `nrpe.py` as the main entry point.** It coordinates this project's Compose
files, checks Docker readiness, and records results. Direct Compose commands
bypass the controller's checks, logs, and target locks.

From the repository root in Windows PowerShell:

```powershell
py -3 nrpe.py doctor
py -3 nrpe.py verify debian12
```

On Linux or macOS:

```sh
python3 nrpe.py doctor
python3 nrpe.py verify debian12
```

If the Windows Python launcher is unavailable, use `python` with Python 3.9+
installed and available in PATH.

Run without arguments for an interactive action and target menu:

```powershell
py -3 nrpe.py
```

The menu performs one selected action and exits. Without an interactive terminal,
no arguments prints help and does not prompt. All CLI messages are in English.
Use `--help` or `<command> --help` for command-specific usage.

## Commands

| Command | Purpose |
| --- | --- |
| `doctor` | Check required project files, Docker connectivity, Linux container mode, Compose v2, and both Compose configurations |
| `build <targets>` | Build packages, run in-container package checks, and verify exported checksums |
| `test <targets>` | Install and test existing packages without rebuilding them |
| `verify <targets>` | Build and integration-test each target before proceeding to the next |
| `status` | Show current packages, SHA-256 hashes, matching test results, and target locks without needing Docker |
| `logs --last` | Display output from the latest recorded workflow run |
| `logs --run <id>` | Display output from a particular recorded workflow run |

Select one target, multiple targets, or `all` by itself:

```powershell
py -3 nrpe.py verify debian12 debian13
py -3 nrpe.py verify all
py -3 nrpe.py test debian14
py -3 nrpe.py status
py -3 nrpe.py logs --last
```

Use `test` for packages you have already built locally. It checks the bytes in
`output/`; it does not establish that they were built from the current checkout.
`doctor` checks local prerequisites, not connectivity to Debian repositories from
build containers. If Docker is unavailable on Windows, the controller suggests
starting Docker Desktop, enabling Linux containers, and waiting for engine
readiness. It does not start or restart Docker Desktop automatically.

If a selected build target already has a server `.deb`, the controller asks for
confirmation in an interactive terminal; the default answer keeps the package.
Without a terminal it refuses to overwrite existing output unless you explicitly
pass `--rebuild`:

```powershell
py -3 nrpe.py verify debian12 --rebuild
py -3 nrpe.py verify all --rebuild --pull
py -3 nrpe.py test debian14 --pull
```

`--pull` checks for updated Debian base images before building the selected
builder/test images. Unchanged layers still use Docker's cache. Without this
option Docker may reuse a locally available base image. This is separate from
the NRPE source version, which APT discovers during each package build. Existing
packages are not automatically declared current merely because a base image is
unchanged. The controller does not yet compare a remote source version and full
build recipe against an existing `.deb` to decide whether rebuilding is needed.
The compatibility wrapper also accepts `--rebuild` and `--pull`.

The previous commands remain supported through a compatibility wrapper:

| Previous command | Preferred command |
| --- | --- |
| `build.py debian12` | `nrpe.py build debian12` |
| `build.py debian12 --test` | `nrpe.py verify debian12` |
| `build.py debian12 --test-only` | `nrpe.py test debian12` |

## Targets and package builds

| Target | Debian codename | Architecture | Output directory |
| --- | --- | --- | --- |
| `debian12` | Bookworm | amd64 | `output/debian12/` |
| `debian13` | Trixie | amd64 | `output/debian13/` |
| `debian14` | Forky | amd64 | `output/debian14/` |

Each target uses a corresponding Debian container with a shared Dockerfile.
The build enables source repositories, installs build dependencies, and fetches
verified official `nagios-nrpe` sources from the selected suite. Source versions
are discovered dynamically; Forky is a moving testing suite.

The build changes only the intended configure option in `debian/rules` and the
custom version entry in `debian/changelog`. It rejects unsupported packaging
layouts. `dpkg-buildpackage` produces binary packages; the exported server keeps
the name `nagios-nrpe-server` and uses `${original_version}+withargs1`.
Do not implement versioning by renaming finished packages. Increment the custom
revision when changing the recipe for the same official source version.

The build verifies package identity, version, architecture, executable contents,
and configure macros before exporting the server `.deb`, `SHA256SUMS`, and
available `.buildinfo`. The client plugin is not exported. Existing valid output
is retained until a replacement build passes its package checks.

## Installation and argument integration tests

`verify` builds and tests a package; `test` exercises an existing artifact.
Separate opt-in services in `compose.test.yaml` use `Dockerfile.test` to:

1. Require exactly one server package and verify its checksum, identity,
   architecture, and custom version suffix.
2. Install that local `.deb` and its dependencies in a fresh matching Debian
   container, then check the installed version.
3. Confirm that the installed package keeps `dont_blame_nrpe=0` by default.
4. Start NRPE with a disposable configuration and confirm that ordinary requests
   succeed while argument requests are rejected.
5. Set `dont_blame_nrpe=1` only in the temporary configuration, restart NRPE, and
   verify exact responses for the argument pairs `alpha beta` and `gamma delta`.

Debian's official `nagios-nrpe-plugin` supplies `check_nrpe`, the client used by
Nagios. A full Nagios scheduler or web interface is unnecessary for this protocol
test. Client and server run inside the same container over loopback using TLS
and a short-lived test certificate. No NRPE port is published. Package outputs
are mounted read-only, and the installed default configuration is unchanged.

There are three builder images and three minimal test images. Keeping tests
separate ensures that compiler and build dependencies cannot hide missing runtime
dependencies during package installation. Common Debian layers are shared by
Docker, and cached images are reused. Tests do not need a full Nagios server image.

An installation success alone does **not** mean the argument tests passed. The
log explicitly reports argument rejection with `dont_blame_nrpe=0` and exact
argument responses with `dont_blame_nrpe=1`.

These tests need Debian repository access and run NRPE directly. They do not
validate systemd startup, external network access, production certificates, or a
complete Nagios deployment. Full package validation has been blocked by DNS in
this cloud environment; do not interpret unit tests as a successful package build.

## Results, logs, and concurrent runs

Each build/test/verify invocation receives a unique run ID and writes:

```text
.nrpe/runs/<run-id>/
├── report.json
└── run.log          # Created when a target reaches its workflow phases
```

The JSON report includes UTC timestamps, action, per-target build/package/test
outcomes, exit code, and the tested artifact's filename, version from its filename,
and SHA-256 hash. A summary distinguishes passed, failed, interrupted, running,
and unrun phases. The first failure stops remaining targets; failed builds never
test old output files. `logs` also shows errors that occur before container output
exists. Local state and logs are ignored by Git and may contain paths or build
output; review them before sharing.

`status` matches test reports to the current package identity and hash. Replacing
a package with different bytes invalidates its previous passed test status. A
matching hash describes tested package bytes, not source provenance.

The controller locks the target during each operation, preventing simultaneous
controller builds or tests of that target. Different targets may run concurrently.
Direct Compose commands do not participate in these locks; avoid mixing them
with controller runs that use the same outputs.

`Ctrl+C` stops the run's Compose process and removes only its uniquely named
container. It does not run `compose down` or stop unrelated containers. If cleanup
fails, the target lock is retained. After a terminal crash or forced process kill,
`status` may show a lock and a report may remain `running`. Inspect
`.nrpe/locks/<target>/owner.json`, the report, and `docker ps -a` before manually
removing a stale lock directory. Never remove a lock while its run or container
is still active. Existing Compose networks and builder caches are retained.

## Target server configuration

The custom package compiles argument support but preserves Debian's defaults.
On a real target server, deliberately configure `/etc/nagios/nrpe.cfg`:

```ini
allowed_hosts=<nagios-server-ip>,127.0.0.1,::1
dont_blame_nrpe=1
```

Replace the placeholder with the permitted Nagios server's address, review
firewall rules, TLS, command definitions, and argument validation, then restart
`nagios-nrpe-server`. Bash command substitution must remain disabled. Build and
test containers never apply these settings to the development host.

## Development and validation

```sh
python3 -m unittest discover -s tests -v
bash -n scripts/build.sh scripts/verify.sh scripts/integration-test.sh
python3 nrpe.py doctor
```

For affected targets, run `python3 nrpe.py verify <target>`. Unit tests cover CLI
routing, Docker diagnostics, run reports, artifact identity, locking, cleanup,
and the Debian rules transformation without requiring Docker or network access.
They do not replace real package and integration tests. Windows-specific error
messages and process handling also need validation on Windows.

Implementation is in `nrpe_cli/`; `nrpe.py` is the public entry point. Docker
runs build and test scripts from `scripts/`. Root [AGENTS.md](AGENTS.md) and the
additional [script](scripts/AGENTS.md) and [test](tests/AGENTS.md) instructions apply.
Write code, comments, documentation, and commits in English; follow
[Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/).

## Repeatability and updates

Current Debian sources and mutable image tags give a repeatable method, not
bit-for-bit reproducible packages. Audit-ready releases require recording or
pinning image digests, repository snapshots, source versions, and dependencies.
Retain checksums and build information with released packages. Monitor Debian
security updates and rebuild custom packages when official sources change; do
not assume APT automatically replaces every custom version as intended.

Official sources: [Debian NRPE sources](https://sources.debian.org/src/nagios-nrpe/)
and [source package information](https://packages.debian.org/src:nagios-nrpe).
