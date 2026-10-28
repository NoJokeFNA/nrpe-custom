# Release preparation plan

Status: local SLES 12 SP3 migration, updated 2026-10-28. The actual deployment
was confirmed as SLES **12.3**, NRPE 2.15-4.24 and the OpenSSL 1.0 ABI. The
previous SLE-15 targets were based on an incorrect platform assumption; their
published test evidence remains historical and is not relabeled.

Current local work stays on a topic branch. Pushes, PR creation and merges into
develop or master require an explicit maintainer request. Changes are handled
sequentially. See [Git workflow](git-workflow.md).

## Current scope and implementation

| Area | State / evidence |
| --- | --- |
| Debian 11–14 amd64 | Existing source discovery, package build/source export and TLS integration retained |
| SLES 12 SP3 x86_64 | Genuine digest-pinned 12.3 base, original SLE-12 Server/SDK dependencies, native compiler and RPM 4.11.2 |
| Input preparation | Separate modern Python download stage; hashes checked before transfer, native SUSE signature/identity checks before installing any RPM |
| NRPE | Version 4.1.1, local Release 0.withargs1; runtime arguments remain disabled by default and Bash substitution disabled |
| SLES support | Native nagios-rpm-macros and system-user-nagios builds; matching NRPE client, all three SRPMs and original source sets exported |
| TLS compatibility | Native 12.3 test passed TLS 1.2 with mandatory client certificates using the original OpenSSL 1.0.2j ABI; TLS 1.3 is not claimed |
| Source/license gate | Requires original hashes, clean commit and fresh verify evidence; client/server source relationship, macro source/license and all assets checked |
| Notices | MIT for independently authored project work; upstream GPL/OpenSSL, companion MIT and macros BSD notices retained |
| Deployment documentation | [Installation](installation.md), [rollback](updates-and-rollback.md), [FAQ](faq.md) and [SLES guide](sles12sp3.md) |
| Signatures | [Ed25519 signing support](release-signing.md) implemented; production enrollment and a verified signed release remain open |
| Branch protection | Master/develop rules applied and verified in the previous integration; no remote setting changes in this task |

## Remaining work, in priority order

- [x] Complete local clean-checkout source/archive checks for the 12.3 port; exact
  implementation commit/run recorded below. No hosted CI run is triggered without
  a requested push. Repeat the gate for the eventual release commit.
