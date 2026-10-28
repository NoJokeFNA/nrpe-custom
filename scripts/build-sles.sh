#!/usr/bin/env bash
set -Eeuo pipefail

. /etc/os-release
[[ "$ID" == sles && "$VERSION_ID" == 12.3 && "$(uname -m)" == x86_64 ]] || {
  echo 'ERROR: Expected SLES 12 SP3 on x86_64' >&2; exit 1;
}
workdir="$(mktemp -d /tmp/nrpe-rpm-build.XXXXXXXX)"
trap 'rm -rf "$workdir"' EXIT
mkdir -p "$workdir"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
cp /opt/nrpe-sources/* "$workdir/SOURCES/"
mv "$workdir/SOURCES/nrpe.spec" "$workdir/SPECS/"
rpmbuild -ba --define "_topdir $workdir" \
  --define "_smp_mflags -j$(nproc)" \
  --define 'vendor nrpe-custom (based on OBS server:monitoring)' \
  "$workdir/SPECS/nrpe.spec"

shopt -s nullglob
packages=("$workdir"/RPMS/x86_64/nrpe-[0-9]*.x86_64.rpm)
(( ${#packages[@]} == 1 )) || {
  echo 'ERROR: Expected one nrpe server RPM' >&2; exit 1;
}
package="${packages[0]}"
expected="$(cat /opt/nrpe-build/expected-version)"
[[ "$(rpm -qp --queryformat '%{NAME} %{VERSION}-%{RELEASE} %{ARCH}' "$package")" == "nrpe $expected x86_64" ]]
configs=("$workdir"/BUILD/nrpe-*/include/config.h)
(( ${#configs[@]} == 1 ))
grep -Eq '^#define[[:space:]]+ENABLE_COMMAND_ARGUMENTS[[:space:]]+1([[:space:]]|$)' "${configs[0]}"
if grep -Eq '^#define[[:space:]]+ENABLE_BASH_COMMAND_SUBSTITUTION[[:space:]]+1([[:space:]]|$)' "${configs[0]}"; then
  echo 'ERROR: Bash command substitution was compiled in' >&2; exit 1
fi
contents="$(rpm -qpl "$package")"
grep -Fx /usr/sbin/nrpe <<< "$contents"
grep -Fx /etc/nrpe.cfg <<< "$contents"
mkdir "$workdir/extracted"
rpm2cpio "$package" > "$workdir/package.cpio"
(cd "$workdir/extracted"; cpio -id --quiet './etc/nrpe.cfg' < "$workdir/package.cpio")
grep -Eq '^dont_blame_nrpe=0[[:space:]]*$' "$workdir/extracted/etc/nrpe.cfg"

outdir=/output/sles12sp3
sources=("$workdir"/SRPMS/nrpe-*.src.rpm)
helpers=(/opt/nrpe-user-package/system-user-nagios-*.noarch.rpm)
helper_sources=(/opt/nrpe-user-package/system-user-nagios-*.src.rpm)
(( ${#sources[@]} == 1 && ${#helpers[@]} == 1 && ${#helper_sources[@]} == 1 ))
clients=("$workdir"/RPMS/x86_64/monitoring-plugins-nrpe-*.x86_64.rpm)
macro_sources=(/opt/nrpe-macros-package/nagios-rpm-macros-*.src.rpm)
(( ${#clients[@]} == 1 && ${#macro_sources[@]} == 1 ))
[[ "$(rpm -qp --queryformat '%{NAME} %{VERSION}-%{RELEASE} %{ARCH}' "${clients[0]}")" == "monitoring-plugins-nrpe $expected x86_64" ]]
for binary in "$package" "${clients[0]}"; do
  requirements="$(rpm -qp --requires "$binary")"
  grep -Fx 'libssl.so.1.0.0()(64bit)' <<< "$requirements"
  grep -Fx 'libcrypto.so.1.0.0()(64bit)' <<< "$requirements"
done
mkdir -p "$outdir"
# Replace old outputs only after the build and package checks passed.
find "$outdir" -maxdepth 1 -type f \( -name 'nrpe-*.rpm' -o -name 'system-user-nagios-*.rpm' -o -name 'monitoring-plugins-nrpe-*.rpm' -o -name 'nagios-rpm-macros-*.src.rpm' \) -delete
install -m 0644 "$package" "$outdir/"
install -m 0644 "${sources[0]}" "${helpers[0]}" "${helper_sources[0]}" "${clients[0]}" "${macro_sources[0]}" "$outdir/"
install -m 0644 /opt/nrpe-build/source.json "$outdir/source-manifest.json"
install -m 0644 /opt/nrpe-build/user-source.json "$outdir/user-source-manifest.json"
install -m 0644 /opt/nrpe-build/macros-source.json "$outdir/macros-source-manifest.json"
install -m 0644 /opt/nrpe-build/bootstrap.json "$outdir/bootstrap-manifest.json"
rm -rf "$outdir/obs-sources"
cp -a /opt/nrpe-original-inputs "$outdir/obs-sources"
(
  cd "$outdir"
  sha256sum "${package##*/}" "${helpers[0]##*/}" "${clients[0]##*/}" > SHA256SUMS
)
echo "PASS: nrpe $expected x86_64; command arguments enabled, Bash substitution disabled"
echo "SUCCESS: $outdir/${package##*/}"
