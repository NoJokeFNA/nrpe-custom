#!/usr/bin/env python3
"""Fetch pinned OBS sources and narrowly adjust their RPM build recipe.

Sources are prepared in the download stage; the SLES 12 target needs no Python.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request


def patch_spec(text, version, release):
    versions = re.findall(r"(?m)^Version:[ \t]+(\S+)[ \t]*$", text)
    if versions != [version]:
        raise ValueError("Source version changed; review the pinned OBS recipe")
    blocks = re.split(r"(?m)^%build[ \t]*\n", text)
    if len(blocks) != 2:
        raise ValueError("Expected one RPM build section")
    header, body = blocks
    boundary = re.search(r"(?m)^%(?:install|check|files|changelog|clean|prep)\b", body)
    if not boundary:
        raise ValueError("Missing section after RPM build")
    build, tail = body[:boundary.start()], body[boundary.start():]
    args = r"(?m)^[ \t]+--enable-command-args[ \t]+\\[ \t]*\n"
    unsafe = r"(?m)^[ \t]+--enable-bash-command-substitution[ \t]+\\[ \t]*\n"
    if len(re.findall(args, build)) != 1 or len(re.findall(unsafe, build)) != 1:
        raise ValueError("Configure flags changed; review the OBS packaging")
    build = re.sub(unsafe, "", build)
    # Keep the source version and apply the custom revision through the spec.
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)*\.withargs[0-9]+", release):
        raise ValueError("Invalid custom RPM release")
    header, count = re.subn(r"(?m)^Release:[^\n]*$", "Release:        " + release, header)
    if count != 1:
        raise ValueError("Expected one RPM release field")
    result = header + "%build\n" + build + tail
    if "--enable-bash-command-substitution" in result:
        raise ValueError("Unexpected remaining Bash command substitution flag")
    return result


def fetch_sources(manifest, destination, opener=urllib.request.urlopen, originals=None):
    destination.mkdir(parents=True, exist_ok=True)
    base = "https://api.opensuse.org/public/source/{}/{}/".format(
        manifest["project"], manifest["package"])
    for name, expected in manifest["files"].items():
        if Path(name).name != name or name in (".", "..") or "\\" in name:
            raise ValueError("Unsafe OBS source filename")
        url = base + urllib.parse.quote(name) + "?" + urllib.parse.urlencode({
            "rev": manifest["revision"], "expand": "1"})
        with opener(url, timeout=60) as response:
            data = response.read(expected["size"] + 1)
        if len(data) != expected["size"] or hashlib.sha256(data).hexdigest() != expected["sha256"]:
            raise ValueError("OBS source checksum mismatch: " + name)
        (destination / name).write_bytes(data)
        if originals is not None:
            originals.mkdir(parents=True, exist_ok=True)
            (originals / name).write_bytes(data)
    if manifest["package"] == "nrpe":
        spec = destination / "nrpe.spec"
        spec.write_text(patch_spec(spec.read_text(encoding="utf-8"), manifest["version"],
                                   manifest["custom_release"]), encoding="utf-8")
    elif manifest["package"] in ("system-user-nagios", "nagios-rpm-macros"):
        text = (destination / (manifest['package'] + '.spec')).read_text(encoding="utf-8")
        if (re.findall(r"(?m)^Version:[ \t]+(\S+)[ \t]*$", text) != [manifest["version"]]
                or re.findall(r"(?m)^Release:[ \t]+(\S+)[ \t]*$", text) != [manifest["release"]]):
            raise ValueError("Unexpected support-package version or release")
    else:
        raise ValueError("Unsupported pinned source package")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--originals", type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    fetch_sources(manifest, args.destination, originals=args.originals)
    print("PASS: Pinned OBS source checksums and custom RPM recipe verified")


if __name__ == "__main__":
    main()
