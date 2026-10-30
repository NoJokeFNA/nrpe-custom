# Optional Arch Linux package

`archlinux` builds a native x86_64 package from the latest reviewed stable NRPE
release, currently **4.2.0**, with compiled command-argument support. It is an
explicit opt-in target and is **excluded from `all` and the five-target release
bundle**. It is not the former official Arch package or an AUR release.

## Security policy difference

Arch deliberately removed argument support from its former official package;
see [AVG-587](https://security.archlinux.org/AVG-587) and
[FS#66574](https://bugs.archlinux.org/task/66574). This custom package changes
that policy. A successful test or a warning does not make arbitrary shell input
safe, and enabling arguments is not a fix for the historical CVEs. Current
upstream fixes and the historical policy are evaluated separately in the
[test report](package-reviews/2026-10-30.md#current-arch-package-and-upstream-fixes).

The shipped configuration keeps `dont_blame_nrpe=0` and Bash substitution disabled.
The CLI, package installation output and installed policy notice identify this
difference. Prefer fixed commands when remote arguments are unnecessary. Require
reviewed commands, argument validation, restricted network access and appropriate
TLS before enabling arguments; follow [deployment security](security.md).

**Upgrades preserve locally modified configurations.** An old configuration may
already contain `dont_blame_nrpe=1`, even if its previous binary rejected all
arguments. Review that setting before starting the new daemon. Do not assume the
new package's safe default overwrites an existing configuration.

## Build and test

On the workstation:

```sh
python3 nrpe.py verify archlinux --pull
```

For an intentional replacement of existing local outputs, add `--rebuild`.
The optional `--ca-cert` works as for other targets and preserves HTTPS and
repository-signature checks. Company CAs can remain in local builder/test image
layers; do not distribute those images without the appropriate approval.

The builder uses the official Arch base-devel image, fully refreshes its matching
rolling repositories, and runs `makepkg` as an unprivileged account. It compares
the latest stable upstream release with [the reviewed manifest](../packaging/archlinux-source.json).
A new upstream release fails for source, license and native-package review; it
does not silently keep using a stale version or publish unreviewed sources.
No packages are installed on the workstation host.

The custom package version is recorded in PKGBUILD as `4.2.0-1.1`; it is not
created by renaming a binary. A later recipe change for the same upstream version
must increment the custom package revision. The source archive checksum, license
hashes and recipe are exported and checked before release staging.

## Outputs and archive preparation

`output/archlinux/` contains:

- `nrpe-4.2.0-1.1-x86_64.pkg.tar.zst`: daemon and matching client.
- `sources/nrpe-4.2.0-1.1.src.tar.gz`: complete native source package, including
  the exact upstream archive and all packaging inputs.
- `build-recipe/`, `source-manifest.json`, `ARGUMENT-POLICY.md` and `SHA256SUMS`.

After committing the reviewed workflow and running `verify` from that exact clean
checkout, prepare a source-complete archive on a Linux staging workstation with
GNU tar and zstd:

```sh
python3 scripts/prepare_release.py target --target archlinux \
  --commit "$(git rev-parse HEAD)" --destination .nrpe/arch-release
```

Staging requires a complete successful verify run bound to that commit and the
unchanged binary/source bytes. It validates the native package metadata, exact
recipe, installation notice, upstream archive and license texts. Dirty/stale
results cannot be used to stage a release.

The separate **Optional Arch Linux package** CI workflow runs on relevant PRs
and can be dispatched manually. It uploads a source-complete archive as a build
artifact; it has no release publishing permissions and does not automatically
create GitHub Releases. Public release publication remains an explicit maintainer action through the
existing **Build and release packages** workflow: select `develop` or `master`
and set **optional_arch_release** to true. The default is false; PRs and master
pushes never invoke the optional Arch publisher. It rebuilds/verifies Arch,
stages exact source-complete assets and publishes a separate prerelease using
GitHub's workflow token. The regular five-target release is unaffected. The native package is unsigned; checksums alone do not authenticate a
publisher. A signed archive manifest does not create a pacman package signature.

## Install or replace an existing package

Use a fully updated, isolated **Arch Linux x86_64** host first. Arch is rolling;
this is not a package for an older frozen snapshot or an Arch derivative. Check
the installed version, source and local patches before replacing a newer or
separately maintained package. Never force conflicts with `--overwrite` or bypass
dependencies/signatures. Follow the official
[Arch system maintenance guidance](https://wiki.archlinux.org/title/System_maintenance)
and [NRPE documentation](https://github.com/NagiosEnterprises/nrpe) for the complete
system, plugin and TLS setup.

For an existing installation, record its state and keep the previous package
archive, configuration, unit overrides and plugins for rollback:

```sh
pacman -Q nrpe
pacman -Ql nrpe
sudo systemctl cat nrpe.service
sudo cp -a /etc/nrpe /root/nrpe-config-before-custom
sudo systemctl stop nrpe.service
```

If the old deployment used `nrpe.socket`, disable and stop that socket before
switching to this standalone daemon. This package does not ship socket activation.
Perform the normal full Arch upgrade in a maintenance window before installing
a package built against the current rolling libraries; avoid partial upgrades.

Transfer the output into a dedicated directory and retain the complete file set
if using its full checksum manifest. Check it before installation:

```sh
sha256sum --check SHA256SUMS
sudo pacman -Syu
sudo pacman -U ./nrpe-4.2.0-1.1-x86_64.pkg.tar.zst
```

The package name stays **`nrpe`**, so pacman upgrades the installed package rather
than creating a second daemon. Its backup entry preserves a modified
`/etc/nrpe/nrpe.cfg`; inspect any `.pacnew` file and deliberately merge required
settings. Recheck `dont_blame_nrpe` before restarting. Package installation does
not enable or restart the daemon automatically. `monitoring-plugins` or individual
custom plugins are separate prerequisites; this package supplies NRPE only.

```sh
pacman -Q nrpe
/usr/bin/nrpe -V
sudo grep -nE '^(dont_blame_nrpe|allow_bash_command_substitution)=' /etc/nrpe/nrpe.cfg
sudo systemctl daemon-reload
sudo systemctl enable --now nrpe.service
sudo systemctl status nrpe.service --no-pager
```

The native paths match the AUR convention: daemon `/usr/bin/nrpe`, client
`/usr/lib/monitoring-plugins/check_nrpe`, configuration `/etc/nrpe/nrpe.cfg`,
service `nrpe.service`, account `nrpe`, runtime directory `/run/nrpe`.
The policy notice is installed under
`/usr/share/licenses/nrpe/ARGUMENT-POLICY.md` and license/OpenSSL notices are
preserved beside it. Verify real monitoring requests using the intended TLS
policy; see [Verify TLS & identity](tls-validation.md).

For rollback, stop the daemon, reinstall the saved previous native package with
pacman, restore its configuration and unit overrides, reload systemd definitions
and restart the previous deployment. Do not overwrite unrelated files or enable
an old socket and standalone listener on the same port. Test that procedure on
the isolated host before relying on it in production.

## Validation scope

A genuine Arch container build and fresh pacman installation passed locally on
30 October 2026. Checks cover package/version identity, real sysusers account
creation, unit-file verification, safe packaged defaults, configuration preservation
on same-version reinstallation, both argument settings,
two argument pairs over certificate-authenticated TLS, Bash-substitution and
metacharacter rejection, unrelated CA rejection and missing client-certificate
rejection. Corresponding source and license identities were also validated.

Containers do not boot systemd. Real service startup, existing-config upgrades,
reboot, rollback, firewall and production Nagios/plugin behavior remain separate
[host validation](practical-validation.md) tasks. These tests are not a complete
security audit. The build is repeatable, not bit-for-bit reproducible: live Arch
repository transactions and base images can change.
