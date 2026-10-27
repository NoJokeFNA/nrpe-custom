#!/usr/bin/env python3
"""Host-only Python 3.9+ release validation and staging. Does not publish."""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nrpe_cli.release import assemble, prepare_target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['target', 'assemble'])
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--commit', required=True)
    parser.add_argument('--target')
    parser.add_argument('--incoming', type=Path)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    if args.mode == 'target':
        print(prepare_target(args.root, args.target, args.commit, args.destination))
    else:
        assemble(args.root, args.incoming, args.commit, args.destination)
        print('PASS: all five tested target archives, workflow source and notices staged')


if __name__ == '__main__':
    main()
