# Third-party provenance and license inventory

This inventory records evidence inspected during release and website preparation
on 2026-10-27 through 2026-10-29. It is not a completed redistribution approval. The root [MIT
license](LICENSE) applies to independently authored project code and
documentation; it does not relicense NRPE, distribution packaging, embedded
code, dependencies, or public signing keys.

The active target was corrected to **SLES 12 SP3** after receiving
its actual OS/binary/library identity on 2026-10-28. The same reviewed NRPE/user
sources are rebuilt natively; their previous SLE-15 runtime observations do not
prove SLE-12 compatibility. The port additionally builds the macros from pinned
upstream sources and retains their BSD notice. Original SLE-12 dependency RPMs
are verified but are not release assets. Historical releases are unchanged.

## Components in generated packages and sources

| Component | Evidence inspected | Findings and remaining work |
| --- | --- | --- |
| Debian `nagios-nrpe` | Actual `debian/copyright` from the reconstructed custom sources for Debian 11 (`4.0.3-1`), 12 (`4.1.0-1`), and 13/14 (`4.1.3-1`); compared with the Debian 12 installed-package notice | These four copyright files are identical. They declare GPL-2-or-later with an explicit OpenSSL linking exception for the main code; separate entries cover ACL code, `snprintf`, and Debian packaging. The full GPL text and upstream notice files are retained in the source archives. Recheck actual sources for every candidate; this is not a blanket approval of future source versions. |
| SLES NRPE `4.1.1` | [Pinned source manifest](packaging/sles12sp3-source.json), revision `835292739a5736a9d8f0460f670b6f15`; actual upstream archive, modified spec and existing custom binary's license output | **Resolved:** `src/utils.c:display_license()` explicitly allows compilation, linking and use with OpenSSL and grants GPLv2-or-later. This is evidence from the SLES source itself. The earlier search missed the word "exemption". Preserve the [upstream notice and full GPL text](packaging/licenses/sles12sp3/README.md); see the [source review](docs/sles-license-review.md). |
| NRPE ACL implementation | Full license notices in `include/acl.h` and `src/acl.c` in the pinned SLES archive; Debian copyright entry | **Resolved:** both full grants explicitly permit GPLv2 or later, consistent with Debian's notice. The short GPLv2 headings did not establish a GPLv2-only restriction. Retain Kaspersky Lab ZAO's 2011 copyright and the full per-file notices. |
| NRPE `snprintf` implementation | `src/snprintf.c` in SLES upstream source; Debian copyright entry | Patrick Powell, 1995. Permission requires retaining the source attribution notice. Do not replace it with the project's MIT notice. |
| Autoconf macros and generated helper files in NRPE sources | Actual `macros/LICENSE`, macro headers, `build-aux/config.guess`, and `build-aux/config.sub` in the SLES source archive | GPL notices include file-specific Autoconf/build-output exceptions. Preserve the files and their notices in the source package. These exceptions are not evidence of an OpenSSL linking exception for NRPE. |
| Nagios RPM macros 0.14 | Immutable OBS revision `a911087cc73b87e04465861110d43754`; actual `nagios-rpm-macros-COPYING` and spec | BSD-3-Clause, Lars Vogdt 2011. Retain the verbatim [BSD notice](packaging/licenses/sles12sp3/nagios-rpm-macros-BSD.txt), source RPM and complete original source set. The binary is a native build dependency, not a released runtime package. |
| SUSE NRPE packaging | Actual pinned `nrpe.spec`, including its SUSE LLC 2024 header | Spec header retains contributed changes under the pristine package's license, subject to its stated fallback. Keep the original notice and modified spec in the source RPM; the project MIT license does not replace the spec's terms. |
| `system-user-nagios` `1.0.0-0` | [Pinned manifest](packaging/sles12sp3-user-source.json), revision `b979817ae6424675519c86e80add617a`; actual original spec extracted from the source RPM and hash-verified | **Resolved:** the source spec itself explicitly declares MIT and retains the SUSE LLC 2024 copyright/licensing header. The missing standalone full text is supplied as a [downstream companion notice](packaging/licenses/sles12sp3/system-user-nagios-MIT.txt), not represented as an original upstream file or a new project license grant. Preserve the spec and README and include that notice in release assets. |

The SLES upstream archive is bound by SHA-256
`7689aea570596573919371f7d6a1753eca90213368ede51f477e25782eb1ef9c`.
The manifests retain expected sizes and checksums for the original OBS input
files; the exported source RPM contains the intentionally modified build spec.

The earlier NRPE source RPM was unpacked and compared with the pinned manifest:
14 entries matched (including the intentionally modified spec), while the OBS
history file `nrpe.changes` was absent. The companion source RPM matched its spec
and README; `system-user-nagios.changes` was absent. Record these provenance
differences explicitly. New SLES builds now export the complete original OBS
input sets under `obs-sources/`; release preparation verifies every file against
the pinned manifests and includes the history alongside the SRPMs. The original
comparison alone is not evidence of a fresh build.

