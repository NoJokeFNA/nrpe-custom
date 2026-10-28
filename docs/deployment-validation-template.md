# Disposable VM deployment validation record

Template only: no VM scenario has been executed by filling in this document.
Copy it for each target into an ignored local evidence directory, for example
`.nrpe/validation/debian12.md`. Keep raw logs, certificates, keys, access details
and configuration backups outside Git. Publish only reviewed, sanitized results.

Follow the [practical validation procedure](practical-validation.md#debian-and-sles-test-vms),
[installation guide](installation.md) and [rollback procedure](updates-and-rollback.md).
Do not use a production host. An actual VM snapshot and console/recovery access
are prerequisites; a container is not a replacement for these tests.

## Identity and preparation

| Field | Recorded value |
| --- | --- |
| Tester / date / timezone | Not recorded |
| Target: debian11 / debian12 / debian13 / debian14 / sles12sp3 | Not selected |
| Disposable VM OS, release, architecture and image date | Not recorded |
| VM snapshot and tested console/recovery access | Not prepared |
| Workflow commit / published release tag | Not selected |
| Baseline binary package filename, exact installed version and SHA-256 | Not recorded |
| Candidate binary package filename, exact version and SHA-256 | Not recorded |
| Trusted checksum/signature verification | Not performed |
| Config/includes/permissions backup and original plugin paths | Not prepared |
| Separate monitoring client version and approved access rules | Not prepared |
| Test CA/server/client identities (no private material) | Not prepared |
| Pre-reboot / post-reboot boot IDs | Not recorded |

Baseline and candidate must be two distinct real package versions. Verify and
save the original binaries/checksums before starting; never rename an artifact
to simulate an update. If either package, repository access or recovery is
missing, mark the relevant scenarios **blocked** and stop before installation.

## Read-only baseline inventory

On the VM, record its actual identity and service definition. Use the correct
branch below; these commands do not install packages or restart services:

```sh
cat /etc/os-release
uname -m
cat /proc/sys/kernel/random/boot_id
getent passwd nagios
```

Debian:

```sh
dpkg-query -W -f='${Package} ${Version} ${Architecture}\n' nagios-nrpe-server
systemctl cat nagios-nrpe-server.service
systemctl is-enabled nagios-nrpe-server.service
systemctl is-active nagios-nrpe-server.service
```

SLES 12 SP3:

```sh
rpm -q --queryformat '%{NAME} %{VERSION}-%{RELEASE} %{ARCH}\n' nrpe
systemctl cat nrpe.service
systemctl is-enabled nrpe.service
systemctl is-active nrpe.service
```

On a fresh VM the package or service may not exist; record that outcome instead
of treating missing baseline components as an installation pass. Save a baseline
remote-check result with its exact command, TLS policy and exit status before
any update. An already failing baseline TLS connection cannot prove successful
remote-check recovery after rollback.

## Execute and record sequentially

Use **passed**, **failed**, **blocked** or **not run** for each scenario. Fill in
actual commands, exit codes, expected/observed results and reviewed evidence;
do not prefill a success based on container CI.

| Order | Scenario | Status | Expected / observed / evidence |
| --- | --- | --- | --- |
| 1 | Fresh install on a separate clean snapshot | Not run | Correct version, architecture, dependencies and real user; runtime arguments disabled |
| 2 | Service start and restart | Not run | Actual systemd unit active, expected listener, no configuration errors |
| 3 | Fixed real monitoring plugin | Not run | Runs as service user; local and remote output/exit status agree |
| 4 | Access, TLS and argument policy | Not run | Approved client works; invalid credentials/unapproved clients rejected; arguments rejected by default and accepted only after deliberate activation |
| 5 | Real VM reboot | Not run | Boot ID changes, service enabled/active, listener and authenticated remote check recover |
| 6 | Upgrade from verified baseline to distinct candidate | Not run | Expected package version; reviewed config prompts, includes/permissions retained; actual remote check passes |
| 7 | Package/configuration rollback | Not run | Original package and config restored; service and previously working baseline check recover; shared user package retained |
| 8 | Snapshot recovery, if necessary | Not run | Record separately; snapshot restoration does not prove package rollback |

Return to the required baseline snapshot between incompatible scenarios rather
than carrying changes from the fresh-install test into an alleged baseline
upgrade. A reboot or migration is performed by the operator only after reviewing
the disposable VM identity, snapshot and recovery prerequisites.

## Completion and follow-up

- Overall result: **not run**.
- Failed/blocked scenarios and concrete reasons: not recorded.
- Restored final state and temporary network/certificate cleanup: not recorded.
- Reviewer and sanitized evidence references: not recorded.

Update the [release plan](release-plan.md#remaining-work-in-priority-order) only
with actual results for the exact tested OS and artifacts. Leave other targets
open. Windows Docker Desktop validation uses its own procedure and is not
established by completing this VM worksheet.
