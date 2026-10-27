# SLES 15 SP4 RPM target (experimental)

The controller accepts `sles15sp4` for builds, existing-package tests, status,
logs, rebuild confirmation, and base image refresh:

```sh
python3 nrpe.py verify sles15sp4
python3 nrpe.py test sles15sp4
```

This target is implemented but has **not completed a full RPM build and runtime
integration test**. Unit tests and source verification do not establish that the
SLES installation workflow works. Do not deploy its packages until `verify`
finishes successfully in the intended SLES environment.

## Package source and revision

The reported deployment uses:

```text
nrpe-4.1.1-150400.95.2.x86_64
Source: nrpe-4.1.1-150400.95.2.src.rpm
Vendor: obs://build.opensuse.org/server:monitoring
Distribution: server:monitoring / SLE_15_SP4
```

That is an OBS `server:monitoring` package, not the Debian package or a claim of
SUSE enterprise support for this custom rebuild. The old `server:monitoring`
SP4 binary repository is currently absent. Do not silently substitute its SP7
packages or claim to have reproduced the missing historical source RPM.

The build instead uses the reviewed, immutable OBS source revision
`835292739a5736a9d8f0460f670b6f15` for NRPE 4.1.1. All 15 upstream files are
downloaded over verified HTTPS and checked against the sizes and SHA-256 hashes
in [the source manifest](../packaging/sles15sp4-source.json). The initial manifest
was also checked against OBS's own source metadata.

The upstream spec already contains `--enable-command-args`, as well as
`--enable-bash-command-substitution`. The custom transformation retains argument
support, removes Bash command substitution, and stamps the spec Release as
`150400.95.2.withargs1`. This baseline is derived from the reported installed
release; it is not an automatically discovered current SP4 release. Unexpected
versions or configure layouts fail for review. Installation paths, service
definitions, and dependency declarations are retained.

SLES sources are intentionally pinned. `--pull` refreshes the base image, not
the OBS source revision. Updating the manifest requires reviewing the new recipe
and source checksums. Debian builds continue to discover source versions via APT.

## Base image and repository prerequisites

`Dockerfile.sles` and `Dockerfile.sles-test` default to the genuine image:

```text
registry.suse.com/bci/bci-base:15.4
```

The image has been retrieved successfully here. It is not an openSUSE Leap or
SP7 replacement. The setup helper adds the still-available matching
`openSUSE:Backports:SLE-15-SP4/standard` package repository with signature checks
enabled. The renewed official backports public key is bundled at
[sles15sp4-backports.asc](../packaging/sles15sp4-backports.asc); its fingerprint is
`637B32FF3D83F07A7AE1C40A9C214D4065176565`, matching the repository's signing
identity. Its authoritative URL and file hash are recorded in the source manifest.
The renewed SUSE signing key is also included as
[sles15sp4-suse.asc](../packaging/sles15sp4-suse.asc), fingerprint
`FEAB502539D846DB2C0961CA70AF9E8139DB7C82`, obtained from the official
`SUSE:SLE-15:Update` key endpoint. Both renewals retain the existing signing
identities instead of bypassing an expired-key problem.

**The public BCI and backports repositories are insufficient on their own.** A
real refresh succeeded, but dependency discovery found missing packages including
`nagios-rpm-macros`. Other requirements include `monitoring-plugins-common` and
`system-user-nagios`. Full matching SLES package sources must be available; an
Internet allowlist cannot supply packages absent from a repository.

Provide a minimal SLES 15 SP4 OCI base with the required repositories configured,
for example through an authorized RMT or installation-media repository. Select it
for both build and test images through `SLES_BASE_IMAGE`:

```powershell
$env:SLES_BASE_IMAGE = "company/sles15sp4-base:approved"
python3 nrpe.py verify sles15sp4
```

The base must retain a real SLES 15 SP4 identity and matching libraries. Keep the
base free of compilers and preinstalled NRPE servers so installation tests cannot
accidentally rely on build dependencies. Handle registry/repository credentials
through secure local Docker/SUSE configuration, not commits or chat messages.

The official [SLES download page](https://www.suse.com/download/sles/) lists SP4
installation media. An ISO is installation media, not a Docker image: do not
pass it to `docker import` or assume it contains the external OBS NRPE package.
It can provide an offline SLES package repository or a foundation for preparing
a suitable OCI base. This project does not automatically download multi-gigabyte
installation images, accept subscription terms, or build an OS root filesystem
from an ISO. Adding Leap packages is not the default workaround.

Historical SP4 repositories may contain old metadata and expired signing-key
copies. Restore trust only through authoritative renewed keys and matching
repositories. Do not disable TLS, package signatures, dependency checks, or
metadata validation to make a build succeed. Corporate proxies may require
installing their trusted CA into the base image; keep TLS verification enabled.

## Build and test contract

The builder installs the original spec's build requirements and uses
`rpmbuild -ba`. Before export it checks RPM name, version/release, architecture,
executable and configuration paths, generated configure macros, and the disabled
argument default in the packaged configuration. Successful outputs go to
`output/sles15sp4/`:

```text
nrpe-4.1.1-150400.95.2.withargs1.x86_64.rpm
nrpe-4.1.1-150400.95.2.withargs1.src.rpm
source-manifest.json
SHA256SUMS
```

The custom RPM is a locally built, unsigned artifact. Its checksum binds the
integration test to those bytes; repository dependencies still undergo normal
zypper signature verification. The test installs only declared runtime
requirements, excluding RPM's internal capabilities, then installs the custom
RPM with normal RPM payload and dependency checks. It does not install the
build toolchain or an older NRPE server to hide missing dependencies.

The test client comes from `monitoring-plugins-nrpe`. The common protocol test
checks both rejected arguments with `dont_blame_nrpe=0` and exact successful
responses with `dont_blame_nrpe=1` over TLS. NRPE runs directly; the test does not
validate systemd startup or access from a real Nagios server.

For this OBS packaging, the deployed configuration is `/etc/nrpe.cfg` and the
service is `nrpe`. Debian instead uses `/etc/nagios/nrpe.cfg` and
`nagios-nrpe-server`. The custom SLES package keeps runtime arguments disabled
until an administrator deliberately changes the target configuration.
