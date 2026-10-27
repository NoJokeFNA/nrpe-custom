# syntax=docker/dockerfile:1
ARG DEBIAN_CODENAME=bookworm
FROM debian:${DEBIAN_CODENAME}

ARG NRPE_CA_SHA256=none

ARG DEBIAN_CODENAME
ENV DEBIAN_FRONTEND=noninteractive \
    DEBEMAIL=nrpe-builder@localhost.invalid \
    DEBFULLNAME="NRPE Custom Builder"

COPY scripts/setup-debian-repositories.sh scripts/install-ca-certificate.sh /opt/nrpe-build/
RUN --mount=type=secret,id=nrpe_ca_cert \
    set -eux; \
    bash /opt/nrpe-build/install-ca-certificate.sh /run/secrets/nrpe_ca_cert "$NRPE_CA_SHA256"; \
    bash /opt/nrpe-build/setup-debian-repositories.sh "$DEBIAN_CODENAME" source; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      build-essential ca-certificates devscripts dpkg-dev fakeroot python3; \
    apt-get build-dep -y --no-install-recommends nagios-nrpe; \
    rm -rf /var/lib/apt/lists/*

COPY scripts/ /opt/nrpe-build/
RUN chmod 755 /opt/nrpe-build/build.sh /opt/nrpe-build/verify.sh

WORKDIR /work
ENTRYPOINT ["/opt/nrpe-build/build.sh"]
