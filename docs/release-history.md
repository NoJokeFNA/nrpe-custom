# Release history and verification evidence

Historical results apply only to their recorded commits, artifacts and targets.
Current deployment guidance is in the [installation guide](installation.md);
open work is tracked in the [release plan](release-plan.md).

## SLES 12 SP3 release, 2026-10-28

[PR #6](https://github.com/NoJokeFNA/nrpe-custom/pull/6) integrated the native
SLES 12 SP3 target into develop. [PR #7](https://github.com/NoJokeFNA/nrpe-custom/pull/7)
promoted develop to master at the maintainer's request. Both long-lived branches
were retained; only the merged topic branch was removed.

[Release build-12-db3e0a10776f](https://github.com/NoJokeFNA/nrpe-custom/releases/tag/build-12-db3e0a10776f)
was published from `db3e0a10776f724df1c4583f56214e90f0fc3ce9` by
[successful run 40668832448](https://github.com/NoJokeFNA/nrpe-custom/actions/runs/40668832448).
Linux/Windows unit tests, shell/Compose validation, dependency audit, all five
fresh build/install/TLS tests, source/license gates and archive assembly passed.

| Target | Published custom server version |
| --- | --- |
| Debian 11 | `4.0.3-1+withargs1` |
| Debian 12 | `4.1.0-1+withargs1` |
| Debian 13 | `4.1.3-1+withargs1` |
| Debian 14 | `4.1.3-1+withargs1` |
| SLES 12 SP3 | `4.1.1-0.withargs1` |

All 11 published assets were downloaded independently after publication and
matched the complete `SHA256SUMS`. All five target archives passed verification
and matched `release.json`; the workflow source archive matched the exact master
commit. Release signing was off; these checks establish checksum integrity, not
an independently authenticated signature. VM/systemd/reboot/update/rollback and
Windows Docker Desktop scenarios remain open.

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
