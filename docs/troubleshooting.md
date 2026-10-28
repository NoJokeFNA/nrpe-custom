# Build and NRPE diagnostics

Failed workflow commands retain their original exit status and raw output in
the local run log. Recognized failures add contextual hints. Successful commands
do not emit failure hints, including when a retry recovered from an earlier
error. Hints classify observed messages; they do not establish a root cause.

## Inspect an existing log

```sh
python3 nrpe.py diagnose ./build.log
python3 nrpe.py diagnose ./build.log --ca-configured
python3 nrpe.py diagnose ./redacted-nrpe.log --context nrpe
```

`diagnose` reads a local text file without Docker or a connection to the server.
It executes no log content, prints category hints rather than raw lines, and
does not mark any workflow as passed. Exit 0 means the file was read successfully,
not that the recorded build/check succeeded. No recognized failure is not a pass.
Use `--ca-configured` only when the recorded build was actually given a CA.

The default context is build/download failures. Use `--context nrpe` for daemon
or `check_nrpe` logs: build-time CA configuration and deployed client/server TLS
are separate. On servers without Python, review/redact the log and copy it to
the workstation running this tool. Never share credentials, private keys or full
environment dumps. Keep raw local logs outside Git.

## Interpret the categories

| Observed error | What to check |
| --- | --- |
| Issuer unknown / certificate verification failed | Build: issuing CA and chain, certificate dates/name and clock. If company HTTPS inspection is used, pass its reviewed CA with `--ca-cert` or `NRPE_CA_CERT`. A supplied CA does not guarantee it is the right issuer. |
| Expired certificate / hostname mismatch | Correct the certificate, endpoint or clock; adding an unrelated CA cannot fix these. |
| Image/frontend pull trust failure | Configure trust in Docker Desktop/Engine and BuildKit. The build's `--ca-cert` does not configure engine trust. |
| Proxy authentication / HTTP 407 | Proxy reachability and credentials for the affected component. A CA cannot fix proxy authentication. |
| DNS resolution failure | Name resolution on the host and inside the affected Docker component, including VPN/proxy configuration. |
| Missing or expired repository metadata | Actual suite/service pack, repository URL, access rights and clock. Do not disable signatures/validity or substitute another distribution. |
| Checksum, signature or pinned-input mismatch | Stop and investigate the reviewed source/key/hash. Do not replace hashes or bypass signatures to obtain a pass. |
| No space left | Host and Docker storage separately. Preview [local cleanup](local-cleanup.md); it does not prune BuildKit caches or delete current packages. |
| Connection refused | Intended address/port, listener, daemon startup logs and any firewall REJECT. The connection failed before TLS negotiation. |

## NRPE on a deployed SLES 12 SP3 host

For `Could not complete SSL handshake. 1`, compare both NRPE and OpenSSL versions,
TLS versions, shared authenticated ciphers and CA/server/client certificate
settings. The message alone does not prove that a CA is missing. NRPE 2.15's
legacy anonymous DH and NRPE 4.x certificate authentication are different modes.

`Receive header underflow` can also result from mismatched TLS modes/packet
versions or access rejection. Check `-2` for NRPE 2.x, `allowed_hosts`, TCP wrappers
and simultaneous server logs before attributing it to certificates.

The [anonymized SLES 12 SP3 diagnostic](sles12sp3-plaintext-diagnostic.md) records
the separate plaintext test, unsupported `-f` option, configuration permissions,
wrong-host bind error and cleanup. Plaintext is temporary test evidence, not a
production fix. Use the [authenticated TLS configuration](configuration-examples.md#hosts-tls-and-fixed-commands)
for the custom NRPE 4.1.1 build. Do not apply modern `ssl_*` directives or
`disable_syslog=0` to an NRPE 2.15 configuration.

Inspect the real service definition and process command before changing startup
options. A manually started daemon is not managed by systemd; a failed second
service start can simply mean its port/PID is already occupied. Do not launch
another instance or remove live locks to hide that condition.
