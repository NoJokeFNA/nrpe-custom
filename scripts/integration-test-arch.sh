#!/usr/bin/env bash
set -Eeuo pipefail
[[ "$(. /etc/os-release; echo "$ID")" == arch && "$(uname -m)" == x86_64 ]]
cd /packages
sha256sum --check SHA256SUMS
shopt -s nullglob
packages=(nrpe-*-x86_64.pkg.tar.zst)
(( ${#packages[@]} == 1 ))
package="${packages[0]}"
version="$(bsdtar -xOf "$package" .PKGINFO | sed -n 's/^pkgver = //p')"
[[ "$version" == "$(python -c 'import json; d=json.load(open("source-manifest.json")); print(d["version"]+"-"+d["pkgrel"])')" ]]
# These custom packages are unsigned local artifacts; repository signatures stay required.
pacman -U --noconfirm "$package"
[[ "$(pacman -Q nrpe)" == "nrpe $version" ]]
id nrpe
grep -qx 'allow_bash_command_substitution=0' /etc/nrpe/nrpe.cfg
# Confirm pacman preserves a deliberately modified configuration on reinstallation.
# This is not a host-version upgrade or a systemd boot test.
original="$(mktemp)"
cp /etc/nrpe/nrpe.cfg "$original"
sed -i 's/^dont_blame_nrpe=0$/dont_blame_nrpe=1/' /etc/nrpe/nrpe.cfg
printf '\n# ARCH_CONFIG_PRESERVATION_PROBE\n' >> /etc/nrpe/nrpe.cfg
pacman -U --noconfirm "$package"
grep -qx 'dont_blame_nrpe=1' /etc/nrpe/nrpe.cfg
grep -qx '# ARCH_CONFIG_PRESERVATION_PROBE' /etc/nrpe/nrpe.cfg
cp "$original" /etc/nrpe/nrpe.cfg
rm "$original"
echo 'PASS: Reinstallation preserves existing runtime policy; stock config restored for protocol tests'
systemd-analyze verify --man=no /usr/lib/systemd/system/nrpe.service
grep -qx 'User=nrpe' /usr/lib/systemd/system/nrpe.service
[[ "$(stat -c %a /etc/nrpe/nrpe.cfg)" == 644 ]]
[[ -s /usr/share/licenses/nrpe/ARGUMENT-POLICY.md ]]
export NRPE_TEST_USER=nrpe
exec /opt/nrpe-test/test-nrpe-protocol.sh /etc/nrpe/nrpe.cfg \
 /usr/lib/monitoring-plugins/check_nrpe /usr/bin/nrpe "$version" archlinux nrpe
