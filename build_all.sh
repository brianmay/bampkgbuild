#!/bin/sh
set -ex

build() {
    src="$1"
    dst="$2"
    dist="$3"

    docker pull "$src"
    docker build --build-arg IMAGE="$src" --build-arg DISTRIBUTION="$dist" -t "$dst" .
}

build_security() {
    src="$1"
    dst="$2"

    docker build --build-arg IMAGE="$src" -t "$dst" --file=Dockerfile-security .
}

for d in buster bullseye sid; do
    build "i386/debian:$d" "brianmay/debian-i386:$d" "$d"
    build "debian:$d" "brianmay/debian-amd64:$d" "$d"
    build "debian:$d" "brianmay/debian-source:$d" "$d"
done

for d in buster bullseye; do
    build_security "brianmay/debian-i386:$d" "brianmay/debian-i386:$d-security"
    build_security "brianmay/debian-amd64:$d" "brianmay/debian-amd64:$d-security"
    build_security "brianmay/debian-source:$d" "brianmay/debian-source:$d-security"
done
