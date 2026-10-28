# Workflow reference

Build Debian `nagios-nrpe-server` packages and a SLES 12 SP3
`nrpe` RPM using the distribution packaging recipes, with command arguments
compiled in and runtime argument handling disabled by default.

## Requirements

- Python 3.9 or newer; direct commands have no third-party Python dependencies.
- Optional arrow-key menu: from the repository root, use `python3 -m pip install -r requirements-menu.txt`.
- Docker Engine with BuildKit, Linux containers, and Docker Compose 2.17 or newer.
- Access from containers to the matching Debian or SLES/OBS repositories.
- Disk space for builder images, source trees, test images, and packages.

Any editor can be used. On Windows, Docker Desktop with Linux containers is a
suitable Docker runtime. ARM hosts need support for `linux/amd64` emulation.
Bash is needed inside containers and for optional local shell syntax checks.

## Quick start

**Use `nrpe.py` as the main entry point.** It coordinates this project's Compose
files, checks Docker readiness, and records results. Direct Compose commands
bypass the controller's checks, logs, and target locks.

From the repository root on Windows, Linux, or macOS:

```sh
python3 nrpe.py doctor
python3 nrpe.py verify debian12
```

Ensure that `python3 --version` reports Python 3.9 or newer. On Windows, make
sure your Python installation provides `python3` in PATH.

Run without arguments for an interactive action and target menu:

```powershell
python3 nrpe.py
```

