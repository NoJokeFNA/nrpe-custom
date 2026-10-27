#!/usr/bin/env bash
set -Eeuo pipefail

workdir="$(mktemp -d /tmp/nrpe-user-build.XXXXXXXX)"
trap 'rm -rf "$workdir"' EXIT
mkdir -p "$workdir"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
python3 /opt/nrpe-build/sles_source.py /opt/nrpe-build/user-source.json "$workdir/SOURCES" \
  --originals /opt/nrpe-original-inputs/system-user-nagios
mv "$workdir/SOURCES/system-user-nagios.spec" "$workdir/SPECS/"
rpmbuild -ba --define "_topdir $workdir" \
  --define 'vendor nrpe-custom (based on OBS server:monitoring)' \
  "$workdir/SPECS/system-user-nagios.spec"
shopt -s nullglob
packages=("$workdir"/RPMS/noarch/system-user-nagios-*.noarch.rpm)
sources=("$workdir"/SRPMS/system-user-nagios-*.src.rpm)
(( ${#packages[@]} == 1 && ${#sources[@]} == 1 ))
[[ "$(rpm -qp --queryformat '%{NAME} %{VERSION}-%{RELEASE} %{ARCH}' "${packages[0]}")" == 'system-user-nagios 1.0.0-0 noarch' ]]
rpm --upgrade --verbose "${packages[0]}"
getent passwd nagios > /dev/null
getent group nagios > /dev/null
mkdir -p /opt/nrpe-user-package
install -m 0644 "${packages[0]}" "${sources[0]}" /opt/nrpe-user-package/
