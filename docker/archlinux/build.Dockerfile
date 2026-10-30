# syntax=docker/dockerfile:1
FROM archlinux:base-devel
ARG NRPE_CA_SHA256=none
COPY scripts/install-ca-certificate.sh /opt/nrpe/scripts/
RUN --mount=type=secret,id=nrpe_ca_cert \
 bash /opt/nrpe/scripts/install-ca-certificate.sh /run/secrets/nrpe_ca_cert "$NRPE_CA_SHA256" \
 && pacman -Syu --noconfirm --needed python openssl systemd \
 && pacman -Scc --noconfirm
COPY packaging/archlinux/ /opt/nrpe/packaging/archlinux/
COPY packaging/archlinux-source.json /opt/nrpe/packaging/
COPY scripts/arch_source.py scripts/build-arch.sh /opt/nrpe/scripts/
ENTRYPOINT ["bash", "/opt/nrpe/scripts/build-arch.sh"]
