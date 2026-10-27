# nrpe-custom

Build the official Debian `nagios-nrpe-server` package with NRPE command argument
support compiled in, while preserving Debian's packaging and runtime defaults.

## Current status

The Dockerfile, Compose configuration, build scripts, rules-transformer tests,
and output directory placeholders from the supplied project archive are included.
The documentation and Compose comments use an editor-independent workflow.

Shell syntax checks, all 17 unit tests (rules transformation, Docker preflight,
and build/test sequencing), and both Compose configuration validations pass.
Attempts to build the Debian 12 builder and integration test image in the cloud
failed while installing dependencies because the containers could not resolve
the Debian repository host (or the configured proxy). No package was produced
here. Debian 13 and 14 builds, package installation, and NRPE client/server
integration have not completed in this environment.
See the validation section for the required checks.

## Build targets

| Target | Debian codename | Compose service | Output directory |
| --- | --- | --- | --- |
| Debian 12 | Bookworm | `debian12` | `output/debian12/` |
| Debian 13 | Trixie | `debian13` | `output/debian13/` |
| Debian 14 | Forky | `debian14` | `output/debian14/` |

Each target uses its matching Debian container and builds for `linux/amd64`.
The build selects the current official source version from the target suite,
rather than assuming a fixed historical NRPE version. Forky is a moving testing
suite, so its sources and dependencies can change frequently.

## Requirements

- Docker Engine with Linux containers and Docker Compose v2.
- Access from containers to the official Debian package repositories.
- Sufficient disk space for builder images, source trees, and generated packages.
- Python 3 for the build launcher and unit tests; Bash for local shell syntax checks.

Any editor or terminal can be used. On Windows, Docker Desktop with Linux
containers is an option. ARM hosts require support for running `linux/amd64`
containers through emulation.

## Usage

Prefer `build.py` for this project instead of calling Docker Compose directly.
It performs the Docker readiness checks and coordinates builds and optional
integration tests using the project's Compose files.

Run it from the repository root. On Windows (PowerShell):

```powershell
py -3 build.py debian12 --test
py -3 build.py debian13 --test
py -3 build.py debian14 --test
```

On Linux or macOS:

```sh
python3 build.py debian12 --test
python3 build.py debian13 --test
python3 build.py debian14 --test
```

Use `all` instead of a service name to build all targets sequentially, stopping
at the first failure (for example, `py -3 build.py all --test` on Windows). Omit
`--test` for a build without integration testing. If the Windows
Python launcher is unavailable, use `python build.py debian12` with Python 3
installed and available in PATH.

The launcher checks the Docker CLI, Engine connectivity, Linux container mode,
and Compose v2 before starting a build. On Windows, an unavailable engine produces
an English message asking you to start Docker Desktop, enable Linux containers,
and wait for the engine to become ready. It also preserves Docker's error details
and suggests checking the active Docker context if Desktop is already running.
It does not start or restart Docker Desktop automatically. A running Desktop
process alone does not prove that the engine is ready, so the check uses the
Docker API instead of checking the process list.

Each build is a one-shot job that should exit successfully when finished. The
launcher streams its output to the terminal and preserves failures as nonzero
exit codes. Its disposable containers are removed after each run.

## Integration tests

Build and then test the newly produced package on Windows:

```powershell
py -3 build.py debian12 --test
py -3 build.py all --test
```

If you already built packages, test them without rebuilding:

```powershell
py -3 build.py debian12 --test-only
py -3 build.py all --test-only
```

On Linux or macOS, replace `py -3` with `python3`. `--test` and `--test-only` are
mutually exclusive. The launcher stops at the first build or test failure. A
failed build never triggers a test against an older package left in `output/`.
`--test-only` deliberately tests the artifacts currently in that directory; it
does not prove they were built from the current checkout.

Each target has a separate test service in `compose.test.yaml`, using
`Dockerfile.test` and the corresponding Debian base image. Test services are
opt-in and do not run as part of normal builds. Each run:

1. Requires exactly one server package, checks its SHA-256 checksum, package
   identity, custom version suffix, and architecture.
2. Installs that local `.deb` and its dependencies in a fresh Debian container,
   verifying that the installed version is the supplied custom version.
3. Checks that the installed package keeps `dont_blame_nrpe=0` by default.
4. Starts NRPE with a disposable test configuration and verifies that a real
   `check_nrpe` request succeeds without arguments, while argument requests fail.
5. Enables arguments only in that temporary configuration, restarts NRPE, and
   verifies exact responses for two different pairs of arguments.

