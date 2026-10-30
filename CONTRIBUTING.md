# Contributing

Read [AGENTS.md](AGENTS.md) and the more specific instructions under `scripts/`
and `tests/`. Use the existing checkout and preserve unrelated local changes.
Write code, comments, documentation, and commits in English. Development is
independent of editors and operating systems; examples use `python3`.

## Development checks

Direct CLI commands need Python 3.11+ and no third-party Python packages. Install
`requirements-menu.txt` to work on terminal navigation and run its keyboard tests.
Builds and installation tests require Docker Engine, Linux containers, BuildKit,
and Compose 2.17+.

From the repository root:

```sh
python3 -m pip install -r requirements-menu.txt
python3 -m unittest discover -s tests -v
python3 nrpe.py doctor
```

For shell syntax checks in Bash, check each script explicitly:

```sh
for script in scripts/*.sh examples/*.sh; do bash -n "$script" || exit; done
```

Without menu dependencies, terminal-input tests are reported as skipped. Workflow
unit tests must remain independent of Docker and network access. Shell syntax
and unit tests alone do not establish that packages build or arguments work.

For a changed build or installation path, run the appropriate targets:

```sh
python3 nrpe.py verify debian12
python3 nrpe.py verify sles12sp3
```

Use `--rebuild` only when replacing existing artifacts intentionally. Validate all
affected targets when changing shared packaging behavior. Report exactly which
checks ran, passed, failed, or were skipped, with any platform limitations.
Native Windows terminal and process behavior need Windows verification; tests on
Linux do not establish that Windows has been exercised.

## Design boundaries

GitHub Actions runs the unit suite on Linux/Windows with Python 3.11 and 3.14,
plus Linux shell syntax and both Compose configuration checks. The separate
weekly dependency audit checks the optional menu requirements. Neither workflow
performs package/protocol integration tests. See the [maintenance policy](docs/maintenance.md)
and inspect actual workflow results for the commit under review.

Container recipes live under `docker/`; their build context remains the repository
root and Compose files remain at that root. Update Compose, `doctor`, and
documentation together when moving a recipe.

- Keep UI navigation in `nrpe_cli/menu.py`; use the existing controller for work.
- Preserve runtime-disabled argument defaults and disabled Bash substitution.
- Keep TLS, repository signatures, source checksums, and RPM verification enabled.
- Match the real target distribution; do not substitute Leap packages for SLES.
- Preserve separate builder/runtime images and meaningful protocol tests.
- Never install the build outputs on the development host during tests.
- Keep artifacts, ISO files, credentials, caches, and local reports out of Git.

Before removing or combining scripts, consult the
[script responsibility review](docs/architecture.md#script-responsibility-review).
Fewer files is not a goal if it couples independent package formats or removes
useful verification boundaries.

## Changes and pull requests

Start from `develop` on `feat/...`, `fix/...`, `refactor/...`, or `remove/...`.
Open a PR into `develop`; promote `develop` to `master` by PR. Never delete either
long-lived branch or work directly on it. Use the human commit author for authored
work; reviewed genuine Dependabot PRs are the sole bot exception. Do not add
co-author or generated-with/by attribution. See the [Git workflow](docs/git-workflow.md)
for route/author checks, guarded topic deletion and required administrator setup.

Keep changes focused and commit independently reviewable changes separately.
Use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/), for
example `feat(menu): add target navigation` or `docs: clarify firewall rules`.
Describe the problem, resulting behavior, and actual validation in pull requests.
Include relevant logs with private paths, addresses, and credentials removed.

Use GitHub issues for reproducible non-sensitive bugs and feature proposals.
For security-sensitive reports, follow [the security guidance](docs/security.md).
Independently authored project code and documentation use the [MIT license](LICENSE).
Retain all third-party notices; see the [license inventory](THIRD_PARTY.md).
Public binary release preparation follows the [release plan](docs/release-plan.md).
It does not authorize publication or grant new rights to third-party code.
