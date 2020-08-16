ARG IMAGE
FROM ${IMAGE}

ARG IMAGE
ENV IMAGE ${IMAGE}

RUN sed -i 's/deb.debian.org/proxy.pri:9999/' /etc/apt/sources.list
RUN apt-get update && apt-get install -y \
    build-essential \
    devscripts \
    haskell-debian-utils \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /build
