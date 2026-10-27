# Release preparation plan

Status: active preparation, updated 2026-10-27. The maintainer has selected MIT
for independently authored project code and documentation. No public binary
release is ready or authorized by this plan. Publish only when explicitly
requested after a concrete candidate has passed the checks below.

## Scope and current state

The intended assets are unofficial custom Debian server packages and the SLES
15 SP4 NRPE/user packages, with corresponding sources, notices, build scripts,
checksums, and artifact-bound test results. Container images, dependency package
bundles, and SLES media are outside this scope.

| Item | State | Evidence or next action |
| --- | --- | --- |
| CLI, menu, workflow logs and artifact-bound test results | Implemented | [Workflow reference](workflow.md); fresh candidate validation is still required |
| Company CA handoff on Windows | Implemented; user confirmed the fix | Environment-backed BuildKit secret, PEM/DER validation and SHA-256 cache identity |
| TLS failure guidance | Implemented | Missing/supplied CA and other TLS failures; separate Docker/BuildKit trust documented |
| Custom package installation instructions | Documented | [Installation guide](installation.md), linked from README and SLES notes; full deployments use upstream manuals |
| Project license | Adopted | [MIT license](../LICENSE); third-party components retain their own licenses |
| Warranty and liability notice | Documented | README and [security guidance](security.md), subject to applicable law; no security or availability guarantee |
| Third-party license inventory | Initial review completed; findings open | [Inspected evidence](../THIRD_PARTY.md); declarations alone do not complete redistribution review |
| Debian corresponding-source export | Implemented and validated on all four targets | `scripts/export_debian_sources.py`; full verify runs and independent source reconstruction passed |
| SLES corresponding-source export | Existing payloads inspected; review findings open | Source RPM inputs/specs compared with manifests; OBS history files absent and notice review incomplete |
| Release bundle completeness and test gate | Not implemented | Implement the offline candidate check described below |
| Public release | Not created | Requires resolved findings, an identified candidate, successful checks, and an explicit publication request |

## 1. Finish source and notice review

- [x] Adopt MIT for independent project work and add the root license text.
- [x] Inventory actual Debian 12 copyright text, the pinned SLES archive and spec
  headers, companion source spec, and exact pinned optional UI wheels.
- [ ] Review each candidate Debian source's `debian/copyright`, embedded notices,
  full GPL text, and OpenSSL linking terms; versions differ by suite.
- [ ] Resolve the SLES NRPE/OpenSSL linking basis from authoritative evidence.
  A Debian copyright exception does not establish permission for the separate
  SLES source. Record actual texts and applicable component scope.
- [ ] Establish and include the full companion user-package license grant and
  notices, not just its RPM `License: MIT` declaration.
- [ ] Preserve NRPE `LEGAL`, ACL and `snprintf` notices, Debian/SUSE packaging
  notices, and Autoconf/helper exceptions in the corresponding sources.

The [inventory](../THIRD_PARTY.md) records the concrete remaining findings.
Do not remove notices, relabel third-party code MIT, or substitute metadata for
unresolved license evidence. Targets with applicable unresolved findings are not
publication candidates.

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

## 3. Implement an offline release candidate gate

Prepare candidates under ignored local storage; do not upload them automatically.
The checker must fail if any selected target is incomplete or untested:

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

Current run reports bind runtime tests to package bytes, but do not record full
source/workflow identity. Add that evidence rather than treating the current
schema as a release attestation. Completeness checks do not resolve license
findings.

## Validation recorded during this preparation

The following checks passed on 2026-10-27:

- 114 discovered unit tests, shell syntax checks, both Compose configurations,
  documentation relative-file links and shell snippets, and `git diff --check`.
- `python3 nrpe.py verify debian11 debian12 debian13 debian14 --rebuild`:
  all four targets passed build, package validation, fresh-container installation,
  arguments-disabled rejection, and two distinct arguments-enabled TLS checks.
- Independent `.dsc` extraction for each target, source/binary checksums, custom
  changelog versions, build flags, and retained GPL/copyright files.
- Inspection of both existing SLES source RPMs against their manifests; findings
  are recorded in the [inventory](../THIRD_PARTY.md). No fresh SLES build was run
  as part of the Debian-only exporter change. No native Windows run was performed.

The first Debian attempt failed because `dpkg-source` was run from the extracted
tree rather than the directory containing the original archive. The build now
sets that working directory explicitly; the subsequent full four-target run
passed. These local checks are preparation evidence, not a published release
attestation. Candidate source/workflow identity still needs the gate above.

## 4. Validate and prepare a reviewable candidate

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

Select a project release tag/version separately from distribution package
versions. Prepare the asset list, checksums, evidence and release notes for
review. Publishing a release or tag requires an explicit request.

## References

- [Third-party provenance and license inventory](../THIRD_PARTY.md)
- [Debian Free Software Guidelines](https://www.debian.org/social_contract.en.html#guidelines)
- [GNU GPL version 2](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html)
- [SUSE BCI documentation and redistribution overview](https://opensource.suse.com/bci-docs/)
