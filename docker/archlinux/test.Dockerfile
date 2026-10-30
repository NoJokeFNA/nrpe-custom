# syntax=docker/dockerfile:1
FROM archlinux:base
ARG NRPE_CA_SHA256=none
COPY scripts/install-ca-certificate.sh /opt/nrpe-test/
RUN --mount=type=secret,id=nrpe_ca_cert \
 bash /opt/nrpe-test/install-ca-certificate.sh /run/secrets/nrpe_ca_cert "$NRPE_CA_SHA256" \
 && pacman -Syu --noconfirm --needed python openssl systemd \
 && pacman -Scc --noconfirm
COPY scripts/integration-test-arch.sh scripts/test-nrpe-protocol.sh /opt/nrpe-test/
ENTRYPOINT ["bash", "/opt/nrpe-test/integration-test-arch.sh"]
