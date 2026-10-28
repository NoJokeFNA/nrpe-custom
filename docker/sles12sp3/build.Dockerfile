# syntax=docker/dockerfile:1
ARG SLES_BASE_IMAGE=registry.suse.com/suse/sles12sp3@sha256:0995dbf051274a3a5baf19c7f94ce7ebe69d7aa91f7b3b22248bd06d7122e53a
# This stage downloads and hash-checks inputs; it never compiles target binaries.
FROM python:3.13-slim AS inputs
ARG NRPE_CA_SHA256=none
COPY scripts/prepare_sles_inputs.py scripts/fetch_sles_packages.py scripts/sles_source.py /tools/
COPY packaging/sles12sp3-*.json packaging/sles12sp3-suse.asc /packaging/
RUN --mount=type=secret,id=nrpe_ca_cert \
    python3 /tools/prepare_sles_inputs.py /packaging /inputs build \
      --ca /run/secrets/nrpe_ca_cert --ca-sha256 "$NRPE_CA_SHA256"

FROM ${SLES_BASE_IMAGE}
COPY --from=inputs /inputs /opt/nrpe-inputs
COPY scripts/verify-sles-packages.sh scripts/verify-sles-environment.sh \
     scripts/build-sles-user.sh /opt/nrpe-build/
RUN set -eu; \
    bash /opt/nrpe-build/verify-sles-environment.sh; \
    rpm --import /opt/nrpe-inputs/suse.asc; \
    bash /opt/nrpe-build/verify-sles-packages.sh /opt/nrpe-inputs/packages; \
    zypper --non-interactive --no-refresh install --no-recommends /opt/nrpe-inputs/packages/*.rpm; \
    cp -a /opt/nrpe-inputs/sources/nrpe /opt/nrpe-sources; \
    cp -a /opt/nrpe-inputs/originals /opt/nrpe-original-inputs; \
    cp /opt/nrpe-inputs/metadata/* /opt/nrpe-build/; \
    bash /opt/nrpe-build/build-sles-user.sh; \
    rpmspec --query --buildrequires /opt/nrpe-sources/nrpe.spec > /tmp/nrpe-build-requires; \
    while IFS= read -r requirement; do \
      rpm --query --whatprovides "$requirement" || exit; \
    done < /tmp/nrpe-build-requires; \
    rm -rf /opt/nrpe-inputs/packages /tmp/nrpe-build-requires; \
    rm -rf /var/cache/zypp/packages /var/cache/zypp/raw /var/cache/zypp/solv
COPY --chmod=755 scripts/build-sles.sh /opt/nrpe-build/build-sles.sh
ENTRYPOINT ["/opt/nrpe-build/build-sles.sh"]
