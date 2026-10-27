# SLES 15 SP4 license notices

These files accompany the pinned NRPE and `system-user-nagios` packages. They
retain upstream terms and are not relicensed under the project's MIT license.
Include this directory with a SLES release candidate alongside the binaries,
both source RPMs, the input manifests, and build scripts.

| File | Origin and scope |
| --- | --- |
| [NRPE-GPL-2.0.md](NRPE-GPL-2.0.md) | Verbatim `LICENSE.md` from the pinned `nrpe-4.1.1.tar.xz`; the full GPLv2 text |
| [NRPE-license-notice.txt](NRPE-license-notice.txt) | Text assembled from the upstream `display_license()` function in `src/utils.c`; GPLv2-or-later grant, OpenSSL exemption, and warranty notice |
| [NRPE-LEGAL.txt](NRPE-LEGAL.txt) | Verbatim upstream `LEGAL` file, including trademark and warranty notices |
| [system-user-nagios-spec-header.txt](system-user-nagios-spec-header.txt) | Verbatim copyright/licensing header from the pinned companion spec |
| [system-user-nagios-MIT.txt](system-user-nagios-MIT.txt) | Standard MIT terms matching the companion spec's explicit `License: MIT` declaration, with the SUSE LLC 2024 copyright from that spec |

The standalone companion MIT file is supplied here as a downstream notice. The
upstream source RPM did not ship that standalone file; this is not a claim that
it did, a new permission from this project, or a license change. The declaration
comes from the original spec, not from this project's choice of MIT.

The input archive and companion spec were checked against their respective
[NRPE](../../sles15sp4-source.json) and [user-package](../../sles15sp4-user-source.json)
manifests. The full [review and source references](../../../docs/sles-license-review.md)
explain the evidence and remaining release work.

Keep the original source-package copyright headers as well, including the ACL,
`snprintf`, Autoconf, and SUSE packaging notices. These companion notices do not
replace either corresponding source RPM. Include all notice assets in the release
checksum manifest. Existing RPM payloads and upstream manifests are unchanged;
notices accompany them as separate release assets.
