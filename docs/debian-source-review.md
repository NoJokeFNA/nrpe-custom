# Debian NRPE 4.2.0-1 source review

Reviewed on 2026-10-29 after Debian 14 source discovery selected `4.2.0-1`
and publication correctly stopped at the unreviewed-source gate.

## Authoritative inputs

The [official Debian source pool](https://deb.debian.org/debian/pool/main/n/nagios-nrpe/)
supplies `nagios-nrpe_4.2.0-1.dsc`, its upstream archive and Debian packaging.
Both archive sizes and SHA-256 digests were checked against the DSC:

| Input | SHA-256 |
| --- | --- |
| `nagios-nrpe_4.2.0.orig.tar.gz` | `f89455bdb5c4057d3bbebbde8a1d9f775d2598eb04d2d876eea9e718716e1a37` |
| `nagios-nrpe_4.2.0-1.debian.tar.xz` | `124df4d50457350c858f7f8e7951559ac8eff396db5d9beefc43e24a60a5e315` |

The comparison baseline was Debian's `4.1.3-1` source reconstructed with
`dpkg-source --extract`; its six recorded license-evidence hashes matched the
existing review. These downloads used HTTPS. This comparison does not claim an
independent verification of the uploader's DSC signature. Build-time APT archive
authentication and source checksum checks remain required.

## License comparison

- `LICENSE.md` and `LEGAL` are byte-identical to the reviewed 4.1.3 source.
- `debian/copyright` only removes obsolete FSF postal-address paragraphs. The
  GPL-2-or-later grant, OpenSSL linking exception, ACL attribution, `snprintf`
  permission notice and Debian packaging license remain unchanged.
- Changed C/header files retain their existing copyright and license notices.
  In particular, `src/acl.c` and `include/acl.h` still explicitly grant GPLv2
  or later. `src/snprintf.c` retains Patrick Powell's attribution requirement.
- `src/utils.c:display_license()` is byte-identical and explicitly permits
  compiling, linking and using OpenSSL. Changes elsewhere in that file do not
  change this grant.
- Upstream code, packaging and tests changed; this review records license
  evidence and does not substitute for build, installation or TLS testing.

The exact upstream archive and six extracted evidence-file hashes are recorded
in [the publication allowlist](../packaging/debian-license-review.json).
Publication still rejects unknown versions, changed upstream bytes or changed
evidence. Full corresponding sources, GPL text and notices remain release
assets. No source-version pin or bypass of the release gate was added.
