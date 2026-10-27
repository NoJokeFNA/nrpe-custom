# SLES 15 SP4 RPM target

The controller accepts `sles15sp4` for builds, existing-package tests, status,
logs, rebuild confirmation, and base image refresh:

```sh
python3 nrpe.py verify sles15sp4
python3 nrpe.py test sles15sp4
```

A full `nrpe.py verify sles15sp4 --rebuild` run passed in the cloud environment:
RPM build, checksums, fresh-container installation, arguments rejected by default,
and exact responses for two argument pairs after runtime activation. The tested
server version is `4.1.1-150400.95.2.withargs1` on genuine SLES 15 SP4. The run
used the regular online workflow with no ISO and no Leap package repository.
The cloud proxy required a CA-enabled SLES base selected through `SLES_BASE_IMAGE`;
TLS and package-signature verification remained enabled.

The container tests run NRPE directly. They do not validate a full VM boot,
systemd service startup, or production Nagios connectivity. Original package
post-install scripts may print a systemd-not-PID-1 message in a container; the
RPM transaction, installed version, and actual NRPE protocol checks must still
complete successfully. These are custom rebuilds, not SUSE-certified releases.

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

## Installing the custom package on a server

Use the [installation guide](installation.md#sles-15-sp4) to deploy the exported
`.withargs1` RPM on a matching SLES 15 SP4 x86_64 server. It covers checksums,
installation with and without an existing `system-user-nagios` package, unsigned
local RPM handling, configuration, service startup, and version verification.
The repository commands in the next section describe the historical upstream
installation and do not select this project's custom artifact.

## Installing the repository package on an existing server

The reported deployment uses this normal zypper workflow, run as root or with
`sudo`:

```sh
sudo zypper install nrpe
```

If the configured repositories do not contain NRPE, the original repository setup
is:

```sh
sudo zypper addrepo 'https://download.opensuse.org/repositories/server:monitoring/SLE_15_SP4/server:monitoring.repo'
sudo zypper refresh
sudo zypper install nrpe
```

The exact URL above and its `server:/monitoring` spelling both returned HTTP 404
when checked here on 2026-10-27. Keep these commands as the deployment's historical
repository procedure, not as a promise that the retired SP4 repository is still
published. Use an approved matching mirror if available; do not replace SP4 with
SP7. This installs the repository package, not necessarily this project's custom
`.withargs1` build. The custom build obtains its reviewed source through the OBS
API independently of that retired binary repository.

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

The public BCI/backports indexes omit some dependencies needed by the current
OBS recipe. The build now supplies these from their original providers:

- `nagios-rpm-macros` 0.14-1.15 and `monitoring-plugins-common` 2.3.1-3.9.2 are
  original SUSE RPMs, identified through the official SP4 NRPE build metadata.
  [The bootstrap manifest](../packaging/sles15sp4-bootstrap.json) pins their
  versions, architecture, vendor, size, SHA-256, and required SUSE signing key.
  An unsigned RPM or a digest-only success is rejected.
- The monitoring package's historical export repository is named
  `pool-leap-15.4`, but its source project is `SUSE:SLE-15:Update`, its vendor is
  SUSE LLC, and its original SUSE signature is verified. It is an SLE binary,
  not a substituted Leap build or an added Leap repository.
- `system-user-nagios` is built natively on SLES from the unmodified, pinned
  `server:monitoring` source in
  [the user-package manifest](../packaging/sles15sp4-user-source.json). It creates
  the real user/groups using the upstream SLES-compatible script, rather than
  pretending to satisfy the dependency. Its RPM and source RPM accompany NRPE.
- SLE repositories take precedence over the SP4 backports repository. The
  `systemd-presets-branding-SLE` package is selected explicitly, alongside
  `util-linux-systemd`, which supplies the required `logger` capability.

This removes the need to download the full ISO merely to obtain these few
dependencies. Distribution binary dependencies remain SLE/Package Hub packages;
the local packages are compiled on SLES. No Leap, MicroOS, SP7, HA, or SAP
repository is added as a replacement package basis.

You can still provide a minimal SLES 15 SP4 OCI base with matching repositories configured,
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

## Optional official installation media

Use the official [SLES download page](https://www.suse.com/download/sles/), choose
**15 SP4**, **AMD64/Intel 64**, and **Full Media1**. The small Online installer
does not contain the required package repositories. The GM file is named
`SLE-15-SP4-Full-x86_64-GM-Media1.iso` and is approximately 13 GB; compare its hash
with the matching checksum published by SUSE before extracting it.

Extract the complete medium, preserving directory and file names, into a local
folder such as `C:\SLES15-SP4`, outside the checkout. Then run:

```powershell
python3 nrpe.py verify sles15sp4 --sles-media "C:\SLES15-SP4"
python3 nrpe.py test sles15sp4 --sles-media "C:\SLES15-SP4"
```

Alternatively set `SLES_MEDIA_DIR` to the extracted directory. This also works for
direct Compose invocations, which bypass the controller's media preflight. An
ISO filename itself is not accepted; no privileged mount or OS installation is
performed by the controller.

The controller checks the product metadata for SLES 15 SP4 x86_64 and requires
signed repository metadata. Zypper performs the actual signature verification.
Only Basesystem, Server Applications, Development Tools, Legacy, Product SLES,
and the medium's root repository can be registered. Other included products such
as HA, SAP, HPC, and desktops are not activated. The media are read-only named
BuildKit contexts during image builds and read-only bind mounts for container
runs. They are not copied into final image layers, but BuildKit may still cache
large contexts: allow adequate disk space for extraction and Docker's cache.

Compose 2.17+ and BuildKit are required. The empty context in
`packaging/empty-media` preserves the regular online workflow when no medium is
selected. ISO files and `local-media/` are excluded from Git and the primary
Docker context. The project does not accept subscription terms, store download
authorization URLs, or automatically download a multi-gigabyte ISO.

Historical SP4 repositories may contain old metadata and expired signing-key
copies. Restore trust only through authoritative renewed keys and matching
repositories. Do not disable TLS, package signatures, dependency checks, or
metadata validation to make a build succeed. Corporate proxies may require an additional trusted CA. Use
`python3 nrpe.py verify sles15sp4 --ca-cert "C:\Certificates\Company-Root.cer"`
to supply one optional public PEM/DER certificate before repository access.
See [company CA setup](network.md#optional-company-ca-certificate) for Docker
daemon trust limits; keep TLS verification enabled.

## Build and test contract

The builder installs the original spec's build requirements and uses
`rpmbuild -ba`. Before export it checks RPM name, version/release, architecture,
executable and configuration paths, generated configure macros, and the disabled
argument default in the packaged configuration. Successful outputs go to
`output/sles15sp4/`:

```text
nrpe-4.1.1-150400.95.2.withargs1.x86_64.rpm
nrpe-4.1.1-150400.95.2.withargs1.src.rpm
system-user-nagios-1.0.0-0.noarch.rpm
system-user-nagios-1.0.0-0.src.rpm
source-manifest.json
user-source-manifest.json
bootstrap-manifest.json
SHA256SUMS
```

The custom RPM is a locally built, unsigned artifact. Its checksum binds the
integration test to the server and companion package bytes; repository dependencies still undergo normal
zypper signature verification. The test installs only declared runtime
requirements, excluding RPM's internal capabilities and capabilities supplied by
the server RPM itself, then installs the custom
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

On a fresh server, the companion `system-user-nagios` RPM may be needed alongside
NRPE if the configured SLES sources do not supply it. On a server that already
has a suitable user package installed, keep the existing package rather than
downgrading it to this locally built companion. The source RPMs and manifests
document the inputs; custom outputs are not signed enterprise release packages.
