ARG IMAGE
FROM ${IMAGE}

ARG IMAGE
ARG DISTRIBUTION

RUN \
 echo "deb http://172.17.0.1:9999/debian ${DISTRIBUTION} main\ndeb-src http://172.17.0.1:9999/debian ${DISTRIBUTION} main" \
 > /etc/apt/sources.list

RUN cat /etc/apt/sources.list
RUN apt-get update --yes && apt-get install --yes \
    build-essential \
    devscripts \
    haskell-debian-utils \
    locales \
    liblz4-tool \
 && rm -rf /var/lib/apt/lists/*

RUN sed -i -e 's/# en_AU.UTF-8 UTF-8/en_AU.UTF-8 UTF-8/' /etc/locale.gen && locale-gen
ENV LANG en_AU.UTF-8

ENV IMAGE ${IMAGE}
ENV DISTRIBUTION ${DISTRIBUTION}

COPY tools/ /usr/local/bin

WORKDIR /build
