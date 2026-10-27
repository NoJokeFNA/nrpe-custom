#!/usr/bin/env python3
"""Narrow, fail-closed Debian rules transformation for the NRPE package.

Changing the packaging rules (not upstream sources) is sufficient, because
Debian's override_dh_auto_configure forwards options to upstream configure.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re


def patch_rules(text: str) -> str:
    if "override_dh_auto_configure:" not in text:
        raise ValueError("No override_dh_auto_configure target; review Debian packaging")

    # Preserve each byte outside the single inserted line (including tabs).
    # Reject changes to Debian's rules structure rather than silently shipping
    # a package without the requested option.
    blocks = re.split(r"(?m)^override_dh_auto_configure:[ \t]*\n", text, maxsplit=1)
    if len(blocks) != 2:
        raise ValueError("No unique configure override found")

    header, remainder = blocks
    match = re.search(r"(?m)^[^\s#][^\n]*:\s*$", remainder)
    boundary = match.start() if match else len(remainder)
    configure_body = remainder[:boundary]
    tail = remainder[boundary:]

    if "--enable-bash-command-substitution" in configure_body:
        raise ValueError("Unexpected bash-command-substitution option; refusing unsafe build")
    if "--enable-command-args" in configure_body:
        raise ValueError("Arguments already enabled in Debian rules; review upstream change")

    ssl_line = re.compile(r"(?m)^([ \t]+)--enable-ssl[ \t]+\\[ \t]*$")
    hits = list(ssl_line.finditer(configure_body))
    if len(hits) != 1:
        raise ValueError(f"Expected exactly one --enable-ssl continuation line; found {len(hits)}")

    line = hits[0]
    indentation = line.group(1)
    newline = "\r\n" if "\r\n" in text else "\n"
    addition = f"{indentation}--enable-command-args \\{newline}"
    # Insert directly after the existing --enable-ssl line (including LF).
    end_of_line = configure_body.find("\n", line.end())
    if end_of_line == -1:
        raise ValueError("Missing line break after --enable-ssl")
    pos = end_of_line + 1
    configure_body = configure_body[:pos] + addition + configure_body[pos:]
    return header + "override_dh_auto_configure:" + newline + configure_body + tail


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rules", type=Path)
    args = parser.parse_args()
    rules = args.rules
    original = rules.read_text(encoding="utf-8")
    patched = patch_rules(original)
    rules.write_text(patched, encoding="utf-8")
    print(f"Inserted --enable-command-args into {rules}")


if __name__ == "__main__":
    main()
