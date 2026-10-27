# Deferred licensing and release plan

Status: deferred at the maintainer's request. Implement documentation, terminal
navigation, and script maintenance first. This document does not authorize
publishing releases or establish that release assets satisfy their licenses.

Before publishing binary GitHub releases:

1. Inspect the actual upstream and distribution license files for every shipped
   component, including NRPE's OpenSSL linking terms and packaging notices.
   Current SLES package metadata reports GPL-2.0-or-later for NRPE and MIT for
   system-user-nagios; verify the underlying texts, not metadata alone.
2. Choose a license for independently authored controller code, scripts, and
   documentation. MIT was proposed; it has not been adopted. Preserve existing
   third-party licenses and copyright notices.
3. Add LICENSE and a third-party provenance/license inventory after that review.
4. Export complete corresponding Debian sources alongside binaries, including
   original source, distribution changes, our changes, and necessary build
   scripts. The current Debian build exports only the server binary and available
   build information. A generic upstream URL or GitHub-generated source archive
   alone does not contain the corresponding Debian source package.
5. Check that exported SLES source RPMs, helper source RPMs, build scripts, and
   notices cover the distributed binaries. Do not republish SLES installation
   media or dependency images under an assumed blanket permission.
6. Define release assets: matching binaries and sources, license notices,
   checksums for every asset, build provenance, and artifact-bound test results.
   Add automated checks that reject incomplete or untested release bundles.
7. Identify packages as unofficial custom builds. Do not imply endorsement,
   certification, support entitlement, or trademark permission from Debian,
   SUSE, or Nagios.
8. Prepare a reviewable release separately; publish only when explicitly requested.

References:

- [Debian Free Software Guidelines](https://www.debian.org/social_contract.en.html#guidelines)
- [GNU GPL version 2](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html)
- [SUSE BCI documentation and redistribution overview](https://opensource.suse.com/bci-docs/)

This is a technical checklist, not legal advice or a completed license audit.