- [ ] Complete [Windows Docker Desktop practical checks](practical-validation.md#windows-docker-desktop).
- [ ] Complete [Debian and SLES test VMs](practical-validation.md#debian-and-sles-test-vms):
  real systemd/reboot, plugins and upgrade/rollback from the saved NRPE 2.15 package.
- [ ] Enroll a maintainer-controlled release key, configure the signing secret and
  authenticate a signed release after an explicitly requested master promotion.
- [ ] Continue recurring [maintenance review](maintenance.md#human-review-cadence),
  including the legacy SLES 12 SP3 lifecycle and upstream NRPE updates.

The dated [2026-10-27 review](maintenance-reviews/2026-10-27.md) records the old
SP4 scope. SLES 12 SP3's published general/LTSS end dates are 2019-06-30 and
2022-06-30; archive access is not an extension of vendor support. See the
[SUSE lifecycle](https://www.suse.com/lifecycle/).

## Source and publication requirements

Each target needs a complete fresh build/package/install/TLS verify run tied to
the exact clean workflow commit and unchanged binary/source hashes. Runtime-only
reports and results from the wrong operating-system target cannot qualify.

Debian exports the custom DSC and every referenced upstream/packaging archive.
SLES exports server/client/user binaries, the NRPE/user/macros source RPMs, all
original OBS files/history and all four pinned manifests. Include the actual
component notices, project MIT license, [inventory](../THIRD_PARTY.md), workflow
sources, sanitized evidence and checksums. Do not ship credentials, company CAs,
private keys, raw environments/logs, container images or dependency RPM bundles.

The stage/archive verifier rejects missing/extra/changed files, unsafe archive
entries, wrong versions or notices, and stale/different source evidence. All five
current targets are required for a complete release. The master-push workflow
publishes only after its full gate; an unrequested promotion is never implied
by implementing or locally validating a change.

## First published release: recorded evidence

On 2026-10-27, [PR #1](https://github.com/NoJokeFNA/nrpe-custom/pull/1)
merged into develop and [PR #2](https://github.com/NoJokeFNA/nrpe-custom/pull/2)
promoted it to master through the active protection rules. The merged topic
branch was deleted; master and develop were retained.

[Release build-4-517fbfb97d7e](https://github.com/NoJokeFNA/nrpe-custom/releases/tag/build-4-517fbfb97d7e)
was published from commit `517fbfb97d7efb7b19570c509fa2287e8251d412` by
[successful run 40571542343](https://github.com/NoJokeFNA/nrpe-custom/actions/runs/40571542343).
The run passed the Linux/Windows Python 3.9/3.14 unit matrix, shell/Compose checks,
dependency audit, all five fresh build/install/TLS tests, source and license
validation, archive assembly and publication. Local preparation also passed
132 unit tests with the pinned menu requirements.

| Target | Published custom server version |
| --- | --- |
| Debian 11 | `4.0.3-1+withargs1` |
| Debian 12 | `4.1.0-1+withargs1` |
| Debian 13 | `4.1.3-1+withargs1` |
| Debian 14 | `4.1.3-1+withargs1` |
| SLES 15 SP4 | `4.1.1-150400.95.2.withargs1` |

All 11 published assets were independently downloaded after publication. Their
complete file set and SHA-256 hashes matched `SHA256SUMS`; all five target
archives passed the archive verifier and their manifests matched `release.json`
and the release commit. This is integrity and completeness evidence, not a signed
attestation or a native Windows/systemd/production deployment test.

The SLES source/license questions are closed for the pinned inputs. Native
Windows Docker Desktop and real Debian/SLES VM tests remain unrun; see the
[practical validation procedure](practical-validation.md). The available Linux
cloud environment has no Windows host, VM hypervisor or supplied test-VM access.

## Local SLES-12 migration evidence

Initial native run `20261028T083230-86e80546` passed the genuine SLES-12 build,
fresh-container installation and certificate-authenticated TLS 1.2 argument
checks. It does not qualify as clean-checkout release provenance: further local
source/guard/documentation changes followed.

Implementation commit `7aa2f316c3e9b1ce26933929ddf37ffa1eeeeb88` then passed
clean-checkout run `20261028T090944-fe957b65`: native build, package checks, fresh
installation and both argument policies over authenticated TLS 1.2. The source
and archive gate passed for that exact commit/run, comparing all three SRPMs
against the pinned originals and checking licenses, manifests, the matching
client and the full 48-file archive. The candidate is local under
`.nrpe/sles12-local-candidate/`; nothing was published.

An isolated OpenSSL 3.5.7 client also completed a real NRPE request over
`DHE-RSA-AES256-GCM-SHA384` with default security settings, server hostname/chain
verification and a separate client certificate. A missing client certificate
was rejected. The [SLES TLS configuration](configuration-examples.md#hosts-tls-and-fixed-commands)
records the NRPE-specific DH initialization requirement without permitting
anonymous ciphers. All 142 unit tests, shell syntax, Compose/doctor checks and
documentation links/snippets passed. A SLE-15 base was explicitly rejected.

These results identify the implementation commit, not every later documentation
or integration commit. Fresh per-commit reports and candidate archives remain
local under `.nrpe/`; the exact eventual release commit must pass the gate again.

Syntax/unit tests are separate from package/runtime proof. Container tests do
not establish production systemd, TLS, firewall, plugins or rollback readiness.
Do not deploy a SLE-15 binary or replace the server's system OpenSSL to imitate
this test. See [practical validation](practical-validation.md).
