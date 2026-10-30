# Optional Arch Linux argument-enabled NRPE

This unofficial package compiles remote command-argument support, departing from
the former official Arch package security policy. Arch deliberately disabled
this feature: https://security.archlinux.org/AVG-587 and
https://bugs.archlinux.org/task/66574 . It is not a distribution security fix.

Arguments remain disabled by default (dont_blame_nrpe=0). Enable them only after
reviewing your commands and validating their arguments. Prefer fixed commands.
Bash command substitution remains disabled at build time and runtime. Restrict
network access and allowed_hosts, and configure certificate-authenticated TLS.
TLS authenticates the connection; it does not make arbitrary shell input safe.

The historical CVEs and current source behavior require separate evaluation.
Functional and rejection tests do not constitute a complete security audit.
Test installation, upgrade, service startup and rollback on an isolated host.
Packages are unsigned local custom builds. Review the exported corresponding
sources and notices. Provided AS IS under the included terms.
