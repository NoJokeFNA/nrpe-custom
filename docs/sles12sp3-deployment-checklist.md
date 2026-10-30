# SLES 12 SP3 deployment checklist

Use this checklist together with the [installation guide](installation.md#sles-12-sp3)
and [update/rollback procedure](updates-and-rollback.md). Examples use fictional
host `nrpe.example.internal`, monitoring address `192.0.2.10` and target address
`192.0.2.20`. Substitute your real values; do not publish private configuration.

## What the operator report established

The reported host was genuine SLES 12 SP3 x86_64. Installing the newer
`monitoring-plugins-nrpe` package updated the client, but `rpm -q nrpe` still
reported server `2.15-4.24`. Consequently the running old daemon rejected newer
`ssl_*` directives. Manually creating `/run/nrpe` allowed that old service to
start, but does not establish reboot persistence. A remote socket timeout was
also reported; its cause was not established by the supplied evidence.

This is not a successful installation or TLS validation of the custom 4.1.1
server. No completed target-host upgrade, reboot or rollback is claimed here.

A subsequent operator report on 2026-10-29 confirmed a running 4.1.1 test-host
daemon and successful remote version/load checks after permitting NRPE through
SuSEfirewall2 and removing client `-n`. Missing Swap/NTP executables caused
`Unable to read output`; installing their separate plugin packages resolved the
checks. See [plugin troubleshooting](troubleshooting.md#nrpe-unable-to-read-output).
This later functional evidence does not fill the lifecycle worksheet below or
prove certificate-authentication policy, reboot persistence or rollback.

## Before replacing a repository-installed server

Record a baseline on the intended host:

```sh
hostname
cat /etc/os-release
uname -m
rpm -q nrpe monitoring-plugins-nrpe system-user-nagios
rpm -qf /usr/sbin/nrpe
/usr/sbin/nrpe -V
getent passwd nagios
getent group nagios
sudo systemctl cat nrpe.service
sudo ss -ltnp 'sport = :5666'
```

Expect SLES `12.3` and `x86_64`. Missing optional client/user packages are not a
server-version result. Save the exact previous server RPM and its checksum,
root-only configuration/includes/TLS backups and service overrides. A backup
of `/etc/nrpe.cfg` alone omits included command files and private keys.

Keep recovery access. Use an isolated test host with a snapshot for lifecycle
validation; do not reboot a production system just to complete this checklist.
The NRPE server package is distinct from Nagios Core: replacing `nrpe` does not
require uninstalling the Nagios scheduler or monitoring plugins.

## Upgrade the actual server

1. Verify all archive checksums and inspect the local server RPM's name,
   version, architecture, dependencies and `/usr/sbin/nrpe` payload.
2. Follow [server installation](installation.md#install-the-server-and-its-real-dependency):
   install the explicit local `nrpe-4.1.1-0.withargs1.x86_64.rpm` with RPM's
   upgrade operation, together with the real user-package dependency if missing.
   Do not first remove the existing server or replace it by the client package.
3. Confirm `rpm -q nrpe`, `rpm -qf /usr/sbin/nrpe` and `/usr/sbin/nrpe -V`
   all identify the intended server. Stop if they still identify 2.15.
4. Review retained configuration and every `.rpmnew`/`.rpmsave` file. Merge the
   [complete TLS policy](installation.md#sles-certificate-authenticated-tls),
   actual credentials, allowed hosts and existing plugin commands. Preserve
   disabled arguments unless deliberately required; keep Bash substitution off.
5. Review overrides, reload unit definitions and restart `nrpe.service` using
   the installation guide. Confirm the packaged `-f` unit, service identity,
   runtime directory, listener and logs. Do not leave a manual `-d -n` listener
   competing with systemd.

## Validate in order

| Check | Expected result | Actual result |
| --- | --- | --- |
| Server identity | Installed RPM and executable both 4.1.1, custom Release recorded | Not run |
| Existing account | Expected Nagios UID/GID preserved | Not run |
| Configuration | Reviewed includes/commands/TLS, no unknown-option errors | Not run |
| Managed service | Active intended `nrpe.service`; correct listener and `/run/nrpe` | Not run |
| TCP from monitoring host | Target port reachable under approved firewall rules | Not run |
| Authenticated TLS | Intended CA/server/client credentials work; missing/invalid client rejected | Not run |
| Real fixed plugin | Local service-user result agrees with remote result | Not run |
| Argument policy | Default rejection; optional deliberate activation verified separately | Not run |
| Controlled test-host reboot | New boot ID, active service and authenticated remote check recover | Not run |
| Package/config rollback | Saved previous version and configuration restore the known baseline | Not run |

Use the actual monitoring client's certificate options from the installation
guide. A timeout requires reachability/listener/log diagnosis; do not assume a
TLS defect or switch off encryption. Build-time `--ca-cert` does not provision
NRPE runtime credentials. Manual `mkdir /run/nrpe` is not a reboot fix.

Record date, release tag, source commit, package SHA-256, actual commands, exit
statuses and redacted evidence. Mark failures and unavailable scenarios honestly.
For a full host lifecycle record use the
[deployment validation worksheet](deployment-validation-template.md).
