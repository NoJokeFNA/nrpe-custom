# Container recipes

| Recipe | Role |
| --- | --- |
| `debian/build.Dockerfile` | Shared builder for the four Debian suites |
| `debian/test.Dockerfile` | Fresh Debian runtime environment for package installation and TLS tests |
| `sles12sp3/build.Dockerfile` | Genuine SLES SP3 builder with pinned OBS sources |
| `sles12sp3/test.Dockerfile` | Separate SLES SP3 runtime test environment |

All four recipes use the **repository root as build context**. The paths in
`COPY` refer to that context, not to the Dockerfile's directory. Both Compose
files remain at the repository root, keeping relative output paths stable.
Use `python3 nrpe.py doctor`, `build`, `test`, or `verify` from there.

Keep builder and runtime roles separate: testing inside a builder can hide missing
runtime dependencies. The test recipes and `compose.test.yaml` are required by
the supported test/verify workflow. Moving files does not change package recipes
or replace Debian/SLES packaging with a shared package manager.

SLES 12 uses a separate Python input-download stage. Compilation and installation
remain native to genuine SLES 12 SP3; Python is not installed into that old target.
All downloaded RPMs undergo native SUSE signature/hash/identity checks before use.
