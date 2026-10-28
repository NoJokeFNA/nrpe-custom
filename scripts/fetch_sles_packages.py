#!/usr/bin/env python3
"""Fetch pinned original SUSE RPMs and require their known SUSE signatures."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.request
import urllib.parse


def download_packages(manifest, destination, role):
    """Download hash-checked RPMs; signature verification must precede installation."""
    destination.mkdir(parents=True, exist_ok=True)
    seen = set()
    for package in manifest["packages"]:
        if role not in package["roles"]:
            continue
        name = package["file"]
        if (not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._+~-]*\.rpm', name)
                or name in seen):
            raise ValueError("Invalid SUSE RPM filename")
        seen.add(name)
        url = urllib.parse.urlsplit(package["url"])
        if url.scheme != "https" or url.hostname != "api.opensuse.org" or url.username or url.password:
            raise ValueError("Expected an authenticated HTTPS source from the public OBS API")
        with urllib.request.urlopen(package["url"], timeout=60) as response:
            data = response.read(package["size"] + 1)
        if len(data) != package["size"] or hashlib.sha256(data).hexdigest() != package["sha256"]:
            raise ValueError("Original SUSE RPM checksum mismatch: " + name)
        path = destination / name
        path.write_bytes(data)
        yield package, path


def fetch_packages(manifest, destination, role):
    for package, path in download_packages(manifest, destination, role):
        name = package['file']
        try:
            environment = dict(os.environ, LC_ALL="C")
            signature = subprocess.check_output(
                ["rpmkeys", "--checksig", "--verbose", str(path)], stderr=subprocess.STDOUT,
                env=environment,
            ).decode("utf-8", errors="replace")
            pattern = r"Signature, key ID " + re.escape(package["signature_key"]) + r": OK"
            if not re.search(pattern, signature, re.I):
                raise ValueError("Required SUSE signature missing from " + name)
            identity = subprocess.check_output([
                "rpm", "-qp", "--queryformat", "%{NAME} %{VERSION}-%{RELEASE} %{ARCH}|%{VENDOR}", str(path)
            ], env=environment).decode("utf-8")
            expected = "{} {} {}|{}".format(package["name"], package["version_release"],
                                            package["arch"], package["vendor"])
            if identity != expected:
                raise ValueError("Unexpected SUSE package identity: " + name)
        except Exception:
            path.unlink()
            raise
        print("PASS: Verified original SUSE signature, checksum, and identity: " + name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("role", choices=("build", "runtime"))
    args = parser.parse_args()
    fetch_packages(json.loads(args.manifest.read_text(encoding="utf-8")), args.destination, args.role)


if __name__ == "__main__":
    main()
