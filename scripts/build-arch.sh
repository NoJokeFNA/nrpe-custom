#!/usr/bin/env bash
set -Eeuo pipefail
[[ "$(. /etc/os-release; echo "$ID")" == arch && "$(uname -m)" == x86_64 ]]
work="$(mktemp -d /tmp/nrpe-arch.XXXXXXXX)"
trap 'rm -rf "$work"' EXIT
chmod 755 "$work"
python /opt/nrpe/scripts/arch_source.py /opt/nrpe "$work/build"
useradd -M -s /usr/bin/nologin nrpe-builder
chown -R nrpe-builder:nrpe-builder "$work/build"
cd "$work/build"
# makepkg must run as an unprivileged user. Dependencies were installed normally.
runuser -u nrpe-builder -- makepkg --noconfirm --cleanbuild
runuser -u nrpe-builder -- makepkg --allsource --noconfirm
shopt -s nullglob
packages=(nrpe-*-x86_64.pkg.tar.zst)
sources=(nrpe-*.src.tar.gz)
(( ${#packages[@]} == 1 && ${#sources[@]} == 1 ))
[[ "$(bsdtar -xOf "${packages[0]}" .PKGINFO | sed -n 's/^pkgname = //p')" == nrpe ]]
version="$(bsdtar -xOf "${packages[0]}" .PKGINFO | sed -n 's/^pkgver = //p')"
[[ "$version" == "$(python -c 'import json; d=json.load(open("source-manifest.json")); print(d["version"]+"-"+d["pkgrel"])')" ]]
stage="$(mktemp -d /output/.archlinux-stage.XXXXXXXX)"
chmod 755 "$stage"
mkdir -p "$stage/sources" "$stage/build-recipe"
cp "${packages[0]}" source-manifest.json ARGUMENT-POLICY.md "$stage/"
cp "${sources[0]}" "$stage/sources/"
cp PKGBUILD nrpe.service nrpe.sysusers nrpe.install ARGUMENT-POLICY.md "$stage/build-recipe/"
(cd "$stage"; find . -type f ! -name SHA256SUMS -printf '%P\n' | sort | xargs sha256sum > SHA256SUMS)
# Publish only after the full build/export succeeded; keep the old output on failure.
python - "$stage" /output/archlinux <<'PYCODE'
from pathlib import Path
import os, shutil, sys
stage, destination = map(Path, sys.argv[1:])
backup = stage.with_name(stage.name + '-previous')
if destination.exists():
    os.replace(destination, backup)
try:
    os.replace(stage, destination)
except BaseException:
    if backup.exists():
        os.replace(backup, destination)
    raise
if backup.exists():
    shutil.rmtree(backup)
PYCODE
printf 'PASS: optional Arch NRPE %s exported; arguments stay disabled by default\n' "$version"
