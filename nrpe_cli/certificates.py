"""Prepare an optional public CA certificate for Docker BuildKit secrets."""

from contextlib import contextmanager
import hashlib
from pathlib import Path
import ssl
import tempfile


@contextmanager
def prepared_certificate(value):
    """Validate PEM or DER and keep a normalized snapshot for this workflow."""
    if not value:
        yield None
        return
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise RuntimeError('CA certificate must be an existing file: ' + str(path))
    with path.open('rb') as source:
        data = source.read(1024 * 1024 + 1)
    if not data or len(data) > 1024 * 1024:
        raise RuntimeError('CA certificate must be nonempty and at most 1 MiB.')
    if b'PRIVATE KEY' in data:
        raise RuntimeError('Supply a public CA certificate, never a private key.')
    try:
        if b'-----BEGIN CERTIFICATE-----' in data:
            text = data.decode('ascii').strip()
            if (text.count('-----BEGIN CERTIFICATE-----') != 1
                    or not text.startswith('-----BEGIN CERTIFICATE-----')
                    or not text.endswith('-----END CERTIFICATE-----')):
                raise ValueError('Expected one public certificate')
            der = ssl.PEM_cert_to_DER_cert(text)
        else:
            der = data
        pem = ssl.DER_cert_to_PEM_cert(der)
        # DER_cert_to_PEM_cert only wraps bytes. OpenSSL must also parse them.
        ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT).load_verify_locations(cadata=pem)
    except (ValueError, UnicodeError, ssl.SSLError) as exc:
        raise RuntimeError('Invalid CA certificate. Supply one PEM or DER X.509 certificate (.cer/.crt/.pem).') from exc
    encoded = pem.encode('ascii')
    with tempfile.TemporaryDirectory(prefix='nrpe-ca-') as directory:
        snapshot = Path(directory) / 'company-ca.pem'
        snapshot.write_bytes(encoded)
        yield {'path': snapshot, 'sha256': hashlib.sha256(encoded).hexdigest()}
