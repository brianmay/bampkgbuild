ARG IMAGE
FROM ${IMAGE}

ARG IMAGE
ENV IMAGE ${IMAGE}

RUN \
 DIST="$(echo "$IMAGE" | sed "s/^.*://")"; \
 echo "deb http://proxy.pri:9999/debian $DIST main\ndeb-src http://proxy.pri:9999/debian $DIST main" \
 > /etc/apt/sources.list

RUN apt-get update && apt-get install -y \
    build-essential \
    devscripts \
    haskell-debian-utils \
    locales \
 && rm -rf /var/lib/apt/lists/*


RUN sed -i -e 's/# en_AU.UTF-8 UTF-8/en_AU.UTF-8 UTF-8/' /etc/locale.gen && locale-gen
ENV LANG en_AU.UTF-8

WORKDIR /build
