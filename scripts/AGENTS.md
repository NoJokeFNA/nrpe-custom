# Build script instructions

These instructions supplement the root `AGENTS.md` for this directory.

- Use Bash with strict error handling for build and verification scripts.
  Use Python standard-library helpers for packaging transformations and source
  downloads. SLES download/source helpers run in the modern input stage; no Python
  runtime is required in the SLES 12 target image.
- Validate the Debian version/codename pairing and `amd64` architecture before
  building. Work in a temporary source tree and clean it up on exit.
- Fetch authenticated distribution sources. Apply Debian changes to
  `debian/rules` and SLES changes to the pinned RPM spec, not upstream NRPE code.
- Keep the transformation narrow: preserve unrelated content and fail clearly
  when the expected packaging structure changes, the option is already present,
  or Bash command substitution would be enabled. Do not silently guess a patch.
- Set the custom package version through the Debian changelog before building.
- Validate the package name, exact version, architecture, NRPE executable, and
  generated configure macros before exporting artifacts. Keep previously valid
  outputs until the replacement build and verification succeed.
- Preserve the failing command's exit status. Do not hide errors behind logging
  pipelines or treat an existing artifact as evidence of a successful new build.
- Run shell syntax checks and the rules-transformer unit tests after relevant
  changes. Changes to source acquisition, dependencies, packaging, or export
  behavior also require builds for the affected Debian targets when Docker is
  available. Report any target that could not be exercised.
