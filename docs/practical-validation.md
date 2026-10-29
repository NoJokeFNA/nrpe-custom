# Practical validation beyond container CI

These checks cover host and service behavior that the automated package/TLS
matrix does not exercise. Use disposable hosts and test certificates. Follow
the [installation guide](installation.md), [upstream NRPE documentation](https://github.com/NagiosEnterprises/nrpe)
and [update/rollback procedure](updates-and-rollback.md) for deployment details.

## Current evidence and result recording

The published SLES 12 SP3 release passed all five container build/install/TLS
and source/archive gates plus Linux/Windows Python unit tests. Exact release and
commit evidence, including the earlier SLE-15 scope, is retained in the
[release history](release-history.md). Windows Docker Desktop and real VM
scenarios below remain **not run**.

On 2026-10-28 the current cloud environment had no `/dev/kvm`, QEMU/libvirt or
supplied test-VM access. The maintainer confirmed that no test VMs are available.
These scenarios are prepared for later execution, not replaced by container or
hosted Windows unit tests. Do not run package migration/reboot tests on a
production server to fill this gap.

On 2026-10-29 the operator supplied an installation attempt from a SLES 12 SP3
host. The client package was updated to 4.1.1, while `rpm -q nrpe` still showed
server 2.15. Unknown TLS directives and a remote timeout therefore do not prove
that the custom server failed after installation. No successful custom-server
migration, authenticated remote check, reboot or rollback was supplied in that
report. The [SLES-specific checklist](sles12sp3-deployment-checklist.md) separates
these checks. Hostnames, IPs and raw shell history are intentionally omitted.

Later on 2026-10-29 the operator confirmed a running NRPE 4.1.1 service on a
SLES 12 SP3 test host. Packet capture showed inbound TCP SYN packets without
replies; SuSEfirewall2 allowed SSH but dropped NRPE traffic. After a scoped TCP
5666 firewall allowance, a remote encrypted version query succeeded. Removing
client `-n` also made the remote load check succeed. Swap/NTP checks then failed
because their configured executables were absent; the operator confirmed that
installing `monitoring-plugins-swap` and `monitoring-plugins-ntp` resolved them.
See [missing-plugin troubleshooting](troubleshooting.md#nrpe-unable-to-read-output).

These are operator-reported functional results. They do not establish mandatory
client-certificate/hostname verification, package checksum provenance, a completed
upgrade/rollback procedure or reboot persistence. The separate lifecycle matrix
remains open; no private hostnames or addresses are published.

For each scenario record passed, failed, blocked or not run, with:

- Date, tester, exact Git commit/release tag, package version and SHA-256.
- Host OS/release/architecture, Python, Docker Engine, Compose and Buildx versions
  where applicable; VM image/release and service unit for deployment tests.
- Scenario, command, expected/actual outcome, exit status and run ID.
- A redacted failure excerpt and follow-up issue when a check fails.

Keep full run reports, private paths, configuration backups, company certificates
and keys outside Git. Share only reviewed, sanitized evidence. A pass applies
to the tested host/artifacts, not automatically to every supported platform.

## Windows Docker Desktop

Use an actual Windows host with Docker Desktop's Linux engine. Record the shell
and terminal; include Compose 5.6.1 and Buildx 0.38.1 when reproducing the original
report, then test current supported versions separately. Use a clean checkout in
a path containing spaces and non-ASCII characters, for example
`C:\NRPE validation\Project Ω\nrpe-custom`. Put a public test CA certificate in a
different such directory; never pass a private key to `--ca-cert`. These are
illustrative test paths, not required installation locations. The `Ω` deliberately
exercises Unicode handling; use real folders and certificate paths on your test host.

From that checkout in a terminal:

```sh
python3 --version
docker version
docker compose version
docker buildx version
python3 nrpe.py doctor
python3 nrpe.py verify debian12 --ca-cert "C:/NRPE validation/Company CA Ω/company-ca.pem" --pull
python3 nrpe.py status
python3 nrpe.py logs --last
```

Use your actual certificate path. Immediately after `verify`, check `$?` in a
POSIX-compatible shell or `$LASTEXITCODE` in PowerShell, before running the
next command. The expected result is a complete successful
build/install/TLS run, with no temporary-path failure at "load local bake
definitions". For intentional repeat builds of existing output, add `--rebuild`.

| Scenario | Expected result |
| --- | --- |
| PEM CA in a path with spaces/non-ASCII characters | Certificate is accepted and the complete verify run passes |
| Equivalent DER CA exported to a `.cer` file | Same successful outcome; no path-format dependency |
| Windows account using a short temporary-directory alias | Repeat the CA run from that actual account; no dependence on long/short temp path spelling |
| Missing file, malformed certificate or empty file | Nonzero exit with an actionable certificate error before a successful build is reported |
| TLS-intercepted repository with its CA omitted or an unrelated CA supplied | An actual certificate trust failure produces a CA hint and failed run; do not break public TLS merely to manufacture a result |
| Docker Desktop stopped | `doctor` reports Docker readiness failure; no successful workflow is claimed |
| Ctrl+C during a build and during an integration test | Exit 130, interrupted run recorded, locks released by normal cleanup; inspect any remaining project containers before retrying |
| Menu: arrows, filtering with `/`, Space/A, Enter, Esc and resize down to 60×16 | Correct navigation and visible focus; no action runs while browsing |
| Menu: Back through targets/options/review, then cancel | Targets, CA choice and options persist only for the session; no rebuild on cancellation |
| Menu: 0/1/12+ drive roots; mapped/disconnected roots; quoted long/UNC paths | Drives stay in their own selector; failure/cancel retains the directory and focus; complete path remains inspectable |
| Menu: explicit CA removal while `NRPE_CA_CERT` is set | This session omits the CA; environment and runtime NRPE TLS settings remain unchanged |
| Menu: live phase display and Ctrl+C during actual build/test | Original exit/report outcome, retained logs and normal container/lock cleanup |
| Menu: cleanup preview, cancellation, changed candidates, then approved disposable data | Preview never deletes; changed scope requires another preview; protected evidence remains |

Test TLS omission only on an approved test network that requires its test CA.
A failure pulling an image through Docker Desktop/BuildKit can require trust in
that component; build-time `--ca-cert` does not configure the Docker engine or
registry trust. See [network and trust boundaries](network.md).

For interruption checks, preserve any previous valid package and its hash first.
Check `status`, the interrupted report and `docker ps -a`; follow
[lock recovery guidance](workflow.md#results-logs-and-concurrent-runs) if cleanup
was prevented. Do not delete locks belonging to a running process or use global
container cleanup. Install `requirements-menu.txt` to exercise the optional menu.

## Debian and SLES test VMs

Use one copy of the [deployment validation worksheet](deployment-validation-template.md)
per target. The operator confirmed no test VMs are available as of 2026-10-28;
execution is **blocked by unavailable infrastructure**. The procedure and result
template are prepared, while all VM/systemd/reboot/update/rollback results remain
not run.

Use disposable amd64 VMs for Debian 11, 12, 13, 14 and genuine SLES 12 SP3.
Keep matching signed repositories available and take a recoverable baseline
snapshot. Use a separate monitoring client for remote TLS checks. Do not
substitute Leap or another SLES service pack. Forky results apply to the tested
image date; use a fresh equivalent image when its base changes.

For each target, download the matching release archive through a trusted
channel, check the release checksum, then check the binary `SHA256SUMS` inside
the target directory. Retain corresponding sources/notices. Install using the
exact local package commands in the [installation guide](installation.md).
Do not install build outputs on the development host.

| Scenario | Expected result and evidence |
| --- | --- |
| Fresh install | Correct custom version/architecture, dependencies resolved, real Nagios user, default `dont_blame_nrpe=0` |
| Service start/restart | Correct distribution service starts; `systemctl status` and `journalctl` show no startup/configuration errors |
| Reboot after enabling service | Service becomes active after a real VM reboot; the remote check succeeds again |
| Actual monitoring plugin | An installed plugin runs as the NRPE service user, returns the expected output/status locally and through the remote TLS check |
| Argument policy | Arguments rejected by default; after deliberate activation, reviewed command/arguments work and forbidden shell syntax remains rejected |
| Access and TLS | Intended monitoring client accepted with the configured TLS policy; unapproved client and invalid client credentials rejected where required by that policy |
| Update | Previous verified package upgraded to a distinct verified version; site configuration/includes/permissions retained and configuration prompts reviewed |
| Rollback | Exact previous package plus configuration restored; service and the original remote check recover; shared user package retained |

Use the service/configuration paths from the installation guide: Debian
`nagios-nrpe-server` and `/etc/nagios/nrpe.cfg`; SLES `nrpe` and `/etc/nrpe.cfg`.
Review plugin paths and TLS/access settings using upstream manuals. Use test
credentials and approved network rules rather than opening NRPE to all clients.

An update/rollback pass requires two distinct real package versions and their
original checksums. Reinstalling the same file is not an upgrade/downgrade test.
If only one suitable package is available, mark that scenario blocked and retain
the baseline; never rename a binary to invent another package version. A VM
snapshot is emergency recovery, not evidence that package/configuration rollback
worked. Record these outcomes separately.

## Follow-up

Add sanitized actual results and their exact environments to the
[release plan](release-plan.md#remaining-work-in-priority-order). Leave scenarios
open until performed; log any failure before claiming practical platform support.
