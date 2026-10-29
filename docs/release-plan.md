# Release preparation plan

Status: SLES 12 SP3 support published, updated 2026-10-29. The actual deployment
was confirmed as SLES **12.3**, NRPE 2.15-4.24 and the OpenSSL 1.0 ABI.

New work stays on a topic branch. Pushes, PR creation and merges into
develop or master require an explicit maintainer request. Changes are handled
sequentially. See [Git workflow](git-workflow.md).

## Current scope and implementation

| Area | State / evidence |
| --- | --- |
| Debian 11–14 amd64 | Published build/install/TLS and source/archive checks passed |
| SLES 12 SP3 x86_64 | Published native build/install/TLS and source/archive checks passed on genuine 12.3 |
| Input preparation | Separate modern Python download stage; hashes checked before transfer, native SUSE signature/identity checks before installing any RPM |
| SLES NRPE | Version 4.1.1, local Release 0.withargs1; runtime arguments remain disabled by default and Bash substitution disabled |
| SLES support | Native nagios-rpm-macros and system-user-nagios builds; matching NRPE client, all three SRPMs and original source sets exported |
| TLS compatibility | Native 12.3 test passed TLS 1.2 with mandatory client certificates using the original OpenSSL 1.0.2j ABI; TLS 1.3 is not claimed |
| Source/license gate | Requires original hashes, clean commit and fresh verify evidence; client/server source relationship, macro source/license and all assets checked |
| Notices | MIT for independently authored project work; upstream GPL/OpenSSL, companion MIT and macros BSD notices retained |
| Deployment documentation | [Installation](installation.md), [rollback](updates-and-rollback.md), [FAQ](faq.md) and [SLES guide](sles12sp3.md) |
| Signatures | [Ed25519 signing support](release-signing.md) implemented; production enrollment and a verified signed release remain open |
| Branch protection | Master/develop retained; owner migrated required minimum-Python checks to 3.11 on 2026-10-29 |
| Workstation dependencies | Python 3.11 minimum; prompt-toolkit 3.0.53, wcwidth 0.9.4 and Markdown 3.11.2 reviewed and tested on Linux/Windows CI |
| Deployment clarification | Server/client RPM identities, complete SLES TLS policy and [operator checklist](sles12sp3-deployment-checklist.md); reported attempt still ran server 2.15 |
| Operator diagnostics | Read-only Bash inspection with no plugin execution; see [troubleshooting](troubleshooting.md#read-only-target-server-inspection) |
| Website regression checks | CSS rules/colors consolidated; responsive/navigation/search/keyboard checks run through the website CI workflow |
| TLS validation | [Ordered procedure](tls-validation.md) distinguishes connectivity, encryption, server identity and mandatory client credentials |
| Source strategy | [Pinned upstream clone evaluated](source-strategy.md); preserve native distribution packaging and reviewed patches |

## Remaining work, in priority order

- [ ] Complete [Windows Docker Desktop practical checks](practical-validation.md#windows-docker-desktop).
- [ ] Complete [Debian and SLES test VMs](practical-validation.md#debian-and-sles-test-vms):
  real systemd/reboot, plugins and upgrade/rollback from the saved NRPE 2.15 package.
  No isolated host management access is available to this task; the
  [per-target worksheet](deployment-validation-template.md) is prepared and the
  lifecycle scenarios remain blocked/not run.
- [ ] Enroll a maintainer-controlled release key, configure the signing secret and
  authenticate a signed release after a separately requested master promotion.
- [ ] Continue recurring [maintenance review](maintenance.md#human-review-cadence),
  including the legacy SLES 12 SP3 lifecycle and upstream NRPE updates.

SLES 12 SP3's published general/LTSS end dates are 2019-06-30 and
2022-06-30; archive access is not an extension of vendor support. See the
[SUSE lifecycle](https://www.suse.com/lifecycle/).

## Published evidence and future releases

The current [SLES 12 SP3 release](release-history.md#sles-12-sp3-release-2026-10-28)
passed all five target gates and publication; see the linked release history
for its exact source commit and artifacts.

Each future release must pass the [publication gate](releases.md#build-and-publication-gate)
for its exact clean commit. Previous passes, local tests and runtime-only reports
cannot replace fresh release evidence. Publication and master promotion still
require the maintainer's explicit request.

## First published release: recorded evidence

Moved to the [release history](release-history.md#first-published-release-recorded-evidence).

## Local SLES-12 migration evidence

Moved to the [release history](release-history.md#local-sles-12-migration-evidence).

The [current validation status](validation-status.md) records completed local
checks, operator-reported results and exact external prerequisites.
