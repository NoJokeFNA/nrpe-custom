# SLES pinned-source license review

Reviewed on 2026-10-27. The same exact upstream and companion source inputs
are reused for the SLES 12 SP3 migration on 2026-10-28. Historical binary observations
below were recorded on SLES 15 SP4 and do not establish SLES 12 SP3 runtime validation.
The published SLES 12 SP3 build/runtime evidence is in the [release history](release-history.md).
The two previously recorded SLES license-evidence gaps
are closed for the pinned inputs below. The review also resolves the apparent
ACL license-version discrepancy. Release completeness, provenance and packaging
checks still apply; this does not approve redistribution of SLES images,
installation media, or dependency bundles.

## NRPE and OpenSSL: explicit upstream permission found

The original `nrpe-4.1.1.tar.xz` in the pinned OBS source has SHA-256:

```text
7689aea570596573919371f7d6a1753eca90213368ede51f477e25782eb1ef9c
```

Its `src/utils.c`, in `display_license()` at lines 572–596, contains a
program-level GPL notice expressly allowing compilation, linking and use with
OpenSSL. The following text grants GPL version 2 or any later version. This is
permission in the actual NRPE source, independent of Debian's copyright file.
The corresponding [upstream release source](https://github.com/NagiosEnterprises/nrpe/blob/nrpe-4.1.1/src/utils.c#L572-L596)
provides a public reference.

The checked `src/utils.c` has SHA-256:

```text
75f4ab494d009b09d8358ced0394d80f9476f8ed6f7323c200a007d8cd1a2bd3
```

The first review searched for "exception" and "permission to link" but missed
the word "exemption" in this function. The earlier unresolved finding was an
incomplete search, not evidence that an exception was absent. The notice is
now retained in [NRPE-license-notice.txt](../packaging/licenses/sles12sp3/NRPE-license-notice.txt),
alongside the original full GPL and `LEGAL` texts.

The existing custom RPM was checksum-checked and its binary extracted in an
offline disposable SLES container. The binary's `-l` output contains the same
OpenSSL/GPL notice. This NRPE license-display path exits with status 3 even when
it prints the notice; the text was checked directly, rather than treating that
exit status as a successful application test. No server was started and no
package was installed on the host. No fresh package build was required or run
for that historical license inspection.

## ACL code: GPLv2-or-later, not a contradictory GPLv2-only grant

The full license notices in both `include/acl.h` and `src/acl.c` expressly
permit version 2 or a later version. Their short "License: GPLv2" headings do
not replace those full grants. The notices retain Kaspersky Lab ZAO's 2011
copyright and are consistent with Debian's `GPL-2+` entry.

Checked file hashes:

| File in the pinned archive | SHA-256 |
| --- | --- |
| `include/acl.h` | `323ca78733e229c77ec4e8a37fdc837b47558af11776660753b98023e83e138a` |
| `src/acl.c` | `73f223aeec851559738d06aa2a4e26319c33300d53082d67f0d8a1fc3ae5ef00` |

Preserve these original headers in the source RPM; no relicensing or replacement
copyright notice is necessary.

## Companion user package: MIT declaration and complete notice

The exact source declaration is in the
[pinned original OBS spec](https://api.opensuse.org/public/source/server:monitoring/system-user-nagios/system-user-nagios.spec?rev=b979817ae6424675519c86e80add617a&expand=1),
not merely in rebuilt RPM metadata. Its source revision is
`b979817ae6424675519c86e80add617a`. The spec is bound by the
[input manifest](../packaging/sles12sp3-user-source.json) to SHA-256:

```text
36e678f60dd314addc9098421d432bac932c23f19a7ce8b048cf06b6b9cbc1b7
```

The source spec was extracted from the companion source RPM and also fetched
directly from OBS at the pinned revision; both matched the manifest's size and
hash. It explicitly declares `License: MIT`; its SUSE LLC 2024 header states
that the spec and contributed modifications use the pristine package's license,
subject to the header's stated fallback. SUSE's
[Package Hub entry](https://packagehub.suse.com/packages/system-user-nagios/)
independently identifies the component as MIT; that entry concerns a different
distribution build and is corroboration, not the identity evidence for ours.

The original source package has no standalone full MIT text. This is a missing
notice asset, not an unidentified license or a need for this project to grant
rights on SUSE's behalf. The
[standard MIT terms](https://spdx.org/licenses/MIT.html) are now supplied in
[system-user-nagios-MIT.txt](../packaging/licenses/sles12sp3/system-user-nagios-MIT.txt),
with the original copyright and the original source header kept separately.
That file is explicitly identified as a downstream companion notice. Standard
short identifiers identify license texts; see
[SPDX's explanation](https://spdx.dev/learn/handling-license-info/).

## Release obligations that remain

The two evidence questions are resolved. A SLES candidate must still include:

- All three complete corresponding source RPMs (NRPE, system user and build
  macros), manifests and required build scripts.
- The [notice directory](../packaging/licenses/sles12sp3/README.md), including the
  original GPL text, OpenSSL notice, trademark notice, companion MIT terms and
  the build macros' BSD-3-Clause notice.
- Original per-file copyright and license notices inside the source packages.
- Candidate checksums covering every distributed asset and tests bound to the
  exact server and companion binaries.

The previously missing OBS `.changes` history is now retained in the original
input sets exported by new builds. The release gate verifies the complete OBS
set and the corresponding SRPMs separately. These additions do not change the
checked license declarations. See [release automation](releases.md) and the
[release plan](release-plan.md) for candidate checks and integration state.

## Native SLES-12 build macros

The port additionally pins `nagios-rpm-macros` 0.14 at OBS revision
`a911087cc73b87e04465861110d43754`. Its original `nagios-rpm-macros-COPYING`
grants BSD-3-Clause terms and retains Lars Vogdt's 2011 copyright. The verbatim
[notice](../packaging/licenses/sles12sp3/nagios-rpm-macros-BSD.txt), native source
RPM and all original source files accompany the port. No macros binary or SLE-12
dependency bundle is published. The release gate compares the notice directly
with its hash-checked source input.
