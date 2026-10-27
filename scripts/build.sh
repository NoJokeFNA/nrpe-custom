#!/usr/bin/env bash
set -Eeuo pipefail

: "${DEBIAN_NUMBER:?Set DEBIAN_NUMBER via compose.yaml}"
: "${DEBIAN_CODENAME:?Set DEBIAN_CODENAME via compose.yaml}"

case "${DEBIAN_NUMBER}:${DEBIAN_CODENAME}" in
  11:bullseye|12:bookworm|13:trixie|14:forky) ;;
  *) echo "ERROR: Invalid Debian target: ${DEBIAN_NUMBER}:${DEBIAN_CODENAME}" >&2; exit 2 ;;
esac

actual_codename="$(. /etc/os-release; printf '%s' "$VERSION_CODENAME")"
if [[ "$actual_codename" != "$DEBIAN_CODENAME" ]]; then
  echo "ERROR: Expected ${DEBIAN_CODENAME}, running ${actual_codename}" >&2
  exit 2
fi

arch="$(dpkg --print-architecture)"
if [[ "$arch" != "amd64" ]]; then
  echo "ERROR: Package must be built on amd64, got ${arch}" >&2
  exit 2
fi

workdir="$(mktemp -d /tmp/nrpe-build.XXXXXXXX)"
trap 'rm -rf "$workdir"' EXIT
cd "$workdir"

printf '==> Fetching authenticated Debian sources for %s (%s)\n' "$DEBIAN_NUMBER" "$DEBIAN_CODENAME"
# apt-get source verifies archive metadata and source hashes using the configured
# Debian repositories. The source version tracks the selected suite.
apt-get update
apt-get source nagios-nrpe

shopt -s nullglob
changelogs=("$workdir"/nagios-nrpe-*/debian/changelog)
if (( ${#changelogs[@]} != 1 )); then
  echo 'ERROR: Expected exactly one extracted nagios-nrpe source tree' >&2
  exit 1
fi
src_dir="$(dirname "$(dirname "${changelogs[0]}")")"
cd "$src_dir"

original_version="$(dpkg-parsechangelog -S Version)"
if [[ "$original_version" == *+withargs* ]]; then
  echo 'ERROR: Already a custom source; refusing duplicate suffix' >&2
  exit 1
fi
custom_version="${original_version}+withargs1"

printf '==> Source version: %s\n' "$original_version"
printf '==> Target version: %s\n' "$custom_version"
python3 /opt/nrpe-build/enable_command_args.py debian/rules

# Record the custom Debian package revision in the package changelog; do not
# rename the .deb after it was built.
dch --newversion "$custom_version" \
  --distribution "$DEBIAN_CODENAME" \
  --force-distribution --no-auto-nmu \
  'Enable NRPE command arguments at build time (runtime remains disabled by default).'

if [[ "$(dpkg-parsechangelog -S Version)" != "$custom_version" ]]; then
  echo 'ERROR: Debian changelog version does not match target' >&2
  exit 1
fi

printf '==> Building corresponding Debian source package\n'
(cd "$workdir"; dpkg-source --build "$src_dir")
description="$workdir/nagios-nrpe_${custom_version#*:}.dsc"
python3 /opt/nrpe-build/export_debian_sources.py \
  "$description" "$workdir/source-export" "$custom_version"

printf '==> Building binary Debian packages\n'
export DEB_BUILD_OPTIONS="parallel=$(nproc)"
dpkg-buildpackage --build=binary --unsigned-source --unsigned-changes -rfakeroot

package="$workdir/nagios-nrpe-server_${custom_version}_amd64.deb"
/opt/nrpe-build/verify.sh "$package" "$src_dir/include/config.h" "$custom_version"

outdir="/output/debian${DEBIAN_NUMBER}"
mkdir -p "$outdir"
# Clear previous versions only after a successful build AND validation so a
# failed run does not erase a previously usable artifact.
find "$outdir" -maxdepth 1 -type f \
  \( -name 'nagios-nrpe-server_*_amd64.deb' -o -name 'nagios-nrpe_*_amd64.buildinfo' \) -delete
install -m 0644 "$package" "$outdir/$(basename "$package")"
rm -rf "$outdir/sources"
mv "$workdir/source-export" "$outdir/sources"
(
  cd "$outdir"
  sha256sum "$(basename "$package")" > SHA256SUMS
)

# Keep the Debian-generated build info for later inspection.
infofile="$workdir/nagios-nrpe_${custom_version}_amd64.buildinfo"
if [[ -f "$infofile" ]]; then
  install -m 0644 "$infofile" "$outdir/$(basename "$infofile")"
fi
printf '\nSUCCESS: %s\n' "$outdir/$(basename "$package")"
