#!/usr/bin/env bash
set -Eeuo pipefail

. /etc/os-release
[[ "$ID" == sles && "$VERSION_ID" == 15.4 && "$(uname -m)" == x86_64 ]] || {
  echo 'ERROR: Expected SLES 15 SP4 on x86_64' >&2; exit 1;
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
expected="$(python3 -c 'import json; m=json.load(open("/opt/nrpe-build/source.json")); print(m["version"]+"-"+m["custom_release"])')"
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

outdir=/output/sles15sp4
mkdir -p "$outdir"
# Replace old outputs only after the build and package checks passed.
find "$outdir" -maxdepth 1 -type f -name 'nrpe-*.rpm' -delete
install -m 0644 "$package" "$outdir/"
sources=("$workdir"/SRPMS/nrpe-*.src.rpm)
(( ${#sources[@]} == 1 ))
install -m 0644 "${sources[0]}" "$outdir/"
install -m 0644 /opt/nrpe-build/source.json "$outdir/source-manifest.json"
(
  cd "$outdir"
  sha256sum "${package##*/}" > SHA256SUMS
)
echo "PASS: nrpe $expected x86_64; command arguments enabled, Bash substitution disabled"
echo "SUCCESS: $outdir/${package##*/}"