The [Debian 4.2.0-1 source review](docs/debian-source-review.md) additionally
covers the version now supplied by Debian 14. Its license grants and OpenSSL
exception are unchanged; the Debian copyright edit removes obsolete FSF postal
addresses. This does not approve later versions.

Reviewed Debian upstream archive and license-file hashes are recorded in
`packaging/debian-license-review.json`. Automatic publication fails for a new
source version or changed evidence until it is reviewed; source discovery and
local builds remain dynamic. This separates successful compilation from license
review of previously unexamined source bytes.

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

`requirements-audit.txt` separately pins the optional CI/development tool
`pip-audit==2.10.1`. Its installed distribution's actual `licenses/LICENSE` contains
Apache License 2.0. It and its dependencies are installed separately for auditing,
not vendored into this repository or shipped inside NRPE packages. Bundling this
tool would require its own complete dependency/notice inventory. GitHub Actions
are similarly fetched by CI at maintainer-selected upstream major-version tags rather than distributed
as part of the server packages.

## Build and runtime dependencies

`requirements-website.txt` pins the separate build-only renderer
`Markdown==3.8.2` (Python-Markdown). Its installed wheel's
`markdown-3.8.2.dist-info/licenses/LICENSE.md` was inspected and contains
BSD-3-Clause terms; wheel metadata records the same SPDX expression. The
renderer is installed separately, not vendored, bundled into NRPE packages or
copied into the static site. Generated pages retain the licenses of their
original documentation and notices. Bundling the renderer would require its
actual license text and a separate dependency inventory. Website CSS, templates
and browser JavaScript are independently authored project code; no external
JavaScript framework or analytics SDK is shipped. The locally hosted font and
its retained notice are listed below.

The build-only syntax highlighter is `shiki@4.5.0`, pinned with integrity-checked
transitive dependencies in `website/package-lock.json`. Installed `shiki`,
`@shikijs/core`, `@shikijs/langs`, `@shikijs/themes` and `@shikijs/engine-oniguruma`
LICENSE files were inspected and contain MIT terms; the installed
`@shikijs/vscode-textmate` LICENSE.md also contains MIT terms. The
[original Shiki license](website/assets/shiki-LICENSE.txt) is retained unchanged.
Individual language/theme provenance is covered by the upstream
[grammar/theme notices](https://github.com/shikijs/textmate-grammars-themes/blob/main/NOTICE).
These dependencies, their grammars and WASM remain build-only, not vendored or
included in NRPE packages or browser JavaScript. Generated code colors use the
bundled GitHub Dark Default theme. The small NRPE syntax grammar and static
HTML/CSS adapter are independently authored project code. The upstream NRPE
sample configuration is referenced, not copied or relicensed as project code.
Static diagrams use build-only `mermaid@12.2.0` (MIT; the installed LICENSE was
inspected and is [retained unchanged](website/assets/mermaid-LICENSE.txt)) and
`puppeteer@25.16.0` (Apache-2.0 in its package metadata), also locked with integrity
hashes. The renderer uses the workstation's installed Chrome/Chromium and ships
SVG output, not a browser binary, Mermaid runtime, fonts or Node dependencies.
The previous Pygments renderer dependency has been removed.

Docker images, OpenSSL, system libraries, Debian/SUSE repository packages,
monitoring plugins, and SLES installation media retain their own licenses.
The current release scope is the custom server packages, the SLES user package,
their corresponding sources, and this project's build workflow. It does not
include container images, dependency RPM/DEB bundles, or installation media.
Any expansion requires an inventory of the additional shipped bytes.

The bundled SUSE public key is trust material identified by the
fingerprints and checksums in the SLES manifests. They are not independently
authored project code; do not label them MIT merely because they are in this
repository. Retain their issuer identity and provenance.

## Required release notices

Each candidate must include this inventory, the project MIT license, and the
actual notices from the source packages being distributed. Source archives must
retain their full upstream and distribution license files. The generic GitHub
repository source archive does not replace corresponding NRPE sources.

For SLES, include the [prepared notice directory](packaging/licenses/sles12sp3/README.md)
as separate release assets alongside the unchanged binary and source RPMs.
The [review](docs/sles-license-review.md) closes the previously recorded SLES
OpenSSL, ACL-version and companion-MIT evidence gaps. It does not replace final
candidate completeness and provenance checks.

Keep the project's unofficial-build wording and NRPE's `LEGAL` trademark notice.
No endorsement or support entitlement from Nagios, Debian, or SUSE is implied.
Metadata labels alone do not establish that an arbitrary release bundle retains
all required notices. See the [release plan](docs/release-plan.md).

## Self-hosted website font

The website bundles Inter Variable from the official
[Inter project](https://github.com/rsms/inter), licensed under SIL OFL 1.1.
The verbatim notice is retained as `website/assets/Inter-OFL.txt` alongside
`InterVariable.woff2`; the font is served locally and is not an NRPE dependency.
No JetBrains font files, logos or illustrations are distributed.
