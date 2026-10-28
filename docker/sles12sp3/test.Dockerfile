# syntax=docker/dockerfile:1
ARG SLES_BASE_IMAGE=registry.suse.com/suse/sles12sp3@sha256:0995dbf051274a3a5baf19c7f94ce7ebe69d7aa91f7b3b22248bd06d7122e53a
FROM python:3.13-slim AS inputs
ARG NRPE_CA_SHA256=none
COPY scripts/prepare_sles_inputs.py scripts/fetch_sles_packages.py scripts/sles_source.py /tools/
COPY packaging/sles12sp3-*.json packaging/sles12sp3-suse.asc /packaging/
RUN --mount=type=secret,id=nrpe_ca_cert \
    python3 /tools/prepare_sles_inputs.py /packaging /inputs runtime \
      --ca /run/secrets/nrpe_ca_cert --ca-sha256 "$NRPE_CA_SHA256"
FROM ${SLES_BASE_IMAGE}
COPY --from=inputs /inputs /opt/nrpe-inputs
COPY scripts/verify-sles-packages.sh scripts/verify-sles-environment.sh /opt/nrpe-test/
RUN set -eu; \
    bash /opt/nrpe-test/verify-sles-environment.sh runtime; \
    rpm --import /opt/nrpe-inputs/suse.asc; \
    bash /opt/nrpe-test/verify-sles-packages.sh /opt/nrpe-inputs/packages; \
    zypper --non-interactive --no-refresh install --no-recommends /opt/nrpe-inputs/packages/*.rpm; \
    rm -rf /opt/nrpe-inputs/packages; \
    rm -rf /var/cache/zypp/packages /var/cache/zypp/raw /var/cache/zypp/solv
COPY --chmod=755 scripts/integration-test-sles.sh scripts/test-nrpe-protocol.sh /opt/nrpe-test/
ENTRYPOINT ["/opt/nrpe-test/integration-test-sles.sh"]
