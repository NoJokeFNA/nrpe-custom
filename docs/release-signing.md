# Release signature setup and verification

SSH Ed25519 signatures authenticate the release's `SHA256SUMS` manifest using an
independently trusted maintainer key. That manifest covers all five target
archives, workflow sources, notices, metadata and notes. This signs the release
bundle; it does not add DEB/RPM package signatures or certify software safety.

## Rollout status

Signing support is included in the published SLES 12 SP3 release. No production signing
key is enrolled in `packaging/release-allowed-signers`. Signing remains off until
the maintainer completes enrollment, configures the secret/variable and explicitly
requests promotion to master. The releases recorded in the [release history](release-history.md) are unsigned;
enrollment does not retroactively authenticate them or replace their files.

GitHub's [artifact attestation requirements](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations)
require Enterprise Cloud for private repositories. This repository is private;
the connected integration's attestation API read returned HTTP 403, so account
entitlement/access is not established. The SSH approach needs neither that
service nor disclosure to a public transparency log. Repository visibility stays
unchanged. No signing key or secret is generated or configured by this change.

## Enroll a maintainer-controlled key

Use OpenSSH 8.2+ with `ssh-keygen -Y` signature support. On a trusted workstation,
outside the checkout, create a dedicated key if none exists:

```sh
ssh-keygen -t ed25519 -N '' -C nrpe-custom-release -f ./nrpe-release-signing
ssh-keygen -lf ./nrpe-release-signing.pub
```

The CI key must be unencrypted for noninteractive use. Protect its private file
and backup; do not reuse an administrator/login key or commit the private key.
Only the `.pub` file and its SHA-256 fingerprint are public enrollment material.

1. On an allowed topic branch, add the actual public key to
   `packaging/release-allowed-signers` using this format:

   ```text
   nrpe-custom-release namespaces="nrpe-custom-release" ssh-ed25519 BASE64_PUBLIC_KEY
   ```

2. Review the key and fingerprint independently and integrate through a PR into
   develop. Consumers need that trusted public key independently of release files.
3. With owner-authorized GitHub credentials, configure the repository secret and
   variable from the trusted workstation, using the actual private-key path:

   ```sh
   gh secret set NRPE_RELEASE_SIGNING_KEY --repo NoJokeFNA/nrpe-custom < ./nrpe-release-signing
   gh variable set NRPE_RELEASE_SIGNING --repo NoJokeFNA/nrpe-custom --body ssh-ed25519
   ```

4. Run the local signing/verification check below with a candidate directory.
   Promote develop to master only on the maintainer's explicit request. Verify
   that the resulting release contains `SHA256SUMS.sig` and passes consumer
   verification before marking enrollment complete in the release plan.

The publishing job writes the secret to a temporary mode-0600 key file, signs,
verifies against the reviewed signer list, then removes the temporary key. The
local CLI restricts the temporary directory to the current Windows SID before
writing a key on Windows; POSIX uses a mode-0700 directory.
The key is unavailable to PR/build/test jobs. A missing/mismatched key, empty trusted
signer list or unsupported signing mode stops publication when signing is
enabled; there is no fallback to an unsigned release. An unset variable or
explicit `off` retains checksum-only publication and logs that signing is off.
Changing this setting is an administrative decision, not an automatic recovery
step after a signing failure.

For key rotation, enroll and independently communicate the new public key before
switching the CI secret. Preserve independently trusted old public keys for
historical releases. If a key is compromised, revoke consumer trust and assess
affected releases; simply changing the workflow key does not revoke old trust.

## Consumer verification

Obtain the signer file from a trusted checkout or independent maintainer channel
and confirm its fingerprint independently. A public key shipped alongside an
untrusted download does not authenticate that download. Download all release
assets into one otherwise empty directory, including `SHA256SUMS.sig`.

From a trusted checkout containing the verification helper:

```sh
python3 scripts/release_signature.py verify --directory /path/to/downloaded-release \
  --allowed-signers /path/to/trusted-release-allowed-signers
```

The helper first authenticates the checksum manifest, then requires the exact
asset set and verifies every payload hash. It rejects missing signatures,
unknown signers, extra/missing files, links, invalid checksum paths and changes.
It does not extract or install packages. Treat any nonzero exit as failure;
unsigned historical releases cannot pass this authentication check.

The equivalent signature-only OpenSSH command on a POSIX host is:

```sh
ssh-keygen -Y verify -f /path/to/trusted-release-allowed-signers \
  -I nrpe-custom-release -n nrpe-custom-release \
  -s /path/to/downloaded-release/SHA256SUMS.sig \
  < /path/to/downloaded-release/SHA256SUMS
```

That command authenticates the manifest only. The Python helper additionally
checks completeness and hashes. On Windows, use a recent OpenSSH installation
and the Python helper; PowerShell redirection is not a substitute for the POSIX
stdin example above.

## Local signing check

For a complete candidate produced by [release preparation](releases.md#local-candidate-preparation),
the signing CLI accepts the name of an environment variable containing the
private key. It never accepts the key itself as a command-line argument:

```sh
NRPE_LOCAL_SIGNING_KEY="$(cat /secure/path/nrpe-release-signing)" \
  python3 scripts/release_signature.py sign --directory .nrpe/release \
  --allowed-signers packaging/release-allowed-signers --key-env NRPE_LOCAL_SIGNING_KEY
```

Use a shell with tracing disabled. Test using disposable keys for development;
never upload private keys or logs containing them. Signing refuses an existing
signature rather than replacing it. Signing and verification commands do not
upload or publish anything.

## Check readiness without accessing private keys

Before enabling signing, inspect the reviewed public signer file and available
local tool:

```sh
python3 scripts/check_release_signing.py
```

Optionally check the specific GitHub variable and secret's **metadata** using
owner-authorized `gh` access:

```sh
python3 scripts/check_release_signing.py --repository NoJokeFNA/nrpe-custom
```

The checker prints public SHA-256 fingerprints, never creates/reads a private key,
never changes GitHub configuration and returns nonzero for missing/invalid public
enrollment or missing/inaccessible requested metadata. It only queries
`NRPE_RELEASE_SIGNING` and metadata for `NRPE_RELEASE_SIGNING_KEY`; GitHub does
not expose the secret's value. Metadata cannot establish that the secret matches
the enrolled public key. Even exit 0 is not proof of a verified signed release.

On 2026-10-29 the maintainer confirmed that no dedicated release key exists yet
and requested prepared setup with enrollment explicitly left open. The local
check found no enrolled public key. The GitHub signing variable could not be
read through the connected credentials; this cannot distinguish an unset setting
from insufficient permission. No setting was changed and no production key was
generated. Complete the workstation key creation/enrollment steps above, retain
an owner-controlled backup and independently communicate the approved fingerprint
before activation. Master promotion and the first signed release remain separate
explicit maintainer actions.

## Optional Arch profile

The optional Arch prerelease has one target archive and the same common source,
notice and release metadata files. Sign or verify it with `--profile archlinux`.
The default `regular` profile continues to require the five regular targets;
it does not silently accept an incomplete bundle or require an optional target.
The manifest must still be authenticated with an independently trusted signer.
