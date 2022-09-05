ARG IMAGE
FROM ${IMAGE}

ARG IMAGE
ARG DISTRIBUTION
ARG SECURITY

RUN \
 echo "deb http://172.17.0.1:9999/debian ${DISTRIBUTION} main" \
 > /etc/apt/sources.list

RUN \
 if test "$SECURITY" = "pre-bullseye"; then \
     echo "deb http://172.17.0.1:9999/security ${DISTRIBUTION}/updates main" \
     >> /etc/apt/sources.list; \
 fi

RUN \
 if test "$SECURITY" = "bullseye"; then \
     echo "deb http://172.17.0.1:9999/security ${DISTRIBUTION}-security main" \
     >> /etc/apt/sources.list; \
 fi

RUN cat /etc/apt/sources.list
RUN apt-get update --yes && apt-get upgrade --yes && apt-get install --yes \
    build-essential \
    devscripts \
    haskell-debian-utils \
    locales \
    liblz4-tool \
    lintian \
 && rm -rf /var/lib/apt/lists/*

RUN sed -i -e 's/# en_AU.UTF-8 UTF-8/en_AU.UTF-8 UTF-8/' /etc/locale.gen && locale-gen
ENV LANG en_AU.UTF-8

ENV IMAGE ${IMAGE}
ENV DISTRIBUTION ${DISTRIBUTION}

COPY tools/ /usr/local/bin

WORKDIR /build
