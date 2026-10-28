"""Bounded, contextual failure classification without executing log contents."""


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
                'curl error 35', 'curl: (35)', 'ssl error', 'tls: bad certificate',
                'peer did not return a certificate', 'alert certificate required')):
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
            'or input-download trust only. Keep TLS verification enabled. '
            'See docs/network.md#optional-company-ca-certificate.'
        )


class FailureDiagnostics:
    """Keep categories only; a log is evidence, never an instruction source."""

    def __init__(self):
        self.tls = TLSFailure()
        self.categories = set()

    def observe(self, line):
        self.tls.observe(line)
        text = line.lower().replace('_', ' ').replace('-', ' ')
        markers = {
            'proxy': ('proxy authentication required', '407 proxy', 'response 407', 'http code 407', 'proxyconnect tcp',
                      'could not resolve proxy', 'failed to connect to proxy', 'curl: (5)'),
            'dns': ('could not resolve host', 'temporary failure resolving',
                    'temporary failure in name resolution', 'name or service not known',
                    'no such host', 'curl: (6)'),
            'repository': ('does not have a release file', 'no release file',
                           'failed to download metadata for repo', 'repository not found',
                           'valid metadata not found', 'release file is expired'),
            'integrity': ('checksum mismatch', 'checksum is missing or incorrect',
                          'computed checksum did not match', 'computed checksums did not match',
                          'hash sum mismatch', 'badsig', 'no pubkey', ': nokey',
                          'signature verification failed', 'required suse signature',
                          'unreviewed or missing rpms', 'unexpected suse rpm identity'),
            'disk': ('no space left on device', 'not enough free disk space'),
            'refused': ('connection refused',),
            'bind': ('cannot assign requested address', 'cannot bind to any address'),
            'underflow': ('receive header underflow',),
            'nrpe_tls': ('could not complete ssl handshake',
                         'no shared cipher', 'wrong version number', 'alert protocol version'),
            'nrpe_config': ('unknown option specified in config file',
                            'unable to open config file', 'config file',),
        }
        for category, values in markers.items():
            if any(marker in text for marker in values):
                # A config filename or successful parse is not itself a failure.
                if category == 'nrpe_config' and not any(marker in text for marker in (
                        'unknown option', 'unable to open', 'contained errors')):
                    continue
                self.categories.add(category)
        if 'invalid option' in text and ("'f'" in text or '‘f’' in text):
            self.categories.add('foreground')

    def hint(self, ca_configured=False, context='build'):
        messages = []
        categories = self.categories
        if 'integrity' in categories:
            messages.append('Package/source integrity verification failed. Stop and compare the reviewed '
                            'source, hashes and signing-key identity. Do not disable signatures, accept '
                            'unchecked packages or replace pinned hashes just to make the build pass.')
        if 'proxy' in categories:
            messages.append('Proxy connection or authentication failed. Check the configured proxy and '
                            'its credentials separately for Docker Engine/BuildKit and build downloads. '
                            '--ca-cert cannot fix proxy authentication. Do not share credentials or a full environment dump.')
        if 'dns' in categories:
            messages.append('Name resolution failed. Check DNS, VPN/proxy settings and name resolution '
                            'inside the affected Docker engine/container as well as on the host.')
        if 'repository' in categories:
            messages.append('Repository metadata is unavailable or expired. Check the exact distribution, '
                            'suite/service pack, repository URL, access entitlement and system clock. '
                            'Keep signature and validity checks enabled; do not substitute another distribution.')
        if 'disk' in categories:
            messages.append('Storage is exhausted. Check free space on the host and Docker Desktop/Engine. '
                            'Preview expired local logs with python3 nrpe.py clean; it does not prune Docker '
                            'caches or remove current packages. See docs/local-cleanup.md.')
        nrpe = context == 'nrpe' or (context == 'test' and bool(categories & {
            'nrpe_tls', 'nrpe_config', 'underflow', 'bind', 'foreground'}))
        tls_problem = (self.tls.trust_failed or self.tls.tls_failed or self.tls.certificate_invalid
                       or 'nrpe_tls' in categories)
        if nrpe:
            if 'foreground' in categories:
                messages.append('The installed NRPE does not accept -f. NRPE 2.15 uses -d for daemon '
                                'mode; do not reuse a newer daemon startup command. Inspect its actual version and service unit.')
            if 'bind' in categories:
                messages.append('NRPE cannot bind the configured address. Check hostname and ip -4 addr show '
                                'on the intended server; server_address must be local to that host.')
            if 'nrpe_config' in categories:
                messages.append('NRPE configuration failed to load or contains unsupported directives. '
                                'Check the reported line, file/group read and directory traversal permissions, '
                                'and the options supported by the installed NRPE version. NRPE 2.15 does not '
                                'recognize disable_syslog=0 or modern ssl_* configuration.')
            if 'underflow' in categories:
                messages.append('NRPE closed the response early. Compare client/server TLS mode, packet '
                                'version (-2 for NRPE 2.x), allowed_hosts, TCP wrappers and simultaneous '
                                'server logs. Header underflow alone does not identify a certificate failure.')
            if tls_problem:
                messages.append('NRPE TLS negotiation failed. Compare both NRPE/OpenSSL versions, TLS '
                                'versions, shared authenticated ciphers and CA/server/client certificate '
                                'settings. NRPE 2.15 anonymous DH differs from modern certificate-based '
                                'TLS; the message alone does not prove a missing CA. Build-time --ca-cert '
                                'does not configure the deployed daemon. See docs/sles12sp3.md and '
                                'docs/sles12sp3-plaintext-diagnostic.md for an isolated temporary diagnostic; '
                                'keep production certificate verification enabled.')
        elif tls_problem:
            hint = self.tls.hint(ca_configured)
            messages.append(hint or 'TLS cipher/protocol negotiation failed. Check compatible TLS versions '
                            'and authenticated cipher suites on both ends; this does not establish a missing CA.')
        if 'refused' in categories and 'proxy' not in categories:
            messages.append('The connection was refused before TLS negotiation. Check the intended '
                            'host/port and listener (ss -ltnp on Linux), daemon startup logs and any '
                            'actively rejecting firewall rule. Do not infer a certificate problem.')
        return '\n\n'.join(messages) or None
