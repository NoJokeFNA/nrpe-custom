# Per-push package releases

Each push to `master` runs the [release workflow](../.github/workflows/release.yml).
The repository's visibility is unchanged. Topic/develop pushes do not publish
releases. Release-relevant PRs run the build and archive checks without publishing;
manual workflow dispatch is also validation-only.

## Build and publication gate

1. Run the Linux/Windows unit matrix, shell/Compose checks and dependency audit.
2. Build all five targets on separate fresh Ubuntu runners: Debian 11, 12, 13,
   14 and SLES 15 SP4. Apply this project's packaging changes through the normal
   builders. Install each package in its matching disposable runtime container
   and test disabled/enabled arguments over TLS. All targets are attempted even
   if one fails; no release is published unless every target succeeds.
3. Record the clean workflow commit before and after verification, plus hashes
   of binaries and exported source assets. A runtime-only test, dirty checkout,
   stale report, changed artifact or missing source/notice fails preparation.
4. Validate Debian DSC references, source/binary versions, reconstructed rules
   and license files. Validate both SLES source RPMs against binary identities
   and pinned original inputs. Export all original OBS files, including `.changes`
   history, alongside the modified source RPMs.
5. Package each target, then require exactly the five expected target archives.
   Verify their entries, target/commit identities, notices and checksums; reject
   traversal, links, duplicates, missing/extra files and oversized archives.
6. Add the exact Git workflow source archive, license inventory, release manifest,
   notes and checksums. Verify uploaded-asset checksums again in the publishing job.
   Upload to a draft first and publish only after all uploads succeed.

Only the master push publishing job receives write permission. No bot commits
are created: a release tag points to the already-reviewed workflow commit.
Optional [SSH release signing](release-signing.md) authenticates the checksum
manifest before publication when explicitly configured. Enrollment and actual
signed-release validation are separate from implementing the helper; see its
rollout status. Creating or merging a master promotion requires an explicit
maintainer request; routine integration stops at develop.

## Assets and naming

The release tag is `build-<workflow-run-number>-<commit-prefix>`. This identifies
every successful master push without inventing a semantic version policy or
renaming distribution packages. Package versions remain the versions recorded
by Debian changelog/SLES spec, including the project's custom revision.

Release assets are:

- `nrpe-custom-debian11.tar.gz` through `nrpe-custom-debian14.tar.gz`.
- `nrpe-custom-sles15sp4.tar.gz`.
- `workflow-source.tar.gz`, `LICENSE`, `THIRD_PARTY.md`, `release.json`,
  `RELEASE_NOTES.md`, and `SHA256SUMS`.
- `SHA256SUMS.sig` when SSH signing is enabled. This detached signature is not
  part of its own signed checksum manifest.

Target archives contain the original package filenames, installation checksum
manifest, corresponding sources, component license notices and a sanitized
verification manifest. SLES includes its real companion binary/source RPM and
original OBS input set. Debian includes its custom DSC and referenced original
and packaging archives. The workflow source includes the required build scripts,
recipes, manifests and original per-file notices.

Raw logs, environment values, CA/media paths and `.buildinfo` files are excluded
from published verification data. Company trust material, private keys, container
images, dependencies and SLES media are not release assets. Actions retains the
prepared archives for 14 days; published GitHub release assets are separate.

An older concurrent build cannot replace a newer commit's `latest` release.
Published assets are immutable in this workflow: rerunning an already published
run fails rather than clobbering its tag or files. An interrupted upload can leave
a draft; inspect and remove that incomplete draft/tag deliberately before rerunning.
No partial target subset is presented as a complete release.

## Local candidate preparation

Use a clean committed checkout. Install ordinary inspection tools (`dpkg-dev`,
`rpm`, `rpm2cpio`, `cpio`) on the inspection runner, not custom output packages on
the workstation. After a fresh `python3 nrpe.py verify <target>` run:

```sh
python3 scripts/prepare_release.py target --target debian12 \
  --commit "$(git rev-parse HEAD)" --destination .nrpe/target-bundles
```

Repeat for all five targets, then:

```sh
python3 scripts/prepare_release.py assemble --commit "$(git rev-parse HEAD)" \
  --incoming .nrpe/target-bundles --destination .nrpe/release
```

Use new/empty staging directories; existing archives are not silently replaced.
Old reports without source/workflow identity cannot be used for releases. The
stage/verify commands do not publish anything. Use the [Git workflow](git-workflow.md)
to review and integrate changes before promoting `develop` to `master`.

Builds still depend on reachable distribution/OBS repositories and registry
availability. A failed download, signature, TLS or protocol check stops publication;
it does not trigger an insecure fallback. Successful container tests do not prove
production systemd, TLS, firewall or monitoring configuration is correct. Follow
[installation](installation.md), [rollback](updates-and-rollback.md) and the
[support policy](maintenance.md) on real systems.
