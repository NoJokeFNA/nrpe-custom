"""Actionable hints for TLS failures in streamed Docker/container output."""


class TLSFailure:
    """Remember failure categories without retaining potentially large logs."""

    def __init__(self):
        self.trust_failed = False
        self.tls_failed = False
        self.certificate_invalid = False

    def observe(self, line):
        text = line.lower().replace('_', ' ').replace('-', ' ')
        if any(marker in text for marker in (
                'certificate verify failed', 'certificate verification failed',
                'ssl certificate problem', 'ssl peer certificate',
                'self signed certificate', 'unable to get local issuer certificate',
                'unable to get issuer certificate',
                'unable to verify the first certificate', 'certificate is not trusted',
                'issuer is unknown', 'certificate signed by unknown authority',
                'curl error 60', 'curl: (60)')):
            self.trust_failed = True
        if any(marker in text for marker in (
                'tls handshake', 'ssl handshake', 'ssl connect error',
                'curl error 35', 'curl: (35)', 'ssl error', 'tls: bad certificate')):
            self.tls_failed = True
        if any(marker in text for marker in (
                'certificate has expired', 'certificate is expired',
                'certificate is not yet valid',
                'certificate is valid for', 'certificate subject name',
                'hostname mismatch')):
            self.certificate_invalid = True

    def hint(self, ca_configured):
        if self.trust_failed and not self.certificate_invalid:
            message = 'TLS certificate verification failed. '
            if ca_configured:
                message += (
                    'A CA certificate was supplied, but verification still failed. '
                    'Check that it is the correct issuing company CA and that the '
                    'server supplies its certificate chain. Check certificate validity '
                    'and the system clock as well.\n'
                )
            else:
                message += (
                    'No company CA certificate was supplied. If your network uses '
                    'a company CA or HTTPS inspection, retry with --ca-cert "path/to/Company-Root.cer" '
                    '(or set NRPE_CA_CERT). In the menu, select Company CA certificate '
                    'under Workflow options. Otherwise check the server certificate '
                    'chain, validity, hostname and system clock.\n'
                )
        elif self.tls_failed or self.certificate_invalid:
            message = (
                'A TLS/SSL connection failed. Check certificate validity, hostname, '
                'the system clock, and proxy/TLS settings. A missing company CA '
                'cannot be inferred from this error alone.\n'
            )
        else:
            return None
        return message + (
            'For image pulls or Dockerfile frontend downloads, configure CA trust '
            'in Docker Desktop/Engine and BuildKit; --ca-cert configures container '
            'trust only. Keep TLS verification enabled. '
            'See docs/network.md#optional-company-ca-certificate.'
        )
