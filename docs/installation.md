# Installing a custom NRPE package

Run these commands on the destination Linux server. Python, Docker, and this
checkout are needed on the build workstation, not on the destination server.
Use a package built for the destination's distribution release and architecture.
The current SLES target is **SLES 12 SP3 x86_64**.

For the complete NRPE server/client and Nagios setup, use the
[official NRPE documentation](https://github.com/NagiosEnterprises/nrpe) and
[Nagios Core documentation](https://assets.nagios.com/downloads/nagioscore/docs/nagioscore/4/en/).
This guide covers deployment of the custom packages and essential configuration
checks; it does not replace those manuals or distribution-specific plugin and
TLS instructions.

## Prepare the files

Build and test the selected target on the workstation with, for example,
`python3 nrpe.py verify debian12` or `python3 nrpe.py verify sles12sp3`.
Copy the following files into a dedicated directory on the destination server:

| Destination | Build output directory | Files to copy |
| --- | --- | --- |
| Debian 11 | `output/debian11/` | `nagios-nrpe-server_*_amd64.deb`, `SHA256SUMS` |
| Debian 12 | `output/debian12/` | `nagios-nrpe-server_*_amd64.deb`, `SHA256SUMS` |
| Debian 13 | `output/debian13/` | `nagios-nrpe-server_*_amd64.deb`, `SHA256SUMS` |
| Debian 14 | `output/debian14/` | `nagios-nrpe-server_*_amd64.deb`, `SHA256SUMS` |
| SLES 12 SP3 | `output/sles12sp3/` | `nrpe-*.x86_64.rpm`, `system-user-nagios-*.noarch.rpm`, `monitoring-plugins-nrpe-*.x86_64.rpm`, `SHA256SUMS` |

Keep exactly one server package version in that directory so the wildcards below
select the intended package. Source RPMs, manifests, and Debian build information
are useful provenance but are not installed on the destination.

Change into the directory containing the copied files and verify them:

```sh
sha256sum --check SHA256SUMS
```

Continue only if every entry reports `OK`. Copy the checksum file through a
trusted channel alongside the packages; checksums detect changes but do not
authenticate the publisher by themselves. Keep all three SLES binary RPMs available
for this check even if the destination already has the user package installed.
For releases that include `SHA256SUMS.sig`, first perform the
[release authentication check](release-signing.md#consumer-verification) using
an independently trusted maintainer key before extracting/installing packages.
Unsigned releases are identified in the [release history](release-history.md).

If NRPE is already installed, back up its configuration before updating. Review
package-manager prompts about configuration files and dependencies. Preserve
the site's command definitions, allowed monitoring hosts, and TLS configuration.
Package installation may start or restart a service.

For an existing deployment, follow [updates and rollback](updates-and-rollback.md)
before replacing packages. The [configuration examples](configuration-examples.md)
and [maintenance policy](maintenance.md) describe optional checks and verification
boundaries.

## Replace an existing distribution installation

The package being replaced is the **NRPE daemon**, not Nagios Core. Keep the
Nagios scheduler, plugin packages and site checks. The local custom server has
the same package name as its distribution counterpart, so use the package
manager's install/upgrade operation; do not uninstall the old server first.

| Existing installation | Local replacement | Required post-install identity |
| --- | --- | --- |
| Debian `nagios-nrpe-server` from official APT sources | Matching-release `nagios-nrpe-server_*_amd64.deb` with `apt install ./...` below | Package version contains the intended `+withargs` revision; `/usr/sbin/nrpe` belongs to it |
| SLES 12 SP3 `nrpe`, including 2.15 from official repositories | `nrpe-4.1.1-0.withargs1.x86_64.rpm` with `rpm --upgrade` below | `rpm -q nrpe` and `/usr/sbin/nrpe -V` identify server 4.1.1 |

Before upgrading, save the exact old package and checksum, configuration,
included files, TLS keys/certificates and service overrides using
[updates and rollback](updates-and-rollback.md#before-an-update). Record current
package/executable versions and a baseline remote check. Verify the new archive
and package identity before installation. Stop if the package manager reports
missing dependencies or a different target; never force the transaction.

After installing, inspect configuration-file prompts and `.rpmnew`/`.rpmsave`
files on SLES. Existing configuration can be retained intentionally; merge new
supported settings into that configuration instead of discarding site commands
or assuming the new defaults took effect. Reload changed service definitions,
restart the intended managed daemon and verify its executable, listener, logs
and actual remote check. Follow the distribution-specific commands below.
If installation or validation fails, use the saved package and configuration
with the [Debian rollback](updates-and-rollback.md#debian-rollback) or
[SLES rollback](updates-and-rollback.md#sles-12-sp3-rollback), and record the
failure rather than claiming a completed migration.

On SLES, installing only **`monitoring-plugins-nrpe` updates the client**, leaving
an old `nrpe` daemon untouched. This is what the supplied operator transcript
showed. Use the [SLES checklist](sles12sp3-deployment-checklist.md) to verify each
step; a newer client version is not evidence of a server upgrade.

## Debian 11, 12, 13, or 14

Check the destination release and architecture:

```sh
cat /etc/os-release
dpkg --print-architecture
```

The architecture must be `amd64`. Use the package from the matching Debian output
directory; a Debian 12 package is not a package for every Debian release.

From the directory with the verified `.deb` file:

```sh
sudo apt update
sudo apt install ./nagios-nrpe-server_*_amd64.deb
dpkg-query -W -f='${Package} ${Version} ${Architecture}\n' nagios-nrpe-server
dpkg-query -S /usr/sbin/nrpe
/usr/sbin/nrpe -V
```

APT resolves runtime dependencies through the destination's configured Debian
repositories. The explicit `./` selects the local custom package. Confirm that
the installed version contains `+withargs1` (or the custom revision of the build
you selected); the upstream version itself is discovered at build time.

Edit `/etc/nagios/nrpe.cfg` using your preferred editor. Review the
[configuration steps below](#configure-and-start-nrpe) before restarting.

```sh
sudo systemctl enable nagios-nrpe-server
sudo systemctl restart nagios-nrpe-server
sudo systemctl status nagios-nrpe-server --no-pager
```

If startup fails, inspect the service log:

```sh
sudo journalctl -u nagios-nrpe-server -n 100 --no-pager
```

## SLES 12 SP3

The custom server package upgrades the old NRPE daemon to **4.1.1** on genuine
SLES **12.3 x86_64**, retaining its native OpenSSL 1.0 ABI. This provides the
modern NRPE configuration/TLS implementation; it does not add TLS 1.3 to OpenSSL
1.0.2. A separate installation of the repository's NRPE 2.15 is unnecessary.

### Choose the server package

The archive contains different packages, not alternate filenames for one binary:

| File | Role | Installed executable |
| --- | --- | --- |
| `nrpe-4.1.1-0.withargs1.x86_64.rpm` | **Server: install on the monitored SLES host** | `/usr/sbin/nrpe` |
| `system-user-nagios-1.0.0-0.noarch.rpm` | Account-package dependency | Creates missing Nagios accounts/groups |
| `monitoring-plugins-nrpe-4.1.1-0.withargs1.x86_64.rpm` | Client: optional on a SLES monitoring host | `/usr/lib/nagios/plugins/check_nrpe` |

Installing `monitoring-plugins-nrpe` does not upgrade `/usr/sbin/nrpe`. If
`rpm -q nrpe` still reports `2.15`, the old server is still installed. Do not
proceed to the NRPE 4 TLS settings until the server version is correct.

From the directory containing all checksum-verified binaries, inspect identities:

```sh
cat /etc/os-release
uname -m
rpm -qp --queryformat '%{NAME} %{VERSION}-%{RELEASE} %{ARCH}\n' \
  ./nrpe-4.1.1-0.withargs1.x86_64.rpm \
  ./system-user-nagios-1.0.0-0.noarch.rpm
rpm -qpl ./nrpe-4.1.1-0.withargs1.x86_64.rpm
rpm -qp --requires ./nrpe-4.1.1-0.withargs1.x86_64.rpm
```

Expect server identity `nrpe 4.1.1-0.withargs1 x86_64` and payload entries for
`/usr/sbin/nrpe`, `/etc/nrpe.cfg`, `nrpe.service` and `tmpfiles.d/nrpe.conf`.
Use the build and repositories matching SLES 12 SP3. Keep the old package and
[root-only configuration/include/key backups](updates-and-rollback.md#before-an-update)
before changing an existing installation. Review `.rpmnew`/`.rpmsave` files;
a preserved old configuration header is not evidence of the executable version.

### Install the server and its real dependency

Check the package dependency and current account state:

```sh
rpm -q --whatprovides system-user-nagios
getent passwd nagios
getent group nagios
```

An existing `nagios` account does not satisfy an RPM requirement on the
`system-user-nagios` package. The companion is included in the archive but must
still be installed when no suitable provider exists. Its inspected script uses
`getent` before creating accounts/groups; record existing UID/GID values and
verify them after installation. Keep a suitable existing user package.

Resolve missing runtime libraries using your authorized matching SLES-12
repositories. A full server may already provide these packages:

```sh
sudo zypper refresh
sudo zypper install libwrap0 util-linux-systemd shadow netcfg grep sed coreutils
```

If the account package is missing, install **the companion and server** together:

```sh
sudo rpm --upgrade --verbose --hash \
  ./system-user-nagios-1.0.0-0.noarch.rpm \
  ./nrpe-4.1.1-0.withargs1.x86_64.rpm
```

If a suitable account package already exists, install only the server:

```sh
sudo rpm --upgrade --verbose --hash ./nrpe-4.1.1-0.withargs1.x86_64.rpm
```

These locally built RPMs are unsigned. Use the previously verified trusted
checksums/release authentication; retain normal RPM dependency and payload
checks. Do not use `--nodeps`, `--nosignature` or disable repository verification.
SLES 12's zypper does not provide `--allow-unsigned-rpm`.

Verify the actual server before configuring TLS:

```sh
rpm -q nrpe system-user-nagios
rpm -qf /usr/sbin/nrpe
/usr/sbin/nrpe -V
getent passwd nagios
getent group nagios
```

Expect custom server `4.1.1-0.withargs1` and NRPE executable version `4.1.1`.
`zypper install nrpe` without an explicit local artifact can select the old
repository version. Installing only the client leaves the old server unchanged.

### SLES certificate-authenticated TLS

Provision a CA, an RSA server certificate/key and a separate monitoring-client
certificate/key according to the [upstream NRPE documentation](https://github.com/NagiosEnterprises/nrpe).
Give the service user read access to its server key without making it public.
The client and server must trust the intended issuing CA and support the chosen
cipher. Keep the server's actual configuration/includes and plugin definitions.

Merge this **complete policy fragment** into `/etc/nrpe.cfg`, replacing the
example monitoring address and certificate paths. Update existing directives
rather than appending conflicting duplicates:

```nrpe
allowed_hosts=127.0.0.1,::1,192.0.2.10
dont_blame_nrpe=0
allow_bash_command_substitution=0
ssl_version=TLSv1.2
ssl_use_adh=1
ssl_cipher_list=DHE-RSA-AES256-GCM-SHA384:!aNULL:!eNULL
ssl_client_certs=2
ssl_cacert_file=/etc/nrpe-tls/monitoring-ca.pem
ssl_cert_file=/etc/nrpe-tls/server.pem
ssl_privatekey_file=/etc/nrpe-tls/server.key
```

On this NRPE 4.1.1/OpenSSL 1.0.2 combination, `ssl_use_adh=0` also skips
initialization of certificate-authenticated finite-field DH. The switch above
initializes it, while the explicit cipher list excludes anonymous/null ciphers.
Keep all certificate/key/CA and mandatory client-certificate settings: the three
protocol/DH/cipher lines alone are not a TLS deployment. This policy passed the
native container protocol tests, including rejection of missing client
certificates; it is not a completed production-host validation.

The build option `--ca-cert` only configures repository HTTPS during builds and
tests. It does not install these runtime NRPE credentials. Provisioning trust for
SLES repositories is also a separate task; verify CA sources/fingerprints rather
than bypassing HTTPS checks. Configure the firewall to permit the actual
monitoring host to reach TCP 5666.

### Start the intended managed daemon

The custom server supplies `nrpe.service` with `RuntimeDirectory=nrpe` and a
`/usr/lib/tmpfiles.d/nrpe.conf` rule for `/run/nrpe`, owned by `nagios:nagios`.
Manual creation of `/run/nrpe` is temporary because `/run` is cleared at boot.
Review old service overrides and configuration migration before restarting:

```sh
sudo systemctl daemon-reload
sudo systemctl enable nrpe.service
sudo systemctl restart nrpe.service
systemctl is-active nrpe.service
sudo systemctl status nrpe.service --no-pager
sudo systemctl cat nrpe.service
sudo systemctl show nrpe.service -p ExecStart -p User -p Group -p RuntimeDirectory
ls -ld /run/nrpe
sudo ss -ltnp 'sport = :5666'
sudo journalctl -u nrpe.service -n 50 --no-pager
```

`daemon-reload` rereads unit definitions; it does not restart other services.
The packaged unit uses `Type=simple` and `/usr/sbin/nrpe -c /etc/nrpe.cfg -f`.
An old drop-in can override it. Confirm that the intended process owns port 5666,
not a manually started test daemon, and resolve startup/configuration errors.
A running NRPE 2.15 reporting unknown `ssl_*` options has not been upgraded by
installing the check client. A successful service start alone does not prove TLS.

From the actual monitoring host, use its native `check_nrpe` with matching
credentials and a configured fixed command, for example:

```sh
check_nrpe -H nrpe.example.internal -d 0 -S TLSv1.2 \
  -L 'DHE-RSA-AES256-GCM-SHA384:!aNULL:!eNULL' \
  -A /etc/monitoring/tls/monitoring-ca.pem \
  -C /etc/monitoring/tls/client.pem \
  -K /etc/monitoring/tls/client.key \
  -c check_load_standard
```

Replace the hostname, paths and command. Install/configure the actual plugin;
see [fixed command examples and identity-verification limits](configuration-examples.md#hosts-tls-and-fixed-commands).
For a socket timeout, establish TCP reachability and inspect simultaneous server
logs before attributing the failure to a certificate or cipher. Repeat the check
after a controlled test-host reboot using the [SLES deployment worksheet](sles12sp3-deployment-checklist.md).

### Install the required monitoring plugins

The custom NRPE server executes configured plugins but does not include every
check. Install plugins separately on the monitored host using matching SLES-12
repositories. For the operator-confirmed Swap and NTP checks:

```sh
zypper search -s monitoring-plugins-swap monitoring-plugins-ntp
sudo zypper install monitoring-plugins-swap monitoring-plugins-ntp
rpm -ql monitoring-plugins-swap monitoring-plugins-ntp
```

Confirm that the executable paths match the existing `command[...]` definitions
and run each check as `nagios` before retrying remotely. Missing executables can
produce `NRPE: Unable to read output`. See the
[diagnosis, command definitions and remote examples](troubleshooting.md#nrpe-unable-to-read-output).
Restart NRPE after changing its configuration; installing a plugin at an already
configured path alone does not require a restart.

### Optional client on a SLES monitoring host

Install this only when that SLES host also needs the `check_nrpe` plugin:

```sh
sudo rpm --upgrade --verbose --hash ./monitoring-plugins-nrpe-4.1.1-0.withargs1.x86_64.rpm
rpm -q monitoring-plugins-nrpe
/usr/lib/nagios/plugins/check_nrpe -V
```

It shares the real user-package/native-library requirements. On another
monitoring distribution, use its native client package. Keep all three binaries
for verification of the archive's unchanged `SHA256SUMS`, even when installing
only the server and user package on the monitored host.


## Configure and start NRPE

| Distribution | Configuration | Service |
| --- | --- | --- |
| Debian | `/etc/nagios/nrpe.cfg` | `nagios-nrpe-server` |
| SLES 12 SP3 / OBS recipe | `/etc/nrpe.cfg` | `nrpe` |

Argument support is compiled in, but `dont_blame_nrpe=0` remains the packaged
default. Keep it at `0` if the monitoring server should not supply arguments.
To deliberately enable them, edit the existing settings in the appropriate
configuration file, for example:

```nrpe
allowed_hosts=127.0.0.1,::1,192.0.2.10
dont_blame_nrpe=1
```

Replace `192.0.2.10` with the actual monitoring server address. Define permitted
commands and validate any `$ARG1$`, `$ARG2$`, etc. they accept. Configure production
TLS authentication and allow incoming TCP 5666 (or your chosen `server_port`)
only from the intended monitoring servers. Keep Bash command substitution
disabled. See [deployment security](security.md) and [network requirements](network.md).

Restart the distribution's service after changing its configuration, using the
commands above. A successful service start does not prove argument handling or
remote connectivity; exercise the configured check from the real monitoring
server with the intended TLS settings and arguments. The project's container
tests do not validate the destination's systemd, firewall, or production TLS.

The build-time `--ca-cert` option configures repository HTTPS trust inside build
and test containers. Its CA is not embedded in the exported package and does not
provision the destination's NRPE certificates, keys, or operating-system trust.

Review future package-manager upgrades: a repository package can supersede a
local custom version. After upgrades, confirm the installed custom revision
again and rebuild from reviewed sources when security updates are needed.
