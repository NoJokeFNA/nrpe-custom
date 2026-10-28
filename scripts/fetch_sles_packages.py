#!/usr/bin/env python3
"""Download hash-checked SUSE inputs; verify signatures natively before installation."""

import hashlib
import re
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
