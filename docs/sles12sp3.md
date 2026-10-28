# SLES 12 SP3 RPM target

The affected deployment is **SLES 12 SP3**, confirmed by `/etc/os-release` on
2026-10-28. Its original package is NRPE `2.15-4.24`, linked to
`libssl.so.1.0.0` and `libcrypto.so.1.0.0`. Previous SLES 15 SP3/SP4 test results
do not validate this platform. The active target is now `sles12sp3`; old releases
are not overwritten or relabeled.

```sh
python3 nrpe.py verify sles12sp3
python3 nrpe.py test sles12sp3
```

Use `--rebuild` to deliberately replace existing local outputs. Old SLE-15 RPMs
must not be installed or copied into this target's output directory.

## Build architecture and matching inputs

The native build and runtime stages use SUSE's genuine image, pinned to:

```text
registry.suse.com/suse/sles12sp3@sha256:0995dbf051274a3a5baf19c7f94ce7ebe69d7aa91f7b3b22248bd06d7122e53a
```

Its identity is `ID=sles`, `VERSION_ID=12.3`, x86_64, with RPM 4.11.2 and
OpenSSL 1.0.2j. `SLES_BASE_IMAGE` can select an approved equivalent, but the
native guard rejects other distributions/releases and requires the OpenSSL 1.0
ABI. The runtime image contains no compiler or preinstalled NRPE server.

The historical image has no configured repositories and the old SP3 backports
index is empty. Instead, the [bootstrap manifest](../packaging/sles12sp3-bootstrap.json)
pins original SLE-12 GA/SP3 Server and SDK RPMs available through SUSE's public
OBS API. Each entry records its original URL, size, SHA-256, name, version,
architecture, vendor and SUSE signing key. No SLE-15 or Leap package is used.

A separate Python download stage fetches and hash-checks those RPMs and the
pinned OBS sources. A company CA is added only to that process's TLS context;
it is not copied into target packages. The actual SLES stage independently
checks the pinned RPM hashes, required SUSE signatures and package identities
before installing anything. Downloads are not treated as signature verification.
Native installation uses the complete local dependency set, retaining normal
RPM dependency checks; no registration credentials or license terms are supplied
or accepted by this workflow. No system OpenSSL replacement is required.

Python is not needed in the old target image. NRPE and its support packages are
compiled/packaged by SLES 12's own tools. The former `--sles-media` option and
SLE-15 module/ISO layout were removed; an ISO is not required by this workflow.

## Sources and package identities

- [NRPE](../packaging/sles12sp3-source.json): reviewed immutable OBS revision
  `835292739a5736a9d8f0460f670b6f15`, version `4.1.1`, local Release `0.withargs1`.
  Command arguments remain compiled in, runtime-disabled by default; Bash command
  substitution stays disabled. This is a native rebuild, not a reproduction of
  the old installed NRPE 2.15 package.
- [Nagios build macros](../packaging/sles12sp3-macros-source.json): immutable OBS
  revision `a911087cc73b87e04465861110d43754`, version `0.14-0`, built natively.
  The upstream spec explicitly supports SLES 12. This build dependency is not
  faked or supplied by a SLE-15 binary.
- [Nagios user package](../packaging/sles12sp3-user-source.json): pinned original
  `system-user-nagios 1.0.0-0`, built natively after the macros. Existing users
  and groups are handled by the original package scripts.

`output/sles12sp3/` contains the server, matching `monitoring-plugins-nrpe` client,
real user-package RPM, all three source RPMs, four input manifests, original OBS
files including history, and `SHA256SUMS` for all three binary RPMs. The macros'
build-only binary is not a runtime dependency or release asset. Its corresponding
source and BSD notice are included for rebuilding the workflow.

The source/license gate checks every original input and SRPM member, the
client/server source/version relationship, the bootstrap manifest and component
notices. See [license evidence](sles-license-review.md) and the
[notice directory](../packaging/licenses/sles12sp3/README.md).

## TLS and the original handshake failure

For the user-performed pre-upgrade diagnostic with NRPE 2.15 and `check_nrpe`
4.1.0, see [isolating an NRPE TLS handshake failure](sles12sp3-plaintext-diagnostic.md).
It documents a separate temporary plaintext instance, the successful result and
cleanup using anonymized hosts and documentation addresses, without modifying
the production service or reloading systemd.

NRPE 2.15 uses legacy anonymous DH. Merely enabling services or adding modern
configuration directives does not add certificate support to that old binary.
This build supplies NRPE 4.1.1 and a matching client against the existing OpenSSL
1.0 ABI. The integration test explicitly requires **TLS 1.2**, excludes anonymous
authentication, requires a client certificate and checks rejected/enabled command arguments.
It does not weaken cipher settings or disable certificate verification to make
the test pass. TLS 1.3 is not supported by OpenSSL 1.0.2 and is not claimed.

For the deployed server, back up the old package/configuration, review included
files and configure compatible CA/server/client certificates on both ends.
Build-time `--ca-cert` does not provision production NRPE TLS. The
[FAQ](faq.md) distinguishes service startup from TLS compatibility.
Use the [SLES-specific DHE-RSA configuration](configuration-examples.md#hosts-tls-and-fixed-commands):
NRPE 4.1.1 needs DH initialization enabled together with an explicit cipher list
that excludes anonymous authentication. The modern-client test passed with
OpenSSL 3.5.7, verified server hostname/chain and a separate required client
certificate; a connection without that client certificate was rejected.

## Recorded validation and limits

Local run `20261028T083230-86e80546` passed native NRPE build, package checks,
fresh SLES-12 installation and TLS-1.2 requests with mandatory client certificates
and both argument policies. Subsequent exact commit/run and candidate evidence
is kept locally under `.nrpe/`; a fresh clean-checkout run is required for each
release candidate. Earlier unsuccessful local runs
stopped for missing genuine dependencies/cleanup handling and were not counted
as passes. No signing, dependency or TLS checks were bypassed.

Container tests run NRPE directly. They do not validate real-server systemd,
reboot, site-specific commands, production certificates, update or rollback.
Use [installation](installation.md#sles-12-sp3), [rollback](updates-and-rollback.md)
and [practical validation](practical-validation.md) before deployment.

The [SUSE lifecycle](https://www.suse.com/lifecycle/) lists SLES 12 SP3 general
support end as 2019-06-30 and LTSS end as 2022-06-30. This is a requested legacy
compatibility build, not extended vendor maintenance or certification. Historical
package/image availability can change and does not guarantee security support.
