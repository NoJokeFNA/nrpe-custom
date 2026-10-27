# Third-party provenance and license inventory

This inventory records evidence inspected during release preparation on
2026-10-27. It is not a completed redistribution approval. The root [MIT
license](LICENSE) applies to independently authored project code and
documentation; it does not relicense NRPE, distribution packaging, embedded
code, dependencies, or public signing keys.

## Components in generated packages and sources

| Component | Evidence inspected | Findings and remaining work |
| --- | --- | --- |
| Debian `nagios-nrpe` | Actual `debian/copyright` from the reconstructed custom sources for Debian 11 (`4.0.3-1`), 12 (`4.1.0-1`), and 13/14 (`4.1.3-1`); compared with the Debian 12 installed-package notice | These four copyright files are identical. They declare GPL-2-or-later with an explicit OpenSSL linking exception for the main code; separate entries cover ACL code, `snprintf`, and Debian packaging. The full GPL text and upstream notice files are retained in the source archives. Recheck actual sources for every candidate; this is not a blanket approval of future source versions. |
| SLES NRPE `4.1.1` | [Pinned source manifest](packaging/sles15sp4-source.json), revision `835292739a5736a9d8f0460f670b6f15`; actual `nrpe-4.1.1.tar.xz` and modified `nrpe.spec` in the existing builder | `LICENSE.md` contains GPLv2; `src/nrpe.c` grants GPLv2-or-later. Spec metadata declares `GPL-2.0-or-later`. An explicit NRPE/OpenSSL linking exception was **not established** by searching this archive; Debian's exception must not be assumed to cover this SLES source. Resolve this before binary publication. |
| NRPE ACL implementation | `include/acl.h` and `src/acl.c` in SLES upstream source; Debian copyright entry | Kaspersky Lab ZAO copyright, 2011. SLES file headers identify GPLv2; Debian's notice identifies GPL-2-or-later. Retain the exact per-file notices and review this difference for the actual release source. |
| NRPE `snprintf` implementation | `src/snprintf.c` in SLES upstream source; Debian copyright entry | Patrick Powell, 1995. Permission requires retaining the source attribution notice. Do not replace it with the project's MIT notice. |
| Autoconf macros and generated helper files in NRPE sources | Actual `macros/LICENSE`, macro headers, `build-aux/config.guess`, and `build-aux/config.sub` in the SLES source archive | GPL notices include file-specific Autoconf/build-output exceptions. Preserve the files and their notices in the source package. These exceptions are not evidence of an OpenSSL linking exception for NRPE. |
| SUSE NRPE packaging | Actual pinned `nrpe.spec`, including its SUSE LLC 2024 header | Spec header retains contributed changes under the pristine package's license, subject to its stated fallback. Keep the original notice and modified spec in the source RPM; the project MIT license does not replace the spec's terms. |
| `system-user-nagios` `1.0.0-0` | [Pinned manifest](packaging/sles15sp4-user-source.json), revision `b979817ae6424675519c86e80add617a`; actual spec extracted from the existing companion source RPM | RPM metadata and spec declare MIT; the SUSE LLC 2024 header describes licensing of the spec. The full MIT grant for this component has not yet been established from an included license file. Preserve the spec and README and resolve notice completeness before publishing the companion RPM. |

The SLES upstream archive is bound by SHA-256
`7689aea570596573919371f7d6a1753eca90213368ede51f477e25782eb1ef9c`.
The manifests retain expected sizes and checksums for the original OBS input
files; the exported source RPM contains the intentionally modified build spec.

The existing NRPE source RPM was unpacked and compared with the pinned manifest:
14 entries matched (including the intentionally modified spec), while the OBS
history file `nrpe.changes` was absent. The companion source RPM matched its spec
and README; `system-user-nagios.changes` was absent. Record these provenance
differences explicitly and include the pinned history files separately if a
candidate promises the complete OBS input set. The comparison is not a fresh
SLES binary build or a completed license review.

## Host-only optional menu dependencies

`requirements-menu.txt` pins `prompt-toolkit==3.0.52` and `wcwidth==0.2.13`.
These libraries are downloaded by the user through pip; they are not vendored
into this checkout or installed in the NRPE server package. The exact pinned
wheels were downloaded without installation and their actual notices inspected:

| Distribution | License evidence | Wheel SHA-256 |
| --- | --- | --- |
| `prompt_toolkit-3.0.52-py3-none-any.whl` | `prompt_toolkit-3.0.52.dist-info/licenses/LICENSE`: BSD three-clause terms, Jonathan Slenders, 2014 | `9aac639a3bbd33284347de5ad8d68ecc044b91a762dc39b7c21095fcd6a19955` |
| `wcwidth-0.2.13-py2.py3-none-any.whl` | `wcwidth-0.2.13.dist-info/LICENSE`: MIT, Jeff Quast, 2014; additional Markus Kuhn 2007 permission/warranty notice | `3da69048e4540d84af32131829ff948f1e022c1c6bdb8d6102117aac784f6859` |

Before distributing a bundled Python application, include these actual license
files and inventory any additional shipped dependencies. Do not substitute the
license files of different versions installed in a development environment.

## Build and runtime dependencies

Docker images, OpenSSL, system libraries, Debian/SUSE repository packages,
monitoring plugins, and SLES installation media retain their own licenses.
The current release scope is the custom server packages, the SLES user package,
their corresponding sources, and this project's build workflow. It does not
include container images, dependency RPM/DEB bundles, or installation media.
Any expansion requires an inventory of the additional shipped bytes.

The bundled SUSE and backports public keys are trust material identified by the
fingerprints and checksums in the SLES manifests. They are not independently
authored project code; do not label them MIT merely because they are in this
repository. Retain their issuer identity and provenance.

## Required release notices

Each candidate must include this inventory, the project MIT license, and the
actual notices from the source packages being distributed. Source archives must
retain their full upstream and distribution license files. The generic GitHub
repository source archive does not replace corresponding NRPE sources.

Keep the project's unofficial-build wording and NRPE's `LEGAL` trademark notice.
No endorsement or support entitlement from Nagios, Debian, or SUSE is implied.
Open findings above remain release blockers; metadata labels alone do not close
them. See the [release plan](docs/release-plan.md).
