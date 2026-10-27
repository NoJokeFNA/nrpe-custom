#!/usr/bin/env python3
"""Compatibility entry point; prefer nrpe.py for new workflows."""

import argparse

from nrpe_cli.cli import main as controller_main
from nrpe_cli.state import TARGETS


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", choices=(*TARGETS, "all"))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--test", action="store_true", help="build and run integration tests")
    mode.add_argument("--test-only", action="store_true", help="test existing packages")
    parser.add_argument("--rebuild", action="store_true", help="allow replacing existing packages")
    parser.add_argument("--pull", action="store_true", help="check for updated base images")
    args = parser.parse_args(argv)
    action = "test" if args.test_only else "verify" if args.test else "build"
    print("Compatibility mode: prefer 'nrpe.py " + action + " " + args.target + "'.")
    options = (["--rebuild"] if args.rebuild and action != "test" else [])
    options += ["--pull"] if args.pull else []
    return controller_main([action, args.target, *options])


if __name__ == "__main__":
    raise SystemExit(main())
