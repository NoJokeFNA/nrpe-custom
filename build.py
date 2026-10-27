#!/usr/bin/env python3
"""Compatibility entry point; prefer nrpe.py for new workflows."""

import argparse

from nrpe_cli.cli import main as controller_main


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", choices=("debian12", "debian13", "debian14", "all"))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--test", action="store_true", help="build and run integration tests")
    mode.add_argument("--test-only", action="store_true", help="test existing packages")
    args = parser.parse_args(argv)
    action = "test" if args.test_only else "verify" if args.test else "build"
    print("Compatibility mode: prefer 'nrpe.py " + action + " " + args.target + "'.")
    return controller_main([action, args.target])


if __name__ == "__main__":
    raise SystemExit(main())
