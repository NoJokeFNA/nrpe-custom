# syntax=docker/dockerfile:1
ARG DEBIAN_CODENAME=bookworm
FROM debian:${DEBIAN_CODENAME}

ARG DEBIAN_CODENAME
ENV DEBIAN_FRONTEND=noninteractive \
    DEBEMAIL=nrpe-builder@localhost.invalid \
    DEBFULLNAME="NRPE Custom Builder"

# Enable Debian source repositories present in the official Debian image.
# This also includes the security source repositories where applicable.
RUN set -eux; \
    if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
      sed -i -E '/^Types: / { /deb-src/! s/$/ deb-src/; }' /etc/apt/sources.list.d/debian.sources; \
    elif [ -f /etc/apt/sources.list ]; then \
      sed -n '/^deb /s/^deb /deb-src /p' /etc/apt/sources.list > /etc/apt/sources.list.d/nrpe-source.list; \
    else \
      echo 'ERROR: Debian apt sources layout not recognized' >&2; exit 1; \
    fi; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      build-essential ca-certificates devscripts dpkg-dev fakeroot python3; \
    apt-get build-dep -y --no-install-recommends nagios-nrpe; \
    rm -rf /var/lib/apt/lists/*

COPY scripts/ /opt/nrpe-build/
RUN chmod 755 /opt/nrpe-build/build.sh /opt/nrpe-build/verify.sh

WORKDIR /work
ENTRYPOINT ["/opt/nrpe-build/build.sh"]
