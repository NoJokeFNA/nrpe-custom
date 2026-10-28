#!/usr/bin/env bash
# Build real native support packages from the pinned, pre-fetched OBS sources.
set -Eeuo pipefail
workdir="$(mktemp -d /tmp/nrpe-support-build.XXXXXXXX)"
trap 'rm -rf "$workdir"' EXIT
for support in nagios-rpm-macros system-user-nagios; do
  top="$workdir/$support"
  mkdir -p "$top"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
  cp /opt/nrpe-inputs/sources/"$support"/* "$top/SOURCES/"
  mv "$top/SOURCES/$support.spec" "$top/SPECS/"
  rpmbuild -ba --define "_topdir $top" \
    --define 'vendor nrpe-custom (based on OBS server:monitoring)' "$top/SPECS/$support.spec"
  shopt -s nullglob
  packages=("$top"/RPMS/noarch/"$support"-*.noarch.rpm)
  sources=("$top"/SRPMS/"$support"-*.src.rpm)
  (( ${#packages[@]} == 1 && ${#sources[@]} == 1 ))
  expected='system-user-nagios 1.0.0-0 noarch'
  [[ "$support" != nagios-rpm-macros ]] || expected='nagios-rpm-macros 0.14-0 noarch'
  [[ "$(rpm -qp --queryformat '%{NAME} %{VERSION}-%{RELEASE} %{ARCH}' "${packages[0]}")" == "$expected" ]]
  rpm --upgrade --verbose "${packages[0]}"
  out=/opt/nrpe-user-package
  [[ "$support" != nagios-rpm-macros ]] || out=/opt/nrpe-macros-package
  mkdir -p "$out"
  install -m 0644 "${packages[0]}" "${sources[0]}" "$out/"
done
getent passwd nagios > /dev/null
getent group nagios > /dev/null