The arrow-key menu returns after each command. Use arrows and Enter to navigate,
Space to toggle targets, and A to select all targets. Escape returns to the
previous screen; Ctrl+C exits the menu or interrupts a running command. Install
the optional dependencies first; see [the menu guide](menu.md). Without an
interactive terminal, no arguments prints help and does not prompt. All CLI
messages are in English. Use `--help` or `<command> --help` for command-specific usage.

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
python3 nrpe.py verify debian12 debian13
python3 nrpe.py verify all
python3 nrpe.py test debian14
python3 nrpe.py status
python3 nrpe.py logs --last
```

SLES 12 SP3 uses a genuine digest-pinned 12.3 image and a hash-pinned set of
original SLE-12 Server/SDK RPMs. A modern input stage downloads sources; native
SLES tools verify package signatures and compile/install the result. No SLE-15
binary or ISO layout is used, and the obsolete `--sles-media` option is removed.
See the [SLES guide](sles12sp3.md).

## Targets and package builds

| Target | Distribution | Architecture | Output directory |
| --- | --- | --- | --- |
| `debian11` | Debian 11 Bullseye | amd64 | `output/debian11/` |
| `debian12` | Debian 12 Bookworm | amd64 | `output/debian12/` |
| `debian13` | Debian 13 Trixie | amd64 | `output/debian13/` |
| `debian14` | Debian 14 Forky | amd64 | `output/debian14/` |
| `sles12sp3` | SLES 12 SP3 | x86_64 | `output/sles12sp3/` |

`all` includes every target, including the SLES target. To validate
only Debian, list `debian11 debian12 debian13 debian14` explicitly.

Debian 11's security package files have moved to `archive.debian.org`; the setup
helper updates that security repository URL in both builder and test images.
Suite names, signing keys, signature checks, and validity checks remain enabled.
Debian 11 has been built and installation/TLS argument tests have passed here
with `4.0.3-1+withargs1`. This is historical archive availability, not a promise
of ongoing security updates for this old release.

SLES uses an actual SLES 12 SP3 base, not a Debian or Leap replacement.
Its RPM recipe, pinned sources, prerequisites, and validation limits
are documented in [SLES 12 SP3](sles12sp3.md).

Each Debian target uses a corresponding Debian container with a shared Dockerfile.
The build enables source repositories, installs build dependencies, and fetches
verified official `nagios-nrpe` sources from the selected suite. Source versions
are discovered dynamically; Forky is a moving testing suite.

The Debian build changes only the intended configure option in `debian/rules` and the
custom version entry in `debian/changelog`. It rejects unsupported packaging
layouts. `dpkg-buildpackage` produces binary packages; the exported server keeps
the name `nagios-nrpe-server` and uses `${original_version}+withargs1`.
Do not implement versioning by renaming finished packages. Increment the custom
revision when changing the recipe for the same official source version.

The build verifies package identity, version, architecture, executable contents,
and configure macros before exporting the server `.deb`, `SHA256SUMS`, and
available `.buildinfo`. It also builds the corresponding source package before
the binary build. `output/debianXX/sources/` contains the custom `.dsc`, every
upstream/packaging archive referenced by its SHA-256 fields, and a separate
`SHA256SUMS`. Export rejects missing files, mismatched versions and hashes, and
unsafe filenames. Preserve this directory alongside binaries for release
preparation; the binary-only checksum file used for installation is unchanged.
The client plugin is not exported. Existing valid output is retained until a
replacement build passes its package and source checks.

## Installation and argument integration tests

`verify` builds and tests a package; `test` exercises an existing artifact.
Separate opt-in services in `compose.test.yaml` use `docker/debian/test.Dockerfile` to:

1. Require exactly one server package and verify its checksum, identity,
   architecture, and custom version suffix.
2. Install that local `.deb` and its dependencies in a fresh matching distribution
   container, then check the installed version.
3. Confirm that the installed package keeps `dont_blame_nrpe=0` by default.
4. Start NRPE with a disposable configuration and confirm that ordinary requests
   succeed while argument requests are rejected.
5. Set `dont_blame_nrpe=1` only in the temporary configuration, restart NRPE, and
   verify exact responses for the argument pairs `alpha beta` and `gamma delta`.

Debian's `nagios-nrpe-plugin` and the natively built SLES `monitoring-plugins-nrpe` supply
`check_nrpe`, the client used by Nagios. A full Nagios scheduler or web interface is unnecessary for this protocol
test. Client and server run inside the same container over loopback using TLS
and a short-lived test certificate. No NRPE port is published. Package outputs
are mounted read-only, and the installed default configuration is unchanged.

Each target has a builder image and a separate minimal test image. Keeping tests
separate ensures that compiler and build dependencies cannot hide missing runtime
dependencies during package installation. Common Debian layers are shared by
Docker, and cached images are reused. Tests do not need a full Nagios server image.

An installation success alone does **not** mean the argument tests passed. The
log explicitly reports argument rejection with `dont_blame_nrpe=0` and exact
argument responses with `dont_blame_nrpe=1`.

These tests need the target distribution's repository access and run NRPE directly. They do not
validate systemd startup, external network access, production certificates, or a
complete Nagios deployment. Debian 11 passed package and runtime validation in this cloud environment. SLES 12 SP3 has also passed a full controller verify run with RPM build,
installation, and TLS argument tests; see its target notes. Do not interpret passing
unit tests as successful package builds for every target.

## Results, logs, and concurrent runs

Use [local cleanup](local-cleanup.md) to preview expired run logs/reports and
explicitly selected retired output or Docker images. `python3 nrpe.py clean`
does not delete anything; deletion requires `--apply` and respects workflow locks.

Each build/test/verify invocation receives a unique run ID and writes:

```text
.nrpe/runs/<run-id>/
├── report.json
└── run.log          # Created when a target reaches its workflow phases
```

The JSON report includes UTC timestamps, action, per-target build/package/test
outcomes, exit code, an optional normalized company CA SHA-256, and the tested artifact's filename, version from its filename,
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

The custom packages compile argument support while leaving runtime arguments
disabled. On a real target server, deliberately configure `/etc/nagios/nrpe.cfg`
on Debian, or `/etc/nrpe.cfg` for this SLES/OBS recipe:

```ini
allowed_hosts=<nagios-server-ip>,127.0.0.1,::1
dont_blame_nrpe=1
```

Replace the placeholder with the permitted Nagios server's address, review
firewall rules, TLS, command definitions, and argument validation, then restart
`nagios-nrpe-server` on Debian or `nrpe` on SLES. Bash command substitution must remain disabled. Build and
test containers never apply these settings to the development host.

## Development and validation

```sh
python3 -m unittest discover -s tests -v
for script in scripts/*.sh; do bash -n "$script" || exit; done
python3 nrpe.py doctor
```

For affected targets, run `python3 nrpe.py verify <target>`. Unit tests cover CLI
routing, Docker diagnostics, run reports, artifact identity, locking, cleanup,
and the Debian/RPM recipe transformations without requiring Docker or network access.
They do not replace real package and integration tests. Windows-specific error
messages and process handling also need validation on Windows.

Implementation is in `nrpe_cli/`; `nrpe.py` is the public entry point. Docker
runs build and test scripts from `scripts/`. Root [AGENTS.md](../AGENTS.md) and the
additional [script](../scripts/AGENTS.md) and [test](../tests/AGENTS.md) instructions apply.
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