The minimal Nagios-side component is Debian's official `nagios-nrpe-plugin`
(`check_nrpe`). This is the client used by Nagios to contact NRPE; a full Nagios
scheduler or web interface is unnecessary for this protocol test. Client and
server run in the same isolated container over loopback, using TLS and a
short-lived test certificate. No NRPE port is published on the host. Outputs are
mounted read-only, and the packaged configuration remains unchanged.

The test container needs access to Debian repositories to install dependencies.
It runs NRPE directly rather than booting systemd, so these tests do not validate
systemd service startup, external networking, production certificates, or a full
Nagios deployment. On failure the script prints available logs and exits nonzero.

## Advanced: direct Compose commands

These commands **bypass the launcher's Docker readiness checks**. Prefer the
launcher above for normal use:

```sh
docker compose run --rm --build debian12
docker compose -f compose.test.yaml run --rm --build test-debian12
```

Compose cannot run a container-side preflight when its connection to Docker
fails. Test containers require a successfully built package in the matching output
directory. Test services use an opt-in profile; explicitly naming a service in
`compose run` activates it automatically.

## Packaging contract

The build performs these steps inside the target Debian container:

1. Enable official source repositories and install the package's build dependencies.
2. Download and verify the official `nagios-nrpe` source package through APT.
3. Add `--enable-command-args` to the configure invocation in `debian/rules`,
   rejecting unsupported packaging layouts instead of guessing a transformation.
4. Record `${original_version}+withargs1` in `debian/changelog` using Debian tools.
5. Build binary packages with `dpkg-buildpackage`.
6. Verify the server package's name, version, architecture, executable, and
   generated configure macros before exporting it.
7. Export the server `.deb`, its SHA-256 checksum, and available `.buildinfo` to
   the target's output directory.

The binary package name remains `nagios-nrpe-server`. Do not rename a finished
package to implement versioning. Keep Debian's installation paths, dependencies,
systemd integration, and other packaging behavior unchanged. Increment the custom
`withargs` revision when the build recipe changes for the same Debian source
version. The client plugin is not exported.

## Security and runtime behavior

Compiling argument support must leave `dont_blame_nrpe=0` as the default.
Enabling `dont_blame_nrpe=1` is a separate, deliberate decision on the target
system. Bash command substitution must remain disabled.

Before enabling remote arguments, review permitted clients, network access, TLS,
command definitions, and argument validation. Preserve APT signature checks,
source checksums, and TLS verification throughout the build.

Test package installation only in an isolated matching Debian environment.
Confirm both the disabled runtime default and a real client/server argument
request before deploying packages. A configure macro check alone does not prove
runtime behavior.

## Validation

Run lightweight checks from the repository root:

```sh
bash -n scripts/build.sh scripts/verify.sh scripts/integration-test.sh
python3 -m unittest discover -s tests -v
docker compose config --quiet
docker compose -f compose.test.yaml --profile integration config --quiet
```

Then use `build.py <target> --test` for each affected Debian target to build and
exercise its package in a fresh matching container.
Unit tests and syntax checks do not substitute for actual package builds,
installation tests, or runtime integration tests. Report unrun checks explicitly.

## Repeatability and updates

Using current Debian sources and mutable base image tags gives a repeatable
build method, not a guarantee of bit-for-bit identical outputs. Audit-ready
releases require recording or pinning image digests, repository snapshots, source
versions, and build dependencies. Retain checksums and build information with
released artifacts.

Monitor Debian security updates and rebuild custom packages when official source
versions change. Do not assume that APT will automatically replace every custom
version with the desired official update.

## Contributing

Write code, comments, documentation, and commit messages in English. Keep
instructions editor-independent and avoid unnecessary IDE-specific configuration.
Follow [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/)
and make a separate commit for each independently reviewable change.

Repository-wide guidance lives in [AGENTS.md](AGENTS.md), with additional rules
for [build scripts](scripts/AGENTS.md) and [tests](tests/AGENTS.md).

## Project files

```text
nrpe-custom/
├── AGENTS.md
├── README.md
├── Dockerfile
├── Dockerfile.test                  # Minimal installation and NRPE test image
├── build.py                         # Host-side Docker preflight and build launcher
├── compose.yaml
├── compose.test.yaml                # Opt-in test services for each Debian release
├── .dockerignore
├── .gitattributes
├── .gitignore
├── scripts/
│   ├── AGENTS.md
│   ├── build.sh
│   ├── enable_command_args.py
│   ├── integration-test.sh
│   └── verify.sh
├── tests/
│   ├── AGENTS.md
│   ├── test_enable_command_args.py
│   └── test_build_launcher.py
└── output/
    ├── debian12/
    ├── debian13/
    └── debian14/
```

## References

- [Official Debian NRPE sources](https://sources.debian.org/src/nagios-nrpe/)
- [Debian source package information](https://packages.debian.org/src:nagios-nrpe)
