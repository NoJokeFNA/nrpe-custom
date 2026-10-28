# Updating and rolling back a deployed package

These are target-server procedures, not `nrpe.py` commands. Start with the
[installation guide](installation.md) and the [upstream manuals](../README.md#using-a-built-package).
Use a maintenance window and test the process on an equivalent disposable server
before a production rollout. Container package/protocol tests do not exercise
your server's service manager, firewall, local checks, or configuration migration.

## Before an update

1. Record the installed package version, distribution, service state, configuration
   locations and a known successful check from the actual monitoring server.
2. Keep the exact previously installed server package and its original checksum
   manifest in a local `previous/` directory. Keep exactly one server version
   there. An installed custom package may not be downloadable from a repository;
   a filesystem/configuration backup alone cannot recreate its original binary.
3. Preserve root-only backups of configuration, included snippets, custom scripts,
   ownership/permissions, service overrides, TLS certificates and private keys.
   Keys may live outside the main configuration directory. Do not commit or
   upload these backups, and do not assume this project's build CA backs them up.
4. Build and verify the replacement for the exact destination release. Transfer
   it into a separate `replacement/` directory and check `SHA256SUMS` there.
   Preserve the previous build outputs before using `--rebuild` on a workstation.
5. Review version/configuration differences and dependency changes. If a package
   transaction would remove unrelated monitoring components or replace a shared
   user package, stop and resolve that change first.

Example root-only configuration backups, run on the destination. Save the printed
backup path; use that same path when restoring, rather than creating a new one.

For Debian:

```sh
nrpe_backup_dir="/var/backups/nrpe-custom/$(date -u +%Y%m%dT%H%M%SZ)"
sudo install -d -m 0700 "$nrpe_backup_dir"
sudo cp -a /etc/nagios "$nrpe_backup_dir/nagios"
dpkg-query -W -f='${Package} ${Version} ${Architecture}\n' nagios-nrpe-server |
  sudo tee "$nrpe_backup_dir/installed-package.txt" > /dev/null
printf 'Backup directory: %s\n' "$nrpe_backup_dir"
```

For SLES 15 SP3:

```sh
nrpe_backup_dir="/var/backups/nrpe-custom/$(date -u +%Y%m%dT%H%M%SZ)"
sudo install -d -m 0700 "$nrpe_backup_dir"
sudo cp -a /etc/nrpe.cfg "$nrpe_backup_dir/nrpe.cfg"
rpm -q nrpe system-user-nagios |
  sudo tee "$nrpe_backup_dir/installed-package.txt" > /dev/null
printf 'Backup directory: %s\n' "$nrpe_backup_dir"
```

These examples back up the standard main configuration only. Add every configured
include directory, local plugin/wrapper, service override and external TLS file
to the backup before changing the installation. On SLES, inspect the configuration
for the actual include paths; do not assume Debian's layout.

## Install and check the replacement

Install the explicit local file from `replacement/` using APT or zypper as in the
[installation guide](installation.md). Package scripts can start or restart NRPE;
use your site's maintenance/access controls during the transaction. Review
configuration prompts rather than automatically forcing new or old files.

After installation:

- Confirm the intended custom version with `dpkg-query -W nagios-nrpe-server`
  or `rpm -q nrpe`; inspect package-created `.dpkg-dist`, `.dpkg-old`, `.rpmnew`
  and `.rpmsave` files where present.
- Merge configuration deliberately, keeping allowed hosts, reviewed command
  definitions, TLS settings and disabled Bash substitution. Do not automatically
  enable `dont_blame_nrpe` simply because the new binary supports arguments.
- Restart the appropriate service and inspect `systemctl status` and `journalctl`
  using the commands in the installation guide.
- Repeat the known check from the real monitoring server with its production TLS
  settings. Check both a normal result and the argument policy you actually use.

If the package installs but checks fail, retain the transaction/service logs and
identify whether the cause is configuration, missing plugins, TLS, access rules,
or the binary. Reinstalling a package alone does not restore configuration.

## Debian rollback

Change into the saved `previous/` directory and verify its original checksum file.
The following intentionally permits a version downgrade to the local file:

```sh
sha256sum --check SHA256SUMS
sudo systemctl stop nagios-nrpe-server
sudo apt install --allow-downgrades ./nagios-nrpe-server_*_amd64.deb
```

Set `nrpe_backup_dir` to the saved path from before the update, then restore the
reviewed configuration and original ownership/permissions:

```sh
sudo cp -a "$nrpe_backup_dir/nagios/." /etc/nagios/
sudo systemctl restart nagios-nrpe-server
sudo systemctl status nagios-nrpe-server --no-pager
dpkg-query -W nagios-nrpe-server
```

Compare the active include tree with the backup. Copying files back does not
remove snippets introduced by the failed update; inspect and reconcile those
before restarting. Restore separately backed-up TLS files, wrappers and service
overrides as needed. Package scripts may restart the service during rollback too.

## SLES 15 SP3 rollback

From the saved `previous/` directory:

```sh
sha256sum --check SHA256SUMS
sudo systemctl stop nrpe
sudo zypper install --oldpackage --allow-unsigned-rpm ./nrpe-[0-9]*.x86_64.rpm
```

`--oldpackage` deliberately allows the older version; `--allow-unsigned-rpm`
applies to this project's local custom RPM installation. Keep repository
signature and dependency checks enabled. Keep an existing compatible
`system-user-nagios`; do not downgrade or remove a shared user package as part
of a server-only rollback.

With `nrpe_backup_dir` set to the saved pre-update backup path:

```sh
sudo cp -a "$nrpe_backup_dir/nrpe.cfg" /etc/nrpe.cfg
sudo systemctl restart nrpe
sudo systemctl status nrpe --no-pager
rpm -q nrpe
```

Also restore/reconcile included snippets, TLS files, scripts and overrides from
their backups. Compare `.rpmnew`/`.rpmsave` files rather than treating either as
the authoritative configuration automatically. Repeat the original remote check.

## After recovery

Confirm the old package version and production checks actually work again. If a
dependency transaction changed other packages, assess those separately; restoring
NRPE alone is not a whole-system rollback. Use your system backup/recovery process
if the host is unresponsive or package operations are no longer possible.

A version hold/lock can be a temporary operational choice, but it can also block
security updates. Record the reason, owner and review date rather than silently
pinning an old custom package forever. See the [maintenance policy](maintenance.md).
