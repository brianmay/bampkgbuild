ARG IMAGE
FROM ${IMAGE}

ARG IMAGE
ENV IMAGE ${IMAGE}

RUN sed -i 's/deb.debian.org/proxy.pri:9999/' /etc/apt/sources.list
RUN cat /etc/apt/sources.list | sed 's/^deb /deb-src /' > /etc/apt/sources.list.d/src.list
RUN apt-get update && apt-get install -y \
    build-essential \
    devscripts \
    haskell-debian-utils \
    locales \
 && rm -rf /var/lib/apt/lists/*


RUN sed -i -e 's/# en_AU.UTF-8 UTF-8/en_AU.UTF-8 UTF-8/' /etc/locale.gen && locale-gen
ENV LANG en_AU.UTF-8

WORKDIR /build
