# SLES 15 SP3 RPM target

The maintainer corrected the affected platform to **SLES 15 SP3** on 2026-10-28.
The previous automation targeted SP4, not SP5. This change replaces that active
SLES target with `sles15sp3`; the four Debian targets are unchanged. Previously
published SP4 packages and release tags are not overwritten or renamed.

```sh
python3 nrpe.py verify sles15sp3
python3 nrpe.py test sles15sp3
```

Use `--rebuild` when intentionally replacing existing local SP3 outputs. Do not
copy an old SP4 RPM into the SP3 output directory or rename its version.
See [installation](installation.md#sles-15-sp3) and the [service FAQ](faq.md).

## Base image and matching dependencies

Both Dockerfiles use the genuine `registry.suse.com/bci/bci-base:15.3` image.
It was downloaded and its `/etc/os-release` checked: `ID=sles`,
`VERSION_ID=15.3`, x86_64. The setup/build/test scripts reject other service
packs. No Leap, SP4, SP5 or SP7 base/repository is substituted.

The setup adds the matching signed
`openSUSE:Backports:SLE-15-SP3/standard` repository, at lower priority than the
base's SLE repositories. The base's configured SUSE repositories supply the
compiler and ordinary dependencies. TLS and repository signatures stay enabled.
An authorized minimal SP3 base/mirror can be selected with `SLES_BASE_IMAGE`;
it must retain a real SP3 identity and matching repositories, without preinstalled
NRPE or compilers in the runtime test image.

The [bootstrap manifest](../packaging/sles15sp3-bootstrap.json) pins original
SUSE dependencies, checked by size, SHA-256, vendor, version, architecture and
known SUSE signing key:

- `nagios-rpm-macros-0.14-1.15.noarch.rpm` from the SUSE SLE 15 GA pool.
- `monitoring-plugins-common-2.2-3.6.4.x86_64.rpm` from the official
  `SUSE:SLE-15:Update/pool-leap-15.3` export. The repository's historical export
  name includes Leap; the package is an original SUSE-signed SLE binary, not a
  Leap substitute or an added Leap repository.

The common plugin RPM has SHA-256
`704bc19e030cab7a19ceb0191ef3c3369aae2e865f280fb0b66361dc65830819`.
The previous SP4 dependency version `2.3.1-3.9.2` is not reused.

## Pinned NRPE sources and custom revision

The [NRPE source manifest](../packaging/sles15sp3-source.json) retains reviewed
OBS source revision `835292739a5736a9d8f0460f670b6f15`, upstream NRPE `4.1.1`.
Its files are independent of a binary service-pack repository: the spec is
rebuilt natively against SP3. This is not a claim to reconstruct an unknown
historical SP3 binary or reproduce the old SP4 release number.

The new local custom Release is `0.withargs1`, producing
`nrpe-4.1.1-0.withargs1.x86_64.rpm`. It deliberately does not copy the former
SP4 release `150400.95.2`. Version/Release are set in the spec before compilation.
The narrow recipe transformation preserves command-argument support, removes
Bash command substitution and keeps runtime arguments disabled by default.

The real `system-user-nagios-1.0.0-0.noarch.rpm` is built on SP3 from the
[unchanged pinned companion source](../packaging/sles15sp3-user-source.json).
It is not a fake dependency provider. Both binary/source RPM pairs, original OBS
inputs/history, all three manifests and the binary `SHA256SUMS` are exported to
`output/sles15sp3/`. The [license review](sles-license-review.md) concerns the
same exact upstream/companion source bytes reused for this rebuild; the
[notices](../packaging/licenses/sles15sp3/README.md) accompany release archives.

`--pull` refreshes images, not the pinned source revision. Source/license changes
require review and corresponding manifest/hash updates.

## Optional official SP3 installation media

The normal workflow uses online repositories. If matching repositories are
unavailable, obtain official SP3 x86_64 **Full Media1** through an authorized
[SUSE download channel](https://www.suse.com/download/sles/), verify SUSE's
published checksum and extract it outside the checkout. The small Online
installer is insufficient. No media is downloaded automatically and no
subscription terms are accepted by the tool.

```powershell
python3 nrpe.py verify sles15sp3 --sles-media "C:\SLES15-SP3"
```

Alternatively set `SLES_MEDIA_DIR`. The host and container helpers require SP3
product metadata, x86_64, the full Basesystem repository and signature files.
SP4/SP5 media, Leap and other architectures are rejected. Only the approved
SLES product/modules are registered, mounted read-only for build and runtime.
Zypper performs actual repository signature verification. Media layout unit
tests use synthetic files and do not establish real ISO authenticity.

For a company CA, add `--ca-cert` or configure `NRPE_CA_CERT` as described in
[network trust](network.md#optional-company-ca-certificate). Registry/BuildKit
trust is separate from container repository trust. Never bypass signature or
TLS checks to compensate for archived infrastructure.

## Validation and support boundaries

On 2026-10-28, local run `20261028T073123-23a6dc86` passed the full SP3 build,
package validation, fresh-container installation and both disabled/enabled
argument cases over TLS for `4.1.1-0.withargs1`. The original SUSE signatures and
identities of both bootstrap packages were verified. The run used the official
SP3 BCI image with the optional cloud proxy CA supplied through `--ca-cert`.
Previous SP4 results remain historical evidence, separate from this SP3 run.

A successful verify must compile on SP3, validate both packages, install them in
a separate fresh SP3 runtime image and exercise TLS requests with arguments
rejected by default and exact responses for two argument pairs after deliberate
runtime activation. Tests run NRPE directly and do not prove real-server systemd,
reboot, firewall or production TLS behavior. See [practical validation](practical-validation.md).

The [SUSE lifecycle](https://www.suse.com/lifecycle/) lists SP3 general support
end as 2022-12-31 and LTSS end as 2025-12-31. This is a legacy compatibility
build requested for the affected deployment; available archives do not extend
vendor maintenance or provide enterprise support rights for custom packages.
