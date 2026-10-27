# Test instructions

These instructions supplement the root `AGENTS.md` for this directory.

- Use Python's standard-library `unittest` for the Debian rules transformer.
  Run from the repository root with
  `python3 -m unittest discover -s tests -v` once the implementation is present.
- Keep unit tests independent of network access, Docker, root permissions, and
  the host Debian release. Use fixtures and temporary directories as needed.
- Check observable behavior: insert the configure option exactly once in the
  correct target, preserve unrelated content and Makefile indentation, and
  reject missing or unsupported structures, repeated patching, and unsafe
  Bash command substitution options.
- Add regression coverage for behavior changes without duplicating implementation
  details or weakening assertions to make a failing transformation pass.
- Keep unit tests separate from package builds and installation/runtime checks.
  Those checks require the appropriate container or isolated Debian target and
  must never install custom NRPE packages on the development host.
- Do not claim argument handling works from a configure macro check alone.
  Runtime validation must exercise a client/server request and the intended
  runtime settings, including disabled argument handling by default.
- Confirm tests were discovered and completed; a zero-test run is not a pass.
  Report missing prerequisites and unrun integration checks explicitly.
