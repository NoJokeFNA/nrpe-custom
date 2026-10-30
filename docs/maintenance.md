# Support and maintenance policy

This independent open-source workflow has best-effort maintenance, without an
SLA, guaranteed response times, enterprise support rights, or an extension of a
distribution's lifecycle. See the [warranty notice](../README.md#warranty-and-responsibility).

## Scope and verification

| Area | Project scope and verification |
| --- | --- |
| Debian 11–14, `amd64` | Matching build/runtime containers, source export, package validation and TLS tests; a successful run verifies its exact package bytes |
| SLES 12 SP3, `x86_64` | Genuine SP3 basis, pinned OBS sources, server/client, real user RPM and build-macros source; other SLES service packs are not covered |
| Linux host CLI | Standard-library CLI and optional menu; hosted unit-test CI |
| Windows host CLI | Hosted Python unit tests; Docker Desktop Linux-container operation and actual console behavior need separate practical verification |
| macOS / ARM hosts | Linux/amd64 emulation may work; outside the hosted host matrix and not verified by Linux/Windows results |
| Production deployment | Installation guidance and examples; operators configure plugins, monitoring, systemd, access, TLS and recovery |

Python 3.11 remains the application minimum. CI exercises that minimum and Python
3.14 on Linux/Windows, not every intermediate interpreter or terminal. The optional
audit tool is not an application dependency. The project workstation baseline
also covers the optional menu and website renderer.
Use an upstream-maintained interpreter for production; compatibility testing does
not provide security maintenance for an interpreter. Consult the
[Python version lifecycle](https://devguide.python.org/versions/).

Fast CI runs units, shell syntax and Compose checks. The separate [release
workflow](releases.md) runs the full package/install/protocol matrix on master
pushes and release-relevant PRs. Workflow configuration is not proof of a pass:
inspect the actual run for the commit being evaluated.

The [practical validation procedure](practical-validation.md) tracks the separate
Windows Docker Desktop and Debian/SLES VM checks for console, company CA paths,
systemd, reboot, plugins and update/rollback behavior.

Historical archives/repositories may become unavailable. Consult [Debian release
information](https://www.debian.org/releases/) and [SUSE lifecycle information](https://www.suse.com/lifecycle/)
for current upstream maintenance status. An archived target that still builds
does not necessarily receive dependency security fixes. Never silently substitute
another suite, SLES service pack, or Leap packages to preserve a passing result.

## Automated dependency monitoring

[Dependabot](../.github/dependabot.yml) checks Python requirements, locked website
npm dependencies and GitHub Actions version tags weekly and proposes update PRs into `develop`, without automatic
merging. Genuine Dependabot PRs may merge into develop after review under the
[Git policy](git-workflow.md).
Python proposals group the optional menu (`prompt-toolkit`, `wcwidth`), website
renderer (`Markdown`) and audit tooling (`pip-audit`) separately. Review each
component's minimum Python version, license and actual CI results before merging;
a dependency's newest release must fit the documented interpreter baseline.

Actions use official major-version tags such as `actions/setup-python@v7`, as
selected by the maintainer. Dependabot proposes major-version changes through PRs;
compatible updates within the selected upstream major tag are picked up directly.
The repository owner may need to enable Actions/Dependabot in GitHub settings;
checkout configuration does not override those settings.

The [dependency audit](../.github/workflows/dependency-audit.yml) runs weekly,
on relevant requirement changes, and manually. Pinned `pip-audit` checks menu
requirements and resolved dependencies against published advisories. Findings
and collection failures fail the job. It does not scan NRPE C code, DEB/RPM
contents, system libraries, container images or SLES repositories. A clean result
is not a security certification.

The separate [website check](../.github/workflows/website.yml) audits
`requirements-website.txt` and validates generated documentation and publication
guards. The renderer is isolated from the NRPE CLI/menu environment.

To reproduce the audit using Python 3.11+ in an isolated development environment:

```sh
python3 -m venv .venv-audit
.venv-audit/bin/python3 -m pip install -r requirements-audit.txt
.venv-audit/bin/python3 -m pip_audit --strict -r requirements-menu.txt
```

On Windows use `.venv-audit\Scripts\python.exe` for the environment-local commands.
Keep the audit tool separate from the optional menu environment.

## Human review cadence

At least monthly during active maintenance, and before a release:

1. Review relevant upstream NRPE announcements, fixes and advisories, Debian
   package changes, and SUSE security information for the deployed versions.
2. Review update PRs and audit findings. Assess affected deployments promptly
   rather than waiting for routine review; record mitigations and review dates.
3. Reassess target lifecycle/repository availability. Explicitly deprecate a
   target when continued validation is no longer feasible.
4. Rebuild affected targets and run fresh install/TLS tests after source,
   dependency or recipe changes. Unit/Compose checks alone are insufficient.

This is a maintainer procedure, not an installed reminder or a claim of continuous
security-feed monitoring on behalf of users.
The [2026-10-27 review](maintenance-reviews/2026-10-27.md) records actual upstream,
advisory, dependency and lifecycle findings, with outstanding actions and the next
review date. Record later reviews separately rather than overwriting that evidence.

## Reviewing source and recipe updates

Debian discovers its suite's official source version at build time. `--pull`
refreshes base images, not an existing exported package's source identity.
Preserve previous outputs, then explicitly rebuild and verify updates.

Do not automatically replace SLES revisions/hashes. Review authoritative source
and packaging changes, signatures and license terms, then update the manifests
and checksums together. Retain pure SP3 dependencies, runtime-disabled arguments
and disabled Bash substitution. Change the custom revision when modifying the
recipe for the same upstream version. Revisit [license evidence](sles-license-review.md)
when source versions or grants change.

For both formats, retain source/binary version identity, export corresponding
sources, and validate every affected target. Never rename a binary to manufacture
a version. Follow the [release plan](release-plan.md) before publication.

## Deprecation and reporting

Before removing a target, document the reason, last actually verified versions
and run date, planned removal boundary, and any separately verified replacement.
An untested suite/service pack is not a drop-in replacement.

For non-sensitive bugs, provide host OS/architecture, Python, Docker Engine,
Compose and Buildx versions, target, command/flags, expected behavior and a
redacted log excerpt. Include artifact/run identity where relevant. Do not attach
keys, company certificates, credentials, full environments or configuration
backups. Follow [security reporting guidance](security.md) for vulnerabilities.

Use [updates and rollback](updates-and-rollback.md) for deployments. Recovery on a
real server is distinct from rebuilding a package in a container.

For the evaluated upstream-clone alternative and future C changes, follow the
[source and patch strategy](source-strategy.md). A newer upstream tag alone does
not establish compatibility with a legacy target.

Review the [package compatibility matrix](package-compatibility.md) when native
recipes change. Record exact package versions and evidence dates; do not infer
argument support from the OS family alone.

The [30 October 2026 package review](package-reviews/2026-10-30.md) adds five
regular-package runtime probes and records current Arch/FreeBSD source findings.
These are separate from the project custom-package release matrix.
