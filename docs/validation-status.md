# Validation status: 29 October 2026

This record distinguishes automated checks, operator reports and work blocked by
external prerequisites. It is not a certificate of production readiness.

## Completed in the development environment

- A read-only Bash target-server diagnostic was tested with isolated fixtures,
  including missing plugins, include cycles and configuration shell expressions
  that must never be executed. This does not install NRPE on this workstation.
- CSS consolidation was compared against the previous rendered site across six
  routes, four viewport widths and normal/expanded-navigation/focus states.
  The 72 combinations matched the compared computed layout/appearance properties
  after normalizing the footer's source label.
- Browser regression checks cover responsive layout, independent sidebar scroll,
  footer alignment, field-note anchors/current section, no-JavaScript article
  links, FAQ filtering, search and keyboard/mobile navigation. They use Chromium
  in the development environment; CI configuration also runs them.
- The [TLS procedure](tls-validation.md) separates transport, encryption, server
  verification and client-certificate enforcement. Documentation is not a
  completed test of the operator's certificate policy.

Record the actual commit and CI results before merging or publishing. Local
passes do not establish that a remote CI run has already completed.

## Operator-reported SLES results

The [field note](../website/content/sles12-handshake.md) records NRPE 4.1.1 active
under systemd and successful remote version/load/Swap/NTP checks after fixing
firewall access, removing client `-n` and installing missing plugins. The raw
host details are private. These reports do not supply a verified binary checksum,
mandatory certificate/hostname verification, reboot, upgrade or rollback record.

## Blocked: isolated host lifecycle and Windows Docker Desktop

The execution environment has no `/dev/kvm`, QEMU/libvirt tooling, configured
VPN or supplied access to isolated Debian/SLES hosts. The operator has described
a SLES test host, but no management access was provided to this task. No host
reboot, package upgrade/downgrade or remote configuration change was performed.
Do not reinterpret existing container checks as those results.

Use the [deployment worksheet](deployment-validation-template.md) per target:
record the baseline package/checksum/configuration and recovery snapshot, install
the candidate, test service/plugins/access/TLS, reboot the isolated host, then
perform upgrade and rollback between distinct verified versions. Use the
[Windows checklist](practical-validation.md#windows-docker-desktop) on an actual
Windows Docker Desktop host. Leave scenarios blocked/not run until real evidence
is supplied. A running Linux container is not a substitute for these prerequisites.

## Release signing prerequisite

No maintainer public release key has been enrolled in the tracked signer file.
Production signing cannot be enabled meaningfully until the maintainer controls
the key/backup, independently confirms its public fingerprint, and configures
the CI secret and signing mode. Follow [release signature setup](release-signing.md).
A disposable-key test validates signing code, not production enrollment. No
master promotion or new package release is authorized by this status record.
