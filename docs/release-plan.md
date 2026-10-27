# Release preparation plan

Status: first automated release published, verified 2026-10-27. MIT is adopted
for independently authored project work. Successful master pushes publish only
after complete five-target verification. Changes follow topic PRs into develop,
then a develop-to-master promotion PR. Both long-lived branches are protected;
repository visibility is unchanged.
Creating or merging a master promotion requires an explicit maintainer request;
ordinary implementation and integration stop at develop.
See [Git workflow](git-workflow.md) and [release automation](releases.md).

## Scope and current state

The intended assets are unofficial custom Debian server packages and the SLES
15 SP4 NRPE/user packages, with corresponding sources, notices, build scripts,
checksums, and artifact-bound test results. Container images, dependency package
bundles, and SLES media are outside this scope.

| Item | State | Evidence or next action |
| --- | --- | --- |
| CLI, menu, workflow logs and artifact-bound test results | Implemented and release-verified | [Workflow reference](workflow.md); fresh verification remains required for every release |
| Company CA handoff on Windows | Implemented; user confirmed the fix | Environment-backed BuildKit secret, PEM/DER validation and SHA-256 cache identity |
| TLS failure guidance | Implemented | Missing/supplied CA and other TLS failures; separate Docker/BuildKit trust documented |
| Custom package installation instructions | Documented | [Installation guide](installation.md), linked from README and SLES notes; full deployments use upstream manuals |
| Operational and maintenance guidance | Documented | [Update/rollback](updates-and-rollback.md), [configuration examples](configuration-examples.md), and [support policy](maintenance.md) |
| Fast CI and dependency monitoring | Passing for the first release | Linux/Windows Python 3.9/3.14, shell/Compose checks and dependency audit; weekly update proposals still need human review |
| Project license | Adopted | [MIT license](../LICENSE); third-party components retain their own licenses |
| Warranty and liability notice | Documented | README and [security guidance](security.md), subject to applicable law; no security or availability guarantee |
| Third-party license inventory | Reviewed inputs and first release validated | [Inspected evidence](../THIRD_PARTY.md) and [SLES review](sles-license-review.md); repeat review for changed source/license evidence |
| Debian corresponding-source export | Implemented and validated on all four targets | `scripts/export_debian_sources.py`; full verify runs and independent source reconstruction passed |
| SLES corresponding sources and notices | Original OBS export and validation implemented | Includes history files, both SRPMs and the [notice directory](../packaging/licenses/sles15sp4/README.md) |
| Release completeness and test gate | Passed for the first published release | Clean source identities, source/binary hashes, complete five-target assembly and independent downloaded-asset checks |
| GitHub releases | Active; first release published | Draft upload then publication; no feature/develop/PR publication, no container/media redistribution |
| Long-lived branch protection | Active and verified on both branches | Deletion/force-push protection, PR requirement, resolved review threads, required fast checks and no bypass actors; [verification](git-workflow.md#server-side-protection-one-time-administrator-action) |

## Remaining work, in priority order

- [x] Update the preparation status after the first published release and verify
  the active branch rules and downloaded release assets.
- [ ] Complete the [Windows Docker Desktop practical checks](practical-validation.md#windows-docker-desktop)
  for company CA trust, Windows paths, console behavior and cancellation.
- [ ] Complete the [disposable-server checks](practical-validation.md#debian-and-sles-test-vms)
  for systemd, reboot, actual plugins, update and rollback on matching Debian/SLES VMs.
- [ ] Add publisher authentication through signed checksums or GitHub artifact
  attestations. [SSH Ed25519 support and consumer verification](release-signing.md)
  are implemented for develop integration; production key enrollment,
  owner configuration and a verified signed release remain outstanding.
  Current published hashes provide integrity checks, not publisher authentication.
- [ ] Continue the recurring [maintenance review](maintenance.md#human-review-cadence):
  upstream advisories, dependency proposals, source/license updates and target lifecycles.
  See the [2026-10-27 review](maintenance-reviews/2026-10-27.md) for current findings
  and follow-up priorities; periodic review is an ongoing task.

Optional later work: compare remote source versions and the complete build recipe
with existing local outputs before recommending a rebuild. The current CLI does
not claim an existing package is current merely because its tests passed.

## 1. Finish source and notice review

- [x] Adopt MIT for independent project work and add the root license text.
- [x] Inventory actual Debian 12 copyright text, the pinned SLES archive and spec
  headers, companion source spec, and exact pinned optional UI wheels.
- [x] Record reviewed Debian source/archive and license hashes in
  `packaging/debian-license-review.json`. Publication rejects unreviewed versions
  or changed license evidence; builds still discover the suite's current source.
- [x] Resolve the SLES NRPE/OpenSSL linking basis from the pinned source's
  `src/utils.c:display_license()` and confirm it in the existing custom binary's
  license output. Retain the GPL text and explicit OpenSSL exemption.
- [x] Verify the companion's MIT declaration in its hash-checked original source
  spec, retain the SUSE copyright header, and prepare the full standard MIT text
  as an explicitly identified downstream companion notice.
- [x] Read the full ACL headers: both grant GPLv2-or-later, resolving the apparent
  difference caused by the short GPLv2 headings.
- [x] Preserve corresponding source archives/SRPMs and original per-file notices,
  with separate component/project notices checked during release preparation.

The [inventory](../THIRD_PARTY.md) and [SLES source review](sles-license-review.md)
record the evidence and correct the earlier incomplete searches. The previously
recorded SLES license questions are closed for these pinned inputs. Do not remove
notices, relabel third-party code MIT, or assume future source versions have the
same terms. The final candidate must still include and checksum all notices.

## 2. Complete and validate corresponding sources

Debian now builds a custom source package after the narrow rules/changelog
changes and before building the binary. `output/debianXX/sources/` must contain:

- The custom `.dsc`, with the source version used by the server binary.
- Every original and Debian packaging archive referenced by its SHA-256 fields.
- A source-directory `SHA256SUMS` covering the `.dsc` and referenced files.

The exporter checks identities, sizes and hashes, archive presence, and safe
filenames before replacing source outputs. Preserve the authentic upstream
archive; do not substitute a GitHub-generated checkout archive.

For each Debian target, require a successful `nrpe.py verify` run and independently
extract its exported `.dsc` with `dpkg-source --extract`. Inspect the extracted
custom changelog, `debian/rules`, and license files. Verify both checksum files.
Old packages built before source export do not gain corresponding sources by
passing a later runtime-only test.

For SLES, inspect both exported `.src.rpm` files. Confirm the NRPE spec records
`150400.95.2.withargs1`, retains command argument support, removes Bash command
substitution, and contains all source inputs. Confirm the real companion source
and notices are present. Retain all three input manifests and required build
scripts. Keep the pure SLES SP4 dependency policy.

## 3. Offline release candidate gate and automation

Local stage commands do not upload. The master-push workflow uploads only after
the gate passes. The checker must fail if any target is incomplete or untested:

1. Identify exact binaries, sources, targets, custom versions, and build workflow
   commit. Require clean tracked sources for the workflow archive.
2. Include complete corresponding sources and the build scripts, Docker/Compose
   recipes, and manifests required to rebuild them.
3. Include actual component/project license texts, notices, this inventory, and
   a record that applicable review findings have been resolved.
4. Require build, package validation, fresh-container installation, and TLS
   protocol results for exact binary hashes, including the SLES companion.
   Runtime-only tests or historical successful runs are insufficient.
5. Cover every asset with SHA-256: source RPMs, `.dsc`/archives, notices, workflow
   archive, and sanitized evidence. Preserve usable binary-only installation
   checksum manifests.
6. Reject missing/extra or modified assets, unsafe archive paths, mismatched
   versions/targets, missing notices, and tests bound to different bytes.
7. Exclude company CAs, private keys, credentials, local paths, raw environment
   values, caches, container images, and SLES media. Review logs and build
   information for local information before including public provenance.

New reports record workflow identity before and after verification and the full
exported release-asset hashes. Preparation requires a clean matching commit,
a fresh successful verify run and unchanged binaries/sources. Legacy reports
and runtime-only tests are rejected. Local records are not signed attestations;
the trusted workflow produces and transfers candidate archives within its run.
Completeness checks do not replace review when source/license evidence changes.

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

## 4. Verification required for subsequent releases

Run the repository's unit, shell syntax, and Compose checks. Run every intended
target with `python3 nrpe.py verify <target>`; use `--rebuild` when intentionally
replacing existing output. Preserve previous valid artifacts until replacement
checks pass. Local reports belong under `.nrpe/`.

Record passed, failed, skipped, and unrun checks separately. Include native
Windows CLI/process/CA validation where claimed. Container tests do not validate
target-server systemd, production TLS, firewall configuration, or a complete
Nagios deployment.

Draft release notes listing exact target/package versions, custom revision,
source provenance, installation links, unsigned-local-RPM policy, runtime-disabled
arguments by default, disabled Bash substitution, and support/security limits
of historical distributions. Keep unofficial-build wording; do not imply Debian,
SUSE, or Nagios endorsement.

Automatic build tags use a workflow-run number and commit prefix, separately
from distribution package versions. Master pushes are the publication trigger
requested by the maintainer. Other publication methods require a separate
request. Changes first follow the [integration workflow](git-workflow.md).

## References

- [Third-party provenance and license inventory](../THIRD_PARTY.md)
- [Debian Free Software Guidelines](https://www.debian.org/social_contract.en.html#guidelines)
- [GNU GPL version 2](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html)
- [SUSE BCI documentation and redistribution overview](https://opensource.suse.com/bci-docs/)
