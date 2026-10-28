# Installing a custom NRPE package

Run these commands on the destination Linux server. Python, Docker, and this
checkout are needed on the build workstation, not on the destination server.
Use a package built for the destination's distribution release and architecture.
The current SLES target is **SLES 15 SP3 x86_64**, not every SLES 15 service pack.

For the complete NRPE server/client and Nagios setup, use the
[official NRPE documentation](https://github.com/NagiosEnterprises/nrpe) and
[Nagios Core documentation](https://assets.nagios.com/downloads/nagioscore/docs/nagioscore/4/en/).
This guide covers deployment of the custom packages and essential configuration
checks; it does not replace those manuals or distribution-specific plugin and
TLS instructions.

## Prepare the files

Build and test the selected target on the workstation with, for example,
`python3 nrpe.py verify debian12` or `python3 nrpe.py verify sles15sp3`.
Copy the following files into a dedicated directory on the destination server:

| Destination | Build output directory | Files to copy |
| --- | --- | --- |
| Debian 11 | `output/debian11/` | `nagios-nrpe-server_*_amd64.deb`, `SHA256SUMS` |
| Debian 12 | `output/debian12/` | `nagios-nrpe-server_*_amd64.deb`, `SHA256SUMS` |
| Debian 13 | `output/debian13/` | `nagios-nrpe-server_*_amd64.deb`, `SHA256SUMS` |
| Debian 14 | `output/debian14/` | `nagios-nrpe-server_*_amd64.deb`, `SHA256SUMS` |
| SLES 15 SP3 | `output/sles15sp3/` | `nrpe-*.x86_64.rpm`, `system-user-nagios-*.noarch.rpm`, `SHA256SUMS` |

Keep exactly one server package version in that directory so the wildcards below
select the intended package. Source RPMs, manifests, and Debian build information
are useful provenance but are not installed on the destination.

Change into the directory containing the copied files and verify them:

```sh
sha256sum --check SHA256SUMS
```

Continue only if every entry reports `OK`. Copy the checksum file through a
trusted channel alongside the packages; checksums detect changes but do not
authenticate the publisher by themselves. Keep both SLES binary RPMs available
for this check even if the destination already has the user package installed.
For releases that include `SHA256SUMS.sig`, first perform the
[release authentication check](release-signing.md#consumer-verification) using
an independently trusted maintainer key before extracting/installing packages.
The first published release has no signature.

If NRPE is already installed, back up its configuration before updating. Review
package-manager prompts about configuration files and dependencies. Preserve
the site's command definitions, allowed monitoring hosts, and TLS configuration.
Package installation may start or restart a service.

For an existing deployment, follow [updates and rollback](updates-and-rollback.md)
before replacing packages. The [configuration examples](configuration-examples.md)
and [maintenance policy](maintenance.md) describe optional checks and verification
boundaries.

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

## SLES 15 SP3

Check the destination release and architecture:

```sh
cat /etc/os-release
uname -m
```

Expect SLES `15.3` and `x86_64`. The current pinned build produces:

```text
nrpe-4.1.1-0.withargs1.x86_64.rpm
system-user-nagios-1.0.0-0.noarch.rpm
```

The destination needs matching, reachable SLES SP3 repositories or an approved
mirror to resolve runtime dependencies. The historical OBS SP3 NRPE repository
may no longer exist; see [SLES repository availability](sles15sp3.md#base-image-and-matching-dependencies).
Do not replace the SP3 dependency basis with SP7 or Leap packages.

From the directory with the verified RPMs, check whether the real Nagios user
package is already installed and refresh repository metadata:

```sh
rpm -q system-user-nagios
sudo zypper refresh
```

If a suitable `system-user-nagios` package is already installed, keep it and
install only the custom NRPE RPM:

```sh
sudo zypper install --allow-unsigned-rpm \
  ./nrpe-4.1.1-0.withargs1.x86_64.rpm
```

If the user package is missing, install the companion and server together:

```sh
sudo zypper install --allow-unsigned-rpm \
  ./system-user-nagios-1.0.0-0.noarch.rpm \
  ./nrpe-4.1.1-0.withargs1.x86_64.rpm
```

These custom RPMs are currently unsigned local artifacts, which is why these
commands explicitly allow unsigned RPMs. Use them only for the files whose
checksums you verified above. Keep repository signature verification enabled;
do not use a global `--no-gpg-checks` setting. Do not downgrade an existing user
package to the companion merely to match this example. Zypper resolves remaining
runtime dependencies; do not use `rpm --nodeps` to bypass missing dependencies.

Confirm the installed server and user:

```sh
rpm -q nrpe
getent passwd nagios
```

Expect `nrpe-4.1.1-0.withargs1.x86_64` for the current build.
`zypper install nrpe` without the local filename can select the repository
package instead of this custom build.

Edit `/etc/nrpe.cfg` using your preferred editor. Review the configuration below
before restarting:

```sh
sudo systemctl enable nrpe
sudo systemctl restart nrpe
sudo systemctl status nrpe --no-pager
```

If startup fails:

```sh
sudo journalctl -u nrpe -n 100 --no-pager
```

## Configure and start NRPE

| Distribution | Configuration | Service |
| --- | --- | --- |
| Debian | `/etc/nagios/nrpe.cfg` | `nagios-nrpe-server` |
| SLES 15 SP3 / OBS recipe | `/etc/nrpe.cfg` | `nrpe` |

Argument support is compiled in, but `dont_blame_nrpe=0` remains the packaged
default. Keep it at `0` if the monitoring server should not supply arguments.
To deliberately enable them, edit the existing settings in the appropriate
configuration file, for example:

```ini
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
