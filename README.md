# nrpe-custom

Build the official Debian `nagios-nrpe-server` package with NRPE command argument
support compiled in, while preserving Debian's packaging and runtime defaults.

## Current status

The Dockerfile, Compose configuration, build scripts, rules-transformer tests,
and output directory placeholders from the supplied project archive are included.
The documentation and Compose comments use an editor-independent workflow.

Shell syntax checks, all five rules-transformer unit tests, and Compose
configuration validation pass. A Debian 12 build was attempted in the cloud
environment, but failed while installing dependencies because the build container
could not resolve `deb.debian.org`. No package was produced. Debian 13 and 14
builds, package installation, and NRPE client/server integration have not been run.
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
- Python 3 and Bash for running the lightweight checks outside containers.

Any editor or terminal can be used. On Windows, Docker Desktop with Linux
containers is an option. ARM hosts require support for running `linux/amd64`
containers through emulation.

## Usage

Run commands from the repository root. Build one target at a time with:

```sh
docker compose run --rm --build debian12
docker compose run --rm --build debian13
docker compose run --rm --build debian14
```

Alternatively, start all three build services:

```sh
docker compose up --build --abort-on-container-failure
```

Each service is a one-shot build job that should exit successfully when finished.
Inspect service logs when a build fails:

```sh
docker compose logs debian12
```

Remove the Compose containers after use:

```sh
docker compose down
```

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
bash -n scripts/build.sh scripts/verify.sh
python3 -m unittest discover -s tests -v
docker compose config --quiet
```

Then build each affected Debian target and verify the artifacts from that run.
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
├── compose.yaml
├── .dockerignore
├── .gitattributes
├── .gitignore
├── scripts/
│   ├── AGENTS.md
│   ├── build.sh
│   ├── enable_command_args.py
│   └── verify.sh
├── tests/
│   ├── AGENTS.md
│   └── test_enable_command_args.py
└── output/
    ├── debian12/
    ├── debian13/
    └── debian14/
```

## References

- [Official Debian NRPE sources](https://sources.debian.org/src/nagios-nrpe/)
- [Debian source package information](https://packages.debian.org/src:nagios-nrpe)
