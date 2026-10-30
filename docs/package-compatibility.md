# NRPE package compatibility matrix

Reviewed: **30 October 2026**. This is a package/build-feature matrix, not a list
of operating systems that universally need a patch. A custom argument-enabled
build is relevant only when remote arguments are required and the installed
server package lacks compiled argument support. Fixed local commands do not
require that feature.

The project changes native packaging options rather than implementing an OS
patch. Argument support needs both `--enable-command-args` at build time and a
deliberate runtime policy (`dont_blame_nrpe=1`). A disabled runtime setting alone
does not establish that compilation is missing. Keep Bash command substitution
disabled and use [reviewed command definitions](configuration-examples.md).

## Confirmed packaging and runtime findings

The versions below identify inspected or recorded examples, not a promise that
they are the latest packages in every repository. Evidence is either a source
review or the explicitly listed container argument probe; neither establishes
production TLS or host lifecycle behavior. The [dated follow-up](package-reviews/2026-10-30.md) records the method,
versions, scope and corrected FreeBSD interpretation.
Only the targets marked **supported** are implemented by this tool.

| System / inspected package | Compiled arguments | Assessment | Tool support |
| --- | --- | --- | --- |
| Debian 11; recorded source `4.0.3-1` | Not enabled by the distribution recipe | Argument-enabled rebuild needed if remote arguments are required [D] | **Supported:** `debian11`, amd64 |
| Debian 12; recorded source `4.1.0-1` | Not enabled by the distribution recipe | Same build-option requirement [D] | **Supported:** `debian12`, amd64 |
| Debian 13; recorded source `4.1.3-1` | Not enabled by the inspected distribution recipe | Same build-option requirement [D] | **Supported:** `debian13`, amd64 |
| Debian 14 / Forky; recorded source `4.1.3-1` | Not enabled by that recorded recipe | Moving suite: inspect the actual newly selected source before rebuilding [D] | **Supported:** `debian14`, amd64 |
| SLES 12 SP3; installed old server `2.15-4.24`, project recipe `4.1.1` | The pinned OBS 4.1.1 recipe already enables arguments | Distinct case: native newer daemon, preserved OpenSSL ABI, Bash substitution disabled; not simply the Debian option change [S] | **Supported:** `sles12sp3`, x86_64 |
| FreeBSD; inspected port `4.2.0` | **Native binary not verified:** `ARGS` defaults off, but upstream handles the generated disable option unexpectedly | Native header/binary/protocol check required; no confirmed patch need [F] | **Not supported** |
| Ubuntu 22.04; `4.0.3-1ubuntu2` | Confirmed by container argument probe | Regular package rejects arguments at policy 0 and returns exact arguments at policy 1 [P] | **Not supported** |
| Ubuntu 24.04; `4.1.0-1ubuntu3` | Confirmed by container argument probe | No compile-option change needed for the tested feature [P] | **Not supported** |
| Alpine 3.22.7; `nrpe 4.1.1-r0` | Confirmed by container argument probe | No compile-option change needed for the tested feature [P] | **Not supported** |
| Fedora 43; `nrpe 4.1.3-4.fc43` | Confirmed by container argument probe | No compile-option change needed for the tested feature [P] | **Not supported** |
| AlmaLinux 9.8 / EPEL 9; `nrpe 4.1.2-2.el9` | Confirmed by container argument probe | No compile-option change needed; no claim for an actual RHEL host [P] | **Not supported** |
| Ubuntu; inspected `plucky-proposed` source `4.1.3-1ubuntu1` | Explicitly enabled by Ubuntu's packaging change | This example does not need our compile-option change; runtime arguments remain disabled by default [U] | **Not supported** |
| Alpine; inspected `aports` master recipe `nrpe 4.1.3-r0` | Explicit `--enable-command-args` | This recipe does not need our compile-option change [A] | **Not supported** |

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
| Arch Linux / AUR `nrpe 4.1.2-1` | Current AUR recipe omits the configure option; exact upstream source leaves the macro undefined when the option is absent. Official core/extra query found no `nrpe` package [P] | Source-level rebuild candidate; no AUR build/runtime test yet. The old official issue [R] remains historical context |
| Debian-derived distributions using unchanged Debian NRPE packaging | Possible inherited build behavior, not independently confirmed here | Identify the exact release, package source/version and architecture before classifying it; Ubuntu demonstrates why inheritance cannot be assumed |
| Other distributions/repositories | Not reviewed by this matrix | Review their current recipe and installed package; absence from this page means unknown, not affected or unaffected |

A candidate row adds no CLI target, build recipe or compatibility guarantee.
FreeBSD requires native BSD build/install/service validation. Existing Debian
or SLES packages must not be installed on another distribution or architecture;
our amd64 outputs are not ARM packages for a Raspberry Pi.

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
- **[F] FreeBSD:** the official [port Makefile](https://github.com/freebsd/freebsd-ports/blob/main/net-mgmt/nrpe/Makefile)
  identifies version 4.2.0 and an off-by-default `ARGS` option. The
  [follow-up](package-reviews/2026-10-30.md#freebsd-why-the-first-classification-needed-correction)
  records why Ports-generated `--disable-command-args` cannot be assumed to leave
  the compiled macro disabled in the reviewed upstream configure block.
- **[U] Ubuntu:** the official [4.1.3-1ubuntu1 acceptance record](https://lists.ubuntu.com/archives/plucky-changes/2024-December/003845.html)
  explicitly records Ubuntu's addition of `--enable-command-args` and the
  retained disabled runtime default. The record is dated 20 December 2024.
- **[A] Alpine:** the official [APKBUILD](https://github.com/alpinelinux/aports/blob/master/main/nrpe/APKBUILD)
  identifies 4.1.3-r0 and passes `--enable-command-args` to configure.
- **[R] Arch:** the official [FS#66574 report](https://bugs.archlinux.org/task/66574)
  identifies version 4.0.2 and the maintainer's May 2020 decision. It provides
  historical evidence, not an independently checked current package.

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
