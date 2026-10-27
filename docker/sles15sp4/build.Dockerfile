# syntax=docker/dockerfile:1
ARG SLES_BASE_IMAGE=registry.suse.com/bci/bci-base:15.4
FROM ${SLES_BASE_IMAGE}

ARG NRPE_CA_SHA256=none

# Keep installation in one layer: vfs-backed cloud Docker otherwise copies the
# entire compiler filesystem for every intermediate COPY/RUN instruction.
COPY scripts/install-ca-certificate.sh scripts/setup-sles-repositories.sh scripts/setup-sles-media.sh \
     scripts/sles_source.py scripts/fetch_sles_packages.py scripts/build-sles-user.sh \
     packaging/sles15sp4-source.json packaging/sles15sp4-user-source.json \
     packaging/sles15sp4-bootstrap.json packaging/sles15sp4-backports.asc \
     packaging/sles15sp4-suse.asc /opt/nrpe-build/
RUN --mount=type=secret,id=nrpe_ca_cert \
    --mount=from=nrpe_sles_media,target=/mnt/nrpe-sles-media,readonly \
    set -eu; \
    bash /opt/nrpe-build/install-ca-certificate.sh /run/secrets/nrpe_ca_cert "$NRPE_CA_SHA256"; \
    cp /opt/nrpe-build/sles15sp4-source.json /opt/nrpe-build/source.json; \
    cp /opt/nrpe-build/sles15sp4-user-source.json /opt/nrpe-build/user-source.json; \
    cp /opt/nrpe-build/sles15sp4-bootstrap.json /opt/nrpe-build/bootstrap.json; \
    rpm --import /opt/nrpe-build/sles15sp4-backports.asc /opt/nrpe-build/sles15sp4-suse.asc; \
    bash /opt/nrpe-build/setup-sles-repositories.sh; \
    zypper --non-interactive install --no-recommends \
      gcc make rpm-build cpio patch diffutils findutils tar gzip xz python3 \
      ca-certificates shadow coreutils grep util-linux \
      systemd-presets-branding-SLE util-linux-systemd; \
    python3 /opt/nrpe-build/fetch_sles_packages.py /opt/nrpe-build/bootstrap.json /tmp/nrpe-suse-rpms build; \
    zypper --non-interactive install --no-recommends /tmp/nrpe-suse-rpms/*.rpm; \
    bash /opt/nrpe-build/build-sles-user.sh; \
    python3 /opt/nrpe-build/sles_source.py /opt/nrpe-build/source.json /opt/nrpe-sources \
      --originals /opt/nrpe-original-inputs/nrpe; \
    rpmspec --query --buildrequires /opt/nrpe-sources/nrpe.spec > /tmp/nrpe-build-requires; \
    while IFS= read -r requirement; do \
      zypper --non-interactive install --no-recommends "$requirement" || exit; \
    done < /tmp/nrpe-build-requires; \
    rm -rf /tmp/nrpe-suse-rpms /tmp/nrpe-build-requires; \
    zypper clean --all

COPY --chmod=755 scripts/build-sles.sh /opt/nrpe-build/build-sles.sh
ENTRYPOINT ["/opt/nrpe-build/build-sles.sh"]
