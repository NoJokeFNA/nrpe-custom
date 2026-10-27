# syntax=docker/dockerfile:1
ARG DEBIAN_CODENAME=bookworm
FROM debian:${DEBIAN_CODENAME}

ARG NRPE_CA_SHA256=none
ARG DEBIAN_CODENAME

ENV DEBIAN_FRONTEND=noninteractive

COPY scripts/setup-debian-repositories.sh scripts/install-ca-certificate.sh /opt/nrpe-test/
# Package installation must not start a background service in the test image.
RUN --mount=type=secret,id=nrpe_ca_cert \
    bash /opt/nrpe-test/install-ca-certificate.sh /run/secrets/nrpe_ca_cert "$NRPE_CA_SHA256" \
    && bash /opt/nrpe-test/setup-debian-repositories.sh "$DEBIAN_CODENAME" binary \
    && printf '#!/bin/sh\nexit 101\n' > /usr/sbin/policy-rc.d \
    && chmod 755 /usr/sbin/policy-rc.d \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates nagios-nrpe-plugin openssl \
    && rm -rf /var/lib/apt/lists/*

COPY scripts/integration-test.sh scripts/test-nrpe-protocol.sh /opt/nrpe-test/
RUN chmod 755 /opt/nrpe-test/*.sh

ENTRYPOINT ["/opt/nrpe-test/integration-test.sh"]
