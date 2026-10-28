# SLES 12 SP3 license notices

These files accompany the pinned NRPE, `system-user-nagios` and build-macros sources. They
retain upstream terms and are not relicensed under the project's MIT license.
Include this directory with a SLES release candidate alongside the binaries,
all three source RPMs, the input manifests, and build scripts.

| File | Origin and scope |
| --- | --- |
| [NRPE-GPL-2.0.md](NRPE-GPL-2.0.md) | Verbatim `LICENSE.md` from the pinned `nrpe-4.1.1.tar.xz`; the full GPLv2 text |
| [NRPE-license-notice.txt](NRPE-license-notice.txt) | Text assembled from the upstream `display_license()` function in `src/utils.c`; GPLv2-or-later grant, OpenSSL exemption, and warranty notice |
| [NRPE-LEGAL.txt](NRPE-LEGAL.txt) | Verbatim upstream `LEGAL` file, including trademark and warranty notices |
| [system-user-nagios-spec-header.txt](system-user-nagios-spec-header.txt) | Verbatim copyright/licensing header from the pinned companion spec |
| [system-user-nagios-MIT.txt](system-user-nagios-MIT.txt) | Standard MIT terms matching the companion spec's explicit `License: MIT` declaration, with the SUSE LLC 2024 copyright from that spec |
| [nagios-rpm-macros-BSD.txt](nagios-rpm-macros-BSD.txt) | Verbatim upstream COPYING from the pinned macros source; BSD-3-Clause, Lars Vogdt 2011 |

The standalone companion MIT file is supplied here as a downstream notice. The
upstream source RPM did not ship that standalone file; this is not a claim that
it did, a new permission from this project, or a license change. The declaration
comes from the original spec, not from this project's choice of MIT.

The input archive and companion spec were checked against their respective
[NRPE](../../sles12sp3-source.json) and [user-package](../../sles12sp3-user-source.json)
manifests. The full [review and source references](../../../docs/sles-license-review.md)
explain the evidence and remaining release work.

Keep the original source-package copyright headers as well, including the ACL,
`snprintf`, Autoconf, and SUSE packaging notices. These companion notices do not
replace the corresponding source RPMs. Include all notice assets in the release
checksum manifest. Existing RPM payloads and upstream manifests are unchanged;
notices accompany them as separate release assets.

The native nagios-rpm-macros build uses BSD-3-Clause sources at pinned OBS
revision `a911087cc73b87e04465861110d43754`. `nagios-rpm-macros-BSD.txt` is the
verbatim upstream COPYING file (Lars Vogdt, 2011). Its source RPM and original
inputs accompany the SLE-12 rebuild; the build-only macro binary is not shipped.
