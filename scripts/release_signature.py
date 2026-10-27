#!/usr/bin/env python3
"""Sign or verify a complete release directory; never upload or install assets."""
import argparse
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nrpe_cli.signing import sign_release, verify_release


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('sign', 'verify'))
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--allowed-signers', type=Path, required=True,
                        help='Trusted signer file obtained independently of the release download')
    parser.add_argument('--key-env', help='Environment variable containing the unencrypted OpenSSH Ed25519 private key')
    args = parser.parse_args()
    try:
        if args.action == 'verify':
            if args.key_env:
                parser.error('--key-env is only valid for signing')
            verify_release(args.directory, args.allowed_signers)
        else:
            value = os.environ.get(args.key_env, '') if args.key_env else ''
            if not value:
                raise RuntimeError('Signing requires a nonempty private-key environment variable')
            value = value.rstrip('\r\n').replace('\r\n', '\n') + '\n'
            if (not value.startswith('-----BEGIN OPENSSH PRIVATE KEY-----\n')
                    or not value.endswith('-----END OPENSSH PRIVATE KEY-----\n')
                    or not value.isascii()):
                raise RuntimeError('Signing key must use ASCII OpenSSH private-key format')
            with tempfile.TemporaryDirectory(prefix='nrpe-release-signing-') as temporary:
                key = Path(temporary) / 'key'
                descriptor = os.open(key, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(descriptor, 'w', encoding='ascii', newline='\n') as stream:
                    stream.write(value)
                sign_release(args.directory, key, args.allowed_signers)
        print('PASS: authenticated release signature and complete asset checksums')
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
