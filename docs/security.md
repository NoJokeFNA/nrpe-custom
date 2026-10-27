# Deployment security and reporting

Compiling command argument support does not make arbitrary arguments safe.
Packages keep `dont_blame_nrpe=0`. Enable it only for a reviewed deployment with
restricted commands, validated arguments, trusted clients, and appropriate TLS.
Do not expose NRPE to the public Internet or enable Bash command substitution.

Use the distribution-specific configuration and service paths documented in the
[README](../README.md#using-a-built-package). Restrict both `allowed_hosts` and
network access to the intended monitoring servers. The allowlist does not replace
TLS client authentication or argument validation. Avoid passing untrusted strings
into shell commands, even if the request arrived from an allowed host.

Integration tests use disposable configurations and a short-lived local
certificate. They do not provision production credentials, test real firewall
rules, validate systemd startup, or establish that every command definition is
safe. Follow the [network guide](network.md) for connection direction and ports.
Custom RPMs are currently unsigned local artifacts; SHA-256 checksums detect
changes but do not by themselves authenticate a publisher.

For a suspected vulnerability, check whether the repository's Security tab offers
private vulnerability reporting. If available, use it. If unavailable, ask the
maintainer to establish a private reporting channel without disclosing exploit
steps or sensitive data in a public issue. No private reporting service or
response-time guarantee is currently claimed by this project.

For upstream NRPE or distribution vulnerabilities, also follow the relevant
upstream/distribution reporting process. Do not publish credentials, internal
addresses, production configurations, or unredacted local run logs.
