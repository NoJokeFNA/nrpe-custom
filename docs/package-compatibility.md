# NRPE package compatibility matrix

Reviewed: **30 October 2026**. The assessment answers whether a custom build is
needed because the installed NRPE package lacks required command-argument or
TLS/SSL support. It applies to the listed package and requirement, not every
installation of that OS.

For exact tested versions, argument settings, TLS checks and source/binary
inspection, open **[Test results — 30 October 2026](package-reviews/2026-10-30.md)**.
That report is also available as **Test results** in the documentation navigation.
This page summarizes the patch decision; the report keeps the technical evidence.

**Assessment:** **Yes** means a custom build is needed for the stated requirement;
**No** means the reviewed regular package already provides it; **Unconfirmed**
means the evidence is insufficient. Debian's **Yes** applies only when remote
arguments are needed. SLES's **Yes** refers to replacing the cited legacy 2.15
server, not every SLES installation or an unconditional requirement for this tool:
a compatible maintained regular package can also replace it. The tool does not
patch firewall rules, missing plugins or TLS configuration.

## Version selection

New reviews compare the latest stable upstream release with the newest candidate
from each OS release's refreshed native repositories. The
[test results](package-reviews/2026-10-30.md#latest-stable-upstream-comparison)
record the current 4.2.0 upstream check and distribution versions separately.
Previous versions remain dated evidence, not pins for the next review.

## Confirmed packaging and runtime findings

Each row applies to the exact listed package. Source inspection, container tests
and native-host validation are different evidence levels; follow the linked
source markers for details. Only targets marked **supported** are implemented.

| System / inspected package | Compiled arguments | Assessment: tool patch needed? | Tool support |
| --- | --- | --- | --- |
| Debian 11; recorded source `4.0.3-1` | Not enabled by the distribution recipe | **Yes** [D] | **Supported:** `debian11`, amd64 |
| Debian 12; recorded source `4.1.0-1` | Not enabled by the distribution recipe | **Yes** [D] | **Supported:** `debian12`, amd64 |
| Debian 13; recorded source `4.1.3-1` | Not enabled by the inspected distribution recipe | **Yes** [D] | **Supported:** `debian13`, amd64 |
| Debian 14 / Forky; recorded source `4.1.3-1` | Not enabled by that recorded recipe | **Yes** [D] | **Supported:** `debian14`, amd64 |
| SLES 12 SP3; installed old server `2.15-4.24`, project recipe `4.1.1` | The pinned OBS 4.1.1 recipe already enables arguments | **Yes** [S] | **Supported:** `sles12sp3`, x86_64 |
| FreeBSD 14 amd64; official `nrpe 4.2.0` package | Argument-enabled code confirmed in the official binary; runtime/TLS not tested | **No** [F] | **Not supported** |
| Ubuntu 22.04; `4.0.3-1ubuntu2` | Confirmed by container argument probe | **No** [P] | **Not supported** |
| Ubuntu 24.04; `4.1.0-1ubuntu3` | Confirmed by container argument probe | **No** [P] | **Not supported** |
| Alpine 3.22.7; `nrpe 4.1.1-r0` | Confirmed by container argument probe | **No** [P] | **Not supported** |
| Fedora 43; `nrpe 4.1.3-4.fc43` | Confirmed by container argument probe | **No** [P] | **Not supported** |
| AlmaLinux 9.8 / EPEL 9; `nrpe 4.1.2-2.el9` | Confirmed by container argument probe | **No** [P] | **Not supported** |
| Ubuntu; inspected `plucky-proposed` source `4.1.3-1ubuntu1` | Explicitly enabled by Ubuntu's packaging change | **No** [U] | **Not supported** |
| Alpine; inspected `aports` master recipe `nrpe 4.1.3-r0` | Explicit `--enable-command-args` | **No** [A] | **Not supported** |

For Debian, recorded versions come from the
[published package evidence](release-history.md#sles-12-sp3-release-2026-10-28).
The builder discovers the actual source from the selected suite; this matrix
does not pin a future build to those examples. It fails for review if arguments
are already enabled in a changed Debian configure recipe. Repository availability
and [upstream support lifecycles](maintenance.md) are separate concerns.

The Ubuntu finding applies to the cited package, not automatically every Ubuntu
release, derivative, PPA or locally rebuilt binary. The Alpine master recipe is
not a verification of every stable branch. FreeBSD Ports options may be changed
locally or by a package builder; inspect the installed package's options rather
than assuming every binary uses the defaults.

## Historical evidence and open candidates

| Candidate | Available evidence | Remaining work |
| --- | --- | --- |
| Arch Linux / AUR `nrpe 4.1.2-1` | Inspected AUR recipe omits argument support [AR]. The former official package deliberately disabled it for security reasons [R] [AS] | Optional build requires security-policy and native-package review. No automatic patch recommendation or supported target; AUR runtime remains untested |
| Debian-derived distributions using unchanged Debian NRPE packaging | Possible inherited build behavior, not independently confirmed here | Identify the exact release, package source/version and architecture before classifying it; Ubuntu demonstrates why inheritance cannot be assumed |
| Other distributions/repositories | Not reviewed by this matrix | Review their current recipe and installed package; absence from this page means unknown, not affected or unaffected |

A disabled feature can be an intentional security restriction. Its absence alone
is not a packaging defect or a recommendation to enable it. This tool enables
argument support when explicitly needed; it does not fix the cited vulnerabilities
by enabling that support. Prefer fixed commands when arguments are unnecessary.

A candidate row adds no CLI target, build recipe or compatibility guarantee.
FreeBSD requires native BSD build/install/service validation. Existing Debian
or SLES packages must not be installed on another distribution or architecture;
our amd64 outputs are not ARM packages for a Raspberry Pi.

## TLS and patch necessity

A TLS failure alone is **not** a reason to apply this tool's patch. First check
TCP reachability, matching TLS settings, trusted certificates, permissions and
the actual daemon version using [Verify TLS & identity](tls-validation.md).
A custom build or newer server can be necessary when the installed binary
cannot provide the required TLS/SSL support. This tool enables compiled
arguments on Debian and provides a native newer server for the cited legacy
SLES case; its current changes are not a general fix for every TLS failure.

The [dated TLS follow-up](package-reviews/2026-10-30.md#tls-follow-up) records
successful certificate-authenticated TLS 1.2 tests for the five container-tested
regular packages above. Their assessment remains **No** for the tested argument
and TLS requirements. A passing
TLS test adds no need for a custom build; a failed handshake remains unconfirmed
until its cause is established. Certificate-policy changes need configuration,
not automatically a rebuilt binary.

## Evidence sources

- **[D] Debian:** inspected [4.1.3-1 build rules](https://sources.debian.org/src/nagios-nrpe/4.1.3-1/debian/rules/)
  omit `--enable-command-args`. Recorded Debian 11–14 source/custom versions and
  actual project build/install/TLS evidence are in the linked release history.
  The [Debian transformation](../scripts/enable_command_args.py) makes the narrow
  option insertion and rejects an already-enabled recipe.
- **[S] SLES:** the [pinned OBS source manifest](../packaging/sles12sp3-source.json)
  identifies NRPE 4.1.1 at revision `835292739a5736a9d8f0460f670b6f15`.
  The [native build guide](sles12sp3.md) describes the actual policy changes;
  the [operator field note](../website/content/sles12-handshake.md) separates the
  old server, client/server package confusion, firewall and plugin problems.
- **[F] FreeBSD:** the [official port](https://github.com/freebsd/freebsd-ports/blob/main/net-mgmt/nrpe/Makefile)
  and the [exact official binary](package-reviews/2026-10-30.md#freebsd-official-binary-follow-up)
  were inspected. The report explains why `ARGS=off` does not describe the compiled
  behavior of that binary. Native runtime and TLS checks remain open.
- **[U] Ubuntu:** the official [4.1.3-1ubuntu1 acceptance record](https://lists.ubuntu.com/archives/plucky-changes/2024-December/003845.html)
  explicitly records Ubuntu's addition of `--enable-command-args` and the
  retained disabled runtime default. The record is dated 20 December 2024.
- **[A] Alpine:** the official [APKBUILD](https://github.com/alpinelinux/aports/blob/master/main/nrpe/APKBUILD)
  identifies 4.1.3-r0 and passes `--enable-command-args` to configure.
- **[R] Arch:** the official [FS#66574 report](https://bugs.archlinux.org/task/66574)
  identifies NRPE 4.0.2 and the May 2020 refusal to restore the feature, explicitly
  citing [AVG-587](https://security.archlinux.org/AVG-587). The
  [2018 advisory](https://security.archlinux.org/ASA-201801-14) records disabling
  argument support as the security measure. This establishes the historical
  official-package decision, not the intent of today's AUR maintainer or a
  current-version vulnerability assessment.

- **[P] Runtime/source follow-up:** [30 October 2026 review](package-reviews/2026-10-30.md)
  and [machine-readable identities/results](package-reviews/2026-10-30.json).
  Five container probes passed; Arch's current AUR evidence is source-only.

## Classify a real installation

1. Record OS/release/architecture, package name/version, repository origin and
   the daemon executable's version/owner. Distinguish `nrpe` from `check_nrpe`.
   The [read-only diagnostic](troubleshooting.md#read-only-target-server-inspection)
   can help inventory an existing Linux host.
2. Inspect the exact package's build recipe/options for compiled argument support.
   A generic comment in `nrpe.cfg` or a version number alone is not evidence.
3. Review the main configuration and includes for the intended runtime argument
   policy. Keep arguments disabled when fixed commands meet the requirement.
4. On an isolated target, verify an actual permitted argument-bearing request
   over the intended TLS connection and compare it with the local plugin result.
   A rejected request can also result from runtime policy, access or bad command
   definitions; a timeout or TLS failure does not prove a missing build option.
5. Before adding a new supported target, implement matching native packaging,
   source/license export, fresh installation and protocol tests, then the
   [separate host lifecycle checks](practical-validation.md).

## Keep the matrix current

During the [maintenance review](maintenance.md#human-review-cadence), record the
review date, exact package/repository and recipe revision or immutable version,
source link, relevant configure options and evidence type. Keep source inspection,
container protocol results and real-host outcomes distinct. Recheck moving
branches before acting on their entries and update changed findings rather than
silently extending them to all releases of a distribution.

[D]: https://sources.debian.org/src/nagios-nrpe/4.1.3-1/debian/rules/
[S]: https://api.opensuse.org/public/source/server:monitoring/nrpe/nrpe.spec?rev=835292739a5736a9d8f0460f670b6f15
[F]: package-reviews/2026-10-30.md#freebsd-official-binary-follow-up
[P]: package-reviews/2026-10-30.md#tls-follow-up
[U]: https://lists.ubuntu.com/archives/plucky-changes/2024-December/003845.html
[A]: https://github.com/alpinelinux/aports/blob/master/main/nrpe/APKBUILD
[R]: https://bugs.archlinux.org/task/66574

[AR]: package-reviews/2026-10-30.md#arch-current-repository-absence-and-aur-source-review
[AS]: https://security.archlinux.org/AVG-587
