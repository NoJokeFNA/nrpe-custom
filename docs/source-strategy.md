# Source and patch strategy

## Decision

Keep the native Debian and SLES packaging as the production build basis.
Cloning upstream NRPE is useful for investigating and developing a C patch,
but is not necessary to apply patches and does not simplify distribution
integration by itself. The current workflow intentionally changes packaging
options rather than maintaining a separate NRPE implementation.

The SLES operator report does not demonstrate a new C defect: client 4.1.1 was
installed while the daemon remained 2.15. Correct the server installation and
validate authenticated TLS before proposing an upstream replacement.

## Evaluated upstream checkout

On 2026-10-29 the official upstream `nrpe-4.2.0` tag was cloned and inspected at
commit `cf47f059637fe4ad23dd4a5f2612e2787ce7c09d`. The source contains legacy
OpenSSL compatibility branches. Inspection and a clean checkout do not prove
that 4.2.0 builds, installs or survives upgrades/reboots on SLES 12 SP3.

A pinned checkout for patch development can be prepared separately:

```sh
git clone --branch nrpe-4.2.0 --single-branch \
  https://github.com/NagiosEnterprises/nrpe.git nrpe-upstream
cd nrpe-upstream
git checkout --detach cf47f059637fe4ad23dd4a5f2612e2787ce7c09d
git rev-parse HEAD
git status --short
```

Match the full commit to independently reviewed upstream evidence before use.
The clone alone does not authenticate a tag or replace source-integrity checks.
Never build a release from a moving `master` branch or run `make install` over a
package-managed daemon. The example is a development checkout, not a new
supported build mode or target-server installation instruction.

## Introducing a necessary C change

1. Reproduce the defect with the correctly installed server and a sanitized
   protocol/configuration case; check upstream fixes and distribution backports.
2. Develop the smallest patch against the exact reviewed source revision.
   Preserve authorship, licensing and corresponding source. Check that the
   patch applies cleanly; fail rather than silently applying a fuzzy substitute.
3. Carry the reviewed change through native packaging: Debian's patch series
   and the SLES spec's patch declarations/application. Keep distribution paths,
   users, services, dependencies and configuration migration behavior.
4. Update reviewed source hashes/manifests and custom package revision as
   necessary. Export the patch with the complete corresponding source and
   notices; a Git link alone is not a replacement for those source archives.
5. Run genuine matching-OS builds, fresh installation and TLS/argument tests
   for every affected target. Follow with real systemd, update, rollback and
   reboot checks on isolated hosts before claiming deployment readiness.

Debian continues to discover its suite's official source. SLES remains on the
reviewed 4.1.1 OBS source recipe until an independently reviewed migration is
justified. A future 4.2.x SLES prototype must retain genuine SP3 libraries,
source/signature verification and native RPM integration. Current container
passes do not validate a different upstream revision.

See [architecture](architecture.md), [maintenance](maintenance.md),
[SLES native build](sles12sp3.md) and [practical validation](practical-validation.md).
